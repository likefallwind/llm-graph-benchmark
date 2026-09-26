"""Whole-description labels, denominators and frozen-sample reassessment."""
import pytest

from test_workflow import config_path, FakeClient, prepared, wire
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow import protocol, engine
from llm_graph_benchmark.workflow.preparation import read, sha
from llm_graph_benchmark.workflow.reporting import report
from llm_graph_benchmark.workflow.transport import write
from llm_graph_benchmark.workflow.description_reassessment import prepare_description_reassessment


@pytest.mark.parametrize("label,refs,valid", [
    ("supported", ["u1"], True), ("not_supported", [], True), ("uncertain", [], True),
    ("supported", [], False), ("supported", ["invented"], False), ("pass", ["u1"], False),
])
def test_single_whole_description_verdict(label, refs, valid):
    task = {"metric": "entity_description", "payload": {
        "target": {"name": "A", "description": "First claim. Second claim—condition."},
        "evidence": [{"id": "u1", "text": "Evidence"}]}}
    value = {"label": label, "reason": "whole description judgment", "evidence_ids": refs}
    if valid:
        assert protocol.parse(wire(value), task) == value
    else:
        with pytest.raises(ValueError):
            protocol.parse(wire(value), task)
    value["claims"] = []
    with pytest.raises(ValueError, match="one verdict"):
        protocol.parse(wire(value), task)


@pytest.mark.parametrize("other_label", ["not_supported", "uncertain"])
def test_whole_description_counts_not_fragment_macro(config_path, other_label):
    run = prepared(config_path)
    tasks = [t for t in read(run / "tasks.json") if t["metric"] == "entity_description"]
    assert len(tasks) == 2
    for task, label in zip(tasks, ("supported", other_label)):
        value = protocol.parse(wire({"label": label, "reason": "fixture", "evidence_ids": ["u1"]}), task)
        write(run / "results" / (task["id"] + ".json"), {
            "task_id": task["id"], "task_hash": canonical_hash(task), "status": "done",
            "value": value, "value_hash": canonical_hash(value)})
    group = report(run)["groups"]["system-a"]["entity_description"]
    assert group["numerator"] == 1 and group["denominator"] == 2 and group["rate"] == .5
    assert group["aggregation"] == "sample_fraction" and group["atomic"] == {}
    assert group["labels"] == {"supported": 1, other_label: 1}
    text = (run / "REPORT.md").read_text()
    assert "整段描述不支持率" in text and "整段描述不确定率" in text
    assert "整段描述支持率（诊断）" not in text


def test_technical_failure_not_a_description_label(config_path):
    run, fake = prepared(config_path), FakeClient()
    fake.fail_once = protocol.DESCRIPTION
    assert engine.execute(run, client_factory=lambda *a, **k: fake) == 3
    group = read(run / "summary.json")["groups"]["system-a"]["entity_description"]
    assert group["rate"] is None and group["unassessed"] == 1
    assert "not_supported" not in group["labels"]
    assert engine.execute(run, client_factory=lambda *a, **k: fake, retry_failed=True) == 0


def test_reassessment_preserves_sample_description_evidence_and_parent(config_path):
    parent = prepared(config_path)
    assert engine.execute(parent, client_factory=FakeClient) == 0
    old_hash = sha(parent / "summary.json")
    run = parent.parent / "description-only"
    assert prepare_description_reassessment([parent], run)["tasks"] == 2
    old = {t["payload"]["target"]["name"]: t for t in read(parent / "tasks.json") if t["metric"] == "entity_description"}
    for task in read(run / "tasks.json"):
        assert task["payload"] == old[task["payload"]["target"]["name"]]["payload"]
    assert engine.execute(run, client_factory=FakeClient) == 0
    summary = read(run / "summary.json")
    assert set(summary["groups"]["system-a"]) == {"entity_description"}
    assert summary["groups"]["system-a"]["entity_description"]["rate"] == 1
    assert sha(parent / "summary.json") == old_hash
    assert "完整断言正确率" not in (run / "comparison.csv").read_text()
