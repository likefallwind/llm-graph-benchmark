"""Offline workflow checks. Fake model responses validate plumbing, not judge accuracy."""
import copy
import json
from pathlib import Path
import threading
import time

import pytest

from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.cli import main
from llm_graph_benchmark.workflow import alignment, engine, granularity, identity_judge, ledger, protocol, referent, qa_support
from llm_graph_benchmark.workflow.preparation import prepare, read, verify
from llm_graph_benchmark.workflow.reporting import report
from llm_graph_benchmark.workflow.transport import write


def wire(value):
    return {"choices": [{"message": {"content": value if isinstance(value, str) else json.dumps(value)}}]}


class FakeClient:
    """Simulates schema-valid output; it has no credentials or network access."""
    def __init__(self, *args, **kwargs):
        self.calls = []
        self.fail_once = None
        self.guard = threading.Lock()
        self.active = self.peak = 0

    def complete(self, messages, max_tokens=8192, validator=None):
        with self.guard:
            self.calls.append(copy.deepcopy(messages))
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(0.005)
            prompt = messages[0]["content"]
            if self.fail_once == prompt:
                self.fail_once = None
                raise OSError("synthetic transport interruption")
            if prompt == ledger.PROMPT:
                payload = json.loads(messages[1]["content"])
                ev = [{"id": payload["reference_context"][0]["id"]}]
                v = {"target_copy": payload["target"],
                     "claims": [{"text": payload["target"]["description"],
                                 "segment_ids": [s["id"] for s in payload["segments"]],
                                 "verdict": "supported", "evidence": ev, "reason": "synthetic fixture"}],
                     "checks": {name: {"verdict": "supported", "evidence": ev, "reason": "synthetic fixture"}
                                for name in ledger.CHECKS}}
            elif prompt == alignment.PROMPT:
                payload = json.loads(messages[1]["content"])
                v = "\n".join(f"<item>{c['index']}|asserted|synthetic fixture</item>" for c in payload["claims"])
                v += "\n<coverage>complete|synthetic fixture</coverage>"
            elif prompt == granularity.PROMPT:
                v = {"label": "L3", "reason": "synthetic fixture"}
            elif prompt == referent.PROMPTS["correctness"]:
                v = "<label>correct</label><reason>u1 synthetic fixture</reason>"
            elif prompt == referent.PROMPTS["evidence"]:
                v = "<label>supported</label><reason>u1 synthetic fixture</reason>"
            elif prompt == protocol.SHARED + protocol.TYPES:
                payload = json.loads(messages[1]["content"])
                v = {"items": [{**t, "label": "pass" if i == 0 else "fail", "level": "L2",
                                 "reason": "synthetic fixture", "evidence_ids": ["u1"]}
                                for i, t in enumerate(payload["target"]["types"])]}
            elif prompt == protocol.DESCRIPTION:
                payload = json.loads(messages[1]["content"])
                v = {"label": "supported", "reason": "synthetic fixture", "evidence_ids": ["u1"]}
            elif prompt == protocol.FACT:
                payload = json.loads(messages[1]["content"])
                v = {"label": "pass" if payload["evidence"] else "fail",
                     "evidence_ids": [x["id"] for x in payload["evidence"]], "reason": "synthetic fixture"}
            elif prompt == qa_support.RUBRIC_PROMPT:
                payload = json.loads(messages[1]["content"])
                v = {"requirements": [{"id": "R1", "text": payload["reference_answer"], "core": True,
                                       "source_ids": [payload["reference_sources"][0]["id"]]}],
                     "source_caveat": ""}
            elif prompt == qa_support.SUPPORT_PROMPT:
                payload = json.loads(messages[1]["content"])
                refs = [{"assertion_id": c["id"], "field": "text", "quote": c["text"]}
                        for c in payload["candidate_assertions"]]
                v = {"judgments": [{"requirement_id": r["id"], "label": "pass" if refs else "fail",
                                     "reason": "synthetic fixture", "assertion_evidence": refs}
                                    for r in payload["answer_requirements"]]}
            else:
                v = {"label": "pass", "confidence": 1, "reason": "synthetic fixture"}
            response = wire(v)
            if validator:
                validator(response)
            return response
        finally:
            with self.guard:
                self.active -= 1


