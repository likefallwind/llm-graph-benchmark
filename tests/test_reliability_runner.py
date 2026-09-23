"""Offline regression checks for frozen evaluation, isolation, and accounting."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest


RUNNER = Path(__file__).resolve().parents[1] / "studies/d2l-reliability-20260920/evaluate.py"


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location("reliability_test_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def transport(monkeypatch):
    class TerminalProviderError(RuntimeError):
        pass

    class ContentRejected(RuntimeError):
        pass

    def unavailable(*args, **kwargs):
        raise AssertionError("Runner tests must supply an offline client")

    fake = SimpleNamespace(
        REQUEST_CONCURRENCY=6,
        TerminalProviderError=TerminalProviderError,
        ContentRejected=ContentRejected,
        Client=unavailable,
        usage_summary=lambda *args: {"request_attempts": 0},
    )
    monkeypatch.setitem(sys.modules, "transport", fake)
    return fake


@pytest.fixture
def run_factory(runner, tmp_path):
    def create(count=12):
        run = tmp_path / "run"
        tasks, key = [], {}
        for index in range(count):
            kind = "entity" if index % 2 == 0 else "assertion"
            task_id = f"q_{index}"
            target = {"name": f"entity-{index}"} if kind == "entity" else {
                "subject": f"entity-{index}", "predicate": "supports", "object": "result",
            }
            tasks.append({
                "id": task_id,
                "payload": {
                    "kind": kind,
                    "target": target,
                    "submitted_sources": [{"id": "P1", "text": "submitted source"}],
                    "reference_context": [{"id": "P2", "text": "expanded-only source"}],
                },
            })
            key[task_id] = {
                "system": "hidden-system", "kind": kind,
                "audit": {"source_characters": 16, "reference_units": 1},
            }
        authored = runner.calibration()
        files = {
            "tasks.json": tasks, "private-key.json": key,
            "calibration.json": authored, "prompts.json": runner.PROMPTS,
            "legacy-coverage.json": {"systems": {}},
        }
        for name, value in files.items():
            runner.write(run / name, value)
        runner.write(run / "manifest.json", {
            "workers": 6,
            "frozen_files": {name: runner.sha(run / name) for name in files},
        })
        # Calibration is already judged; fake clients below exercise the actual
        # evaluation scheduler without needing to imitate an LLM on smoke cases.
        for task in authored:
            for dimension, label in task["expected"].items():
                runner.write(run / "results" / f"{task['id']}-{dimension}.json", {
                    "task_id": task["id"], "dimension": dimension,
                    "status": "done", "value": {"label": label, "reason": "fixture"},
                })
        return run, tasks

    return create


def response(label):
    return {"choices": [{"message": {"content": f"<label>{label}</label>\n<reason>fixture</reason>"}}]}


def test_evidence_call_cannot_receive_expanded_context_or_unblinding_metadata(runner):
    task = {
        "id": "PRIVATE-TASK-ID", "system": "PRIVATE-SYSTEM", "private_key": "PRIVATE-KEY",
        "payload": {
            "kind": "assertion", "target": {"subject": "A", "predicate": "supports", "object": "B"},
            "submitted_sources": [{"id": "P1", "text": "A supports B."}],
            "reference_context": [{"id": "P2", "text": "EXPANDED-ONLY-SECRET"}],
            "system": "PRIVATE-PAYLOAD-SYSTEM", "private_key": "PRIVATE-PAYLOAD-KEY",
        },
    }
    original = copy.deepcopy(task)
    evidence = runner.messages(task, "evidence", runner.PROMPTS)
    correctness = runner.messages(task, "correctness", runner.PROMPTS)

    evidence_payload = json.loads(evidence[1]["content"])
    assert set(evidence_payload) == {"kind", "target", "submitted_sources", "directed_relation"}
    assert evidence_payload['directed_relation'] == 'A → supports → B'
    assert evidence_payload["submitted_sources"] == task["payload"]["submitted_sources"]
    assert "EXPANDED-ONLY-SECRET" not in json.dumps(evidence)
    assert "PRIVATE-" not in json.dumps([evidence, correctness])
    assert json.loads(correctness[1]["content"])["reference_context"] == task["payload"]["reference_context"]
    assert task == original


def test_pending_uncertain_and_failures_remain_in_selected_denominator(runner, transport, run_factory):
    run, tasks = run_factory(count=6)
    # Three entity records: confirmed, uncertain, and missing. Three assertion
    # records: confirmed, rejected, and provider failure. Evidence stays missing.
    labels = {0: "correct", 2: "uncertain", 1: "correct", 3: "incorrect"}
    for index, label in labels.items():
        runner.write(run / "results" / f"{tasks[index]['id']}-correctness.json", {
            "status": "done", "value": {"label": label, "reason": "fixture"},
        })
    runner.write(run / "results" / f"{tasks[5]['id']}-correctness.json", {"status": "failed"})

    summary = runner.summarize(run)

    assert summary["complete"] is False
    assert summary["expected_judgments"] == 12
    assert summary["judgment_statuses"] == {"done": 4, "pending": 7, "failed": 1}
    groups = summary["systems"]["hidden-system"]
    entities = groups["entity"]["correctness"]
    assertions = groups["assertion"]["correctness"]
    assert groups["entity"]["selected"] == groups["assertion"]["selected"] == 3
    assert entities["uncertain"] == 1 and entities["unassessed"] == 1
    assert entities["confirmed_rate_all"] == pytest.approx(1 / 3)
    assert entities["rate_decided"] == 1.0
    assert assertions["unassessed"] == 1
    assert assertions["confirmed_rate_all"] == pytest.approx(1 / 3)
    assert assertions["rate_decided"] == 0.5
    assert groups["entity"]["evidence"]["unassessed"] == 3
    assert groups["entity"]["evidence"]["rate_decided"] is None
    report = (run / "REPORT.md").read_text()
    assert "未完成，不得作为最终排名" in report
    assert "| hidden-system | 1/3 | 0/3 | 1/3 | 0/3 |" in report


@pytest.mark.parametrize("name", ["tasks.json", "private-key.json", "prompts.json", "calibration.json"])
def test_changed_frozen_input_rejected_before_client_creation(runner, transport, run_factory, name):
    run, _ = run_factory()
    path = run / name
    path.write_text(path.read_text() + " ")

    # The fixture's Client raises if constructed, so a hash failure must happen
    # before credentials are accessed or any external work starts.
    with pytest.raises(ValueError, match="Frozen artifact changed"):
        runner.execute(run)
    assert not list((run / "results").glob("q_*.json"))


def test_terminal_provider_error_stops_queue_and_leaves_missing_results_pending(
    runner, transport, run_factory,
):
    run, _ = run_factory()
    barrier = threading.Barrier(6)
    guard = threading.Lock()
    calls = []

    class Client:
        def __init__(self, *args):
            pass

        def complete(self, messages, **kwargs):
            with guard:
                calls.append(messages)
            barrier.wait(timeout=5)
            raise transport.TerminalProviderError("fixture quota exhausted")

    transport.Client = Client

    assert runner.execute(run) == 4
    assert len(calls) == 6  # One in-flight wave; the remaining queue is untouched.
    progress = runner.read(run / "progress.json")
    summary = runner.read(run / "summary.json")
    assert progress["phase"] == "stopped_provider_error"
    assert progress["processed"] == 6 and progress["total"] == 24
    assert summary["complete"] is False
    assert summary["judgment_statuses"] == {"terminal_provider_error": 6, "pending": 18}
    assert len(list((run / "results").glob("q_*.json"))) == 6
    assert "未完成，不得作为最终排名" in (run / "REPORT.md").read_text()


def test_six_slot_fake_run_preserves_verdicts_and_resumes_without_new_calls(
    runner, transport, run_factory,
):
    run, _ = run_factory()
    barrier = threading.Barrier(6)
    guard = threading.Lock()
    counts = {"active": 0, "peak": 0, "calls": 0}

    class Client:
        def __init__(self, *args):
            pass

        def complete(self, messages, validator, **kwargs):
            with guard:
                counts["active"] += 1
                counts["calls"] += 1
                counts["peak"] = max(counts["peak"], counts["active"])
            try:
                barrier.wait(timeout=5)
                payload = json.loads(messages[1]["content"])
                label = "incorrect" if "reference_context" in payload else "uncertain"
                value = response(label)
                validator(value)
                return value
            finally:
                with guard:
                    counts["active"] -= 1

    transport.Client = Client

    assert runner.execute(run) == 0
    assert counts == {"active": 0, "peak": 6, "calls": 24}
    summary = runner.read(run / "summary.json")
    assert summary["complete"] is True
    assert summary["judgment_statuses"] == {"done": 24}
    for group in summary["systems"]["hidden-system"].values():
        assert group["correctness"]["incorrect"] == 6
        assert group["evidence"]["uncertain"] == 6
        assert group["correctness"]["confirmed_rate_all"] == 0
        assert group["evidence"]["rate_decided"] is None

    assert runner.execute(run) == 0
    assert counts["calls"] == 24  # Cached negative and uncertain votes stay fixed.


def test_calibration_failure_never_dispatches_evaluation(runner, transport, run_factory):
    run, _ = run_factory()
    path = run / "results/cal-supported-correctness.json"
    result = runner.read(path)
    result["value"]["label"] = "incorrect"
    runner.write(path, result)
    transport.Client = lambda *args: SimpleNamespace()

    assert runner.execute(run) == 2
    assert runner.read(run / "progress.json")["phase"] == "calibration_needs_review"
    assert runner.read(run / "calibration-report.json")["passed"] is False
    assert not list((run / "results").glob("q_*.json"))


def test_explicit_exploratory_mode_preserves_failed_checks_in_completed_report(runner, transport, run_factory):
    run, _ = run_factory()
    manifest = runner.read(run / 'manifest.json')
    manifest['allow_unvalidated_judge'] = True
    runner.write(run / 'manifest.json', manifest)
    path = run / 'results/cal-supported-correctness.json'
    failed = runner.read(path)
    failed['value']['label'] = 'incorrect'
    runner.write(path, failed)

    class Client:
        def __init__(self, *args):
            pass

        def complete(self, messages, validator, **kwargs):
            payload = json.loads(messages[1]['content'])
            value = response('correct' if 'reference_context' in payload else 'supported')
            validator(value)
            return value

    transport.Client = Client
    assert runner.execute(run) == 0
    summary = runner.read(run / 'summary.json')
    assert summary['complete'] is True
    assert summary['judge_validation']['development_checks_passed'] is False
    assert summary['judge_validation']['independent_validation'] is False
    assert runner.read(path) == failed
    assert '裁判未通过开发检查' in (run / 'REPORT.md').read_text()