@pytest.fixture
def config_path(benchmark_dir, submission_payload):
    doc = submission_payload["documents"][0]
    doc["entities"][0]["types"] = ["concept", "fine type"]
    doc["entities"][0]["aliases"] = ["shared name"]
    doc["entities"][1]["aliases"] = ["shared name"]
    submission_payload["runtime"] = {"input_tokens": 2_000_000, "output_tokens": 500_000}
    write(benchmark_dir / "submission.json", submission_payload)
    config = {"benchmark": "benchmark.json", "submissions": ["submission.json"],
              "samples": {"entities": 100, "assertions": 200, "aliases": 30, "splits": 30},
              "seed": 31, "workers": 6}
    path = benchmark_dir / "workflow.json"
    write(path, config)
    return path


def prepared(config_path):
    run = config_path.parent / "run"
    prepare(config_path, run)
    return run


def test_prepare_is_offline_deterministic_and_only_selected_metrics(config_path, monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    run = prepared(config_path)
    other = config_path.parent / "run2"
    prepare(config_path, other)
    tasks = read(run / "tasks.json")
    assert tasks == read(other / "tasks.json")
    assert set(t["metric"] for t in tasks) == set(protocol.METRICS)
    assert not (run / "api").exists()
    assert verify(run)["planned_calls_without_retries"] == len(tasks) + 1
    for task in tasks:
        assert "system-a" not in json.dumps(task["messages"])
        if task["metric"] == "fact_recovery":
            assert "source_evidence" not in task["payload"]
            assert not any("text" in row for row in task["payload"]["evidence"])
    assert engine.status(run)["phase"] == "prepared"
    assert not engine.status(run)["complete"]
    with pytest.raises(ValueError, match="new run directory"):
        prepare(config_path, run)


def test_end_to_end_macro_denominator_and_cached_resume(config_path):
    run, fake = prepared(config_path), FakeClient()
    assert engine.execute(run, client_factory=lambda *a, **k: fake) == 0
    first_calls = len(fake.calls)
    assert 1 < fake.peak <= 6
    summary = read(run / "summary.json")
    groups = summary["groups"]["system-a"]
    assert summary["complete"]
    assert groups["entity_typing"]["rate"] == .75  # Not micro-average 2/3.
    assert groups["entity_typing"]["atomic"] == {"pass": 2, "fail": 1}
    assert groups["relation_granularity"]["correct_l3_coverage"] == 1
    assert groups["relation_granularity"]["correct_within_l3"] == 1
    assert "book_qa" not in groups
    assert summary["structure"]["system-a"]["construction"]["total_tokens_million"] == 2.5
    assert engine.execute(run, client_factory=lambda *a, **k: fake, retry_failed=True) == 0
    assert len(fake.calls) == first_calls
    assert (run / "comparison.csv").exists()
    assert "历史断言引用支持率" not in (run / "REPORT.md").read_text()
    assert "score" in next(x for x in read(run / "case-results.json") if x["metric"] == "entity_typing")


def test_technical_failure_not_semantic_failure_and_explicit_retry(config_path):
    run, fake = prepared(config_path), FakeClient()
    fake.fail_once = protocol.SHARED + protocol.TYPES
    assert engine.execute(run, client_factory=lambda *a, **k: fake) == 3
    first = read(run / "summary.json")["groups"]["system-a"]["entity_typing"]
    assert first["rate"] is None
    assert first["unassessed"] == 1
    assert first["statuses"]["failed"] == 1
    assert engine.status(run)["phase"] == "incomplete"
    calls = len(fake.calls)
    assert engine.execute(run, client_factory=lambda *a, **k: fake) == 3
    assert len(fake.calls) == calls
    assert engine.execute(run, retry_failed=True, client_factory=lambda *a, **k: fake) == 0
    assert len(fake.calls) == calls + 1
    assert len(list((run / "technical-retries").glob("*.json"))) == 1


def test_qa_is_not_prepared_requested_or_reported(config_path, monkeypatch):
    from llm_graph_benchmark import retrieval
    def forbidden(*args, **kwargs):
        raise AssertionError("Retired QA retrieval must not run")
    monkeypatch.setattr(retrieval, "retrieve_qa_probes", forbidden)
    run, fake = prepared(config_path), FakeClient()
    assert "book_qa" not in protocol.METRICS and "book_qa" not in protocol.VERSIONS
    assert "qa_requirements" not in read(run / "prompts.json")
    assert all("qa" not in system["retrieval"] for system in read(run / "systems.json").values())
    assert engine.execute(run, client_factory=lambda *a, **k: fake) == 0
    assert all(m[0]["content"] not in {qa_support.RUBRIC_PROMPT, qa_support.SUPPORT_PROMPT} for m in fake.calls)
    for name in ("REPORT.md", "comparison.csv"):
        assert "Book QA" not in (run / name).read_text()
    assert "book_qa" not in read(run / "summary.json")["groups"]["system-a"]


def test_native_absence_does_not_replace_entities_or_invent_fields(config_path):
    path = config_path.parent / "submission.json"
    sub = read(path)
    for e in sub["documents"][0]["entities"]:
        e["types"] = []
        e["metadata"] = {"definition_available": False}
        e["definition"] = ""
    write(path, sub)
    run = prepared(config_path)
    tasks = read(run / "tasks.json")
    assert not any(t["metric"] in {"entity_typing", "entity_description"} for t in tasks)
    sample = read(run / "sampling.json")["system-a"][0]
    assert len(sample["entity_ids"]) == 2
    assert len(sample["excluded_fields"]) == 4
    summary = report(run)
    assert summary["groups"]["system-a"]["entity_typing"]["status"] == "not_applicable"
    assert summary["structure"]["system-a"]["field_counts"]["definition"] == 0


def test_binding_verbatim_guards_and_uncertain_denominator(config_path):
    run = prepared(config_path)
    tasks = read(run / "tasks.json")
    task = next(t for t in tasks if t["metric"] == "entity_typing" and len(t["payload"]["target"]["types"]) == 2)
    value = {"items": [{**t, "label": "uncertain", "reason": "ambiguous", "evidence_ids": [], "level": None}
                        for t in task["payload"]["target"]["types"]]}
    assert protocol.parse(wire(value), task)["label"] == "uncertain"
    value["items"][0]["type_text"] = "wrong label"
    with pytest.raises(ValueError, match="binding"):
        protocol.parse(wire(value), task)
    desc = next(t for t in tasks if t["metric"] == "entity_description")
    source = desc["payload"]["target"]["description"]
    for text in [source + " extra unsupported words", source[:-5], ""]:
        with pytest.raises(ValueError):
            protocol.parse(wire({"claims": [{"text": text, "label": "pass",
                                            "reason": "x", "evidence_ids": ["u1"]}]}), desc)
    # A structurally valid uncertain outcome remains a zero supported fraction
    # within the entity; it is never removed from the denominator.
    for t in tasks:
        if t["metric"] == "entity_typing":
            vals = {"items": [{**x, "label": "uncertain", "reason": "ambiguous", "evidence_ids": []}
                              for x in t["payload"]["target"]["types"]]}
            v = protocol.parse(wire(vals), t)
            write(run / "results" / (t["id"] + ".json"),
                  {"task_id": t["id"], "task_hash": canonical_hash(t), "status": "done",
                   "value": v, "value_hash": canonical_hash(v)})
    assert report(run)["groups"]["system-a"]["entity_typing"]["rate"] == 0


def test_frozen_inputs_and_results_cannot_be_silently_reused(config_path):
    run = prepared(config_path)
    tasks = read(run / "tasks.json")
    tasks[0]["payload"]["injected"] = True
    write(run / "tasks.json", tasks)
    with pytest.raises(ValueError, match="Frozen input changed"):
        engine.execute(run, client_factory=FakeClient)
    with pytest.raises(ValueError, match="Frozen input changed"):
        engine.status(run)


def test_missing_probes_na_and_no_structural_zero_for_empty_graph(config_path):
    (config_path.parent / "qa_probes.jsonl").write_text("")
    subpath = config_path.parent / "submission.json"
    sub = read(subpath)
    sub["documents"][0]["assertions"] = []
    write(subpath, sub)
    run = prepared(config_path)
    summary = report(run)
    assert "book_qa" not in summary["groups"]["system-a"]
    assert summary["groups"]["system-a"]["fact_recovery"]["expected"] == 1
    assert summary["structure"]["system-a"]["assertion_citation_presence"] is None


@pytest.mark.parametrize("workers", [0, 7, True, 1.5])
def test_bad_concurrency_is_rejected(config_path, workers):
    config = read(config_path)
    config["workers"] = workers
    write(config_path, config)
    with pytest.raises(ValueError, match="1..6"):
        prepared(config_path)


def test_multidocument_shared_local_ids_remain_distinct(config_path):
    documents = [json.loads(x) for x in (config_path.parent / "documents.jsonl").read_text().splitlines()]
    second = copy.deepcopy(documents[0])
    second["document_id"] = "doc-2"
    with (config_path.parent / "documents.jsonl").open("a") as f:
        f.write(json.dumps(second) + "\n")
    subpath = config_path.parent / "submission.json"
    sub = read(subpath)
    second = copy.deepcopy(sub["documents"][0])
    second["document_id"] = "doc-2"
    sub["documents"].append(second)
    write(subpath, sub)
    run = prepared(config_path)
    keys = read(run / "private-key.json")
    aliases = [v for v in keys.values() if v["metric"] == "alias_identity"]
    splits = [v for v in keys.values() if v["metric"] == "identity_split"]
    assert len(aliases) == 4 and len(splits) == 2
    assert {v["document_id"] for v in aliases} == {"doc-1", "doc-2"}


def test_cli_prepare_status_report_and_duplicate_worker_guard(config_path, capsys):
    run = config_path.parent / "cli-run"
    assert main(["workflow", "prepare", "--config", str(config_path), "--run", str(run)]) == 0
    assert main(["workflow", "status", "--run", str(run)]) == 0
    assert main(["workflow", "report", "--run", str(run)]) == 0
    with engine.run_lock(run):
        assert engine.active(run)
        with pytest.raises(ValueError, match="active worker"):
            engine.execute(run, client_factory=FakeClient)
    assert not engine.active(run)


def test_quality_subset_and_full_structure_are_distinct(config_path):
    subpath = config_path.parent / "submission.json"
    full = read(subpath)
    full["documents"][0]["assertions"].append({**full["documents"][0]["assertions"][0], "id": "a2"})
    write(config_path.parent / "full.json", full)
    config = read(config_path)
    config["submissions"] = [{"path": "submission.json", "structure_path": "full.json", "scope_note": "one semantic edge"}]
    write(config_path, config)
    run = prepared(config_path)
    structural = read(run / "structure.json")["system-a"]
    assert structural["assertion_count"] == 2
    assert structural["quality_assertion_count"] == 1



def test_background_launch_completed_run_uses_no_api(config_path, monkeypatch):
    run = prepared(config_path)
    engine.execute(run, client_factory=FakeClient)
    monkeypatch.setenv("MINIMAX_API_KEY", "synthetic-unused-key")
    launched = engine.launch(run)
    assert launched["run"] == str(run)
    deadline = time.monotonic() + 5
    while engine.active(run) and time.monotonic() < deadline:
        time.sleep(.02)
    assert engine.status(run)["complete"]
    assert not (run / "api").exists()
    assert (run / "worker.log").exists()

def test_missing_field_marker_required_and_no_nontext_silent_failure(config_path):
    path = config_path.parent / "submission.json"
    sub = read(path)
    sub["documents"][0]["entities"][0]["definition"] = ""
    write(path, sub)
    with pytest.raises(ValueError, match="Invalid submission"):
        prepared(config_path)



def test_identity_judges_see_every_submitted_source_untruncated(config_path):
    docs = config_path.parent / "documents.jsonl"
    document = json.loads(docs.read_text())
    long_text = "Alpha relates to beta. " + "context " * 400 + "Alpha is also called shared name."
    document["units"] = [{"unit_id": "u1", "modality": "text", "text": long_text},
                         {"unit_id": "u2", "modality": "text", "text": "Beta appears here."}]
    docs.write_text(json.dumps(document) + "\n")
    path = config_path.parent / "submission.json"
    sub = read(path)
    entities = sub["documents"][0]["entities"]
    entities[0]["evidence"] = [{"unit_id": "u1"}, {"unit_id": "u1"}]
    entities[1]["evidence"] = [{"unit_id": "u2"}]
    write(path, sub)
    tasks = read(prepared(config_path) / "tasks.json")
    alias = next(t for t in tasks if t["metric"] == "alias_identity" and t["payload"]["content"]["name"] == "Alpha")
    split = next(t for t in tasks if t["metric"] == "identity_split")
    assert alias["messages"][0]["content"] == identity_judge.ALIAS_PROMPT
    assert split["messages"][0]["content"] == identity_judge.SPLIT_PROMPT
    shown = json.loads(alias["messages"][1]["content"])
    assert shown["alias"] == "shared name"
    assert shown["evidence"] == [{"id": "u1", "text": long_text}]
    pair = json.loads(split["messages"][1]["content"])
    assert pair["shared_surfaces"] == ["sharedname"]
    assert {pair["left"]["name"]: pair["left"]["evidence"], pair["right"]["name"]: pair["right"]["evidence"]} == {
        "Alpha": [{"id": "u1", "text": long_text}], "Beta": [{"id": "u2", "text": "Beta appears here."}]}
