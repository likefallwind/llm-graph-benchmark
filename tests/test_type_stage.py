"""Two-level type granularity and the type re-judging stage of a completed run."""
import pytest

from test_semantic_duplicate import parent, prepare_stage
from test_workflow import config_path, FakeClient, wire
from llm_graph_benchmark.cli import main
from llm_graph_benchmark.workflow import engine, protocol, type_stage
from llm_graph_benchmark.workflow.preparation import read
from llm_graph_benchmark.workflow.reporting import combine
from llm_graph_benchmark.workflow.transport import write


def type_task():
    types = [{"type_id": "type-0", "type_text": "algorithm"}]
    return {"metric": "entity_typing",
            "payload": {"target": {"name": "Q-learning", "types": types}, "evidence": [{"id": "u1", "text": "x"}]}}


def test_only_two_type_levels_are_accepted():
    row = {"type_id": "type-0", "type_text": "algorithm", "label": "pass",
           "reason": "fits", "evidence_ids": ["u1"]}
    assert protocol.parse(wire({"items": [{**row, "level": "L1"}]}), type_task())["label"] == "pass"
    with pytest.raises(ValueError):
        protocol.parse(wire({"items": [{**row, "level": "L3"}]}), type_task())
    assert "只评价类型标签本身" in protocol.TYPES


def test_stage_rejudges_the_parents_type_tasks_and_combines(parent):
    parent_types = {t["id"]: t for t in read(parent / "tasks.json") if t["metric"] == "entity_typing"}
    run = parent.parent / "types"
    result = type_stage.prepare(parent, run)
    tasks = read(run / "tasks.json")
    assert result["tasks"] == len(tasks) == len(parent_types)
    # Same sample, labels and evidence; the parent here already uses the current version.
    assert {t["id"]: t["payload"] for t in tasks} == {i: t["payload"] for i, t in parent_types.items()}
    assert engine.execute(run, client_factory=FakeClient) == 0
    summary = read(run / "summary.json")
    assert set(summary["groups"]["system-a"]) == {"entity_typing"}
    assert set(summary["groups"]["system-a"]["entity_typing"]["finest_supported_type"]) <= {"L1", "L2", "none"}
    semantic = prepare_stage(parent)
    assert engine.execute(semantic, client_factory=FakeClient) == 0
    combined = combine(parent, [semantic, run], parent.parent / "both")
    assert [s["metric"] for s in combined["composed_from"]["stages"]] == ["semantic_duplicate", "entity_typing"]
    assert combined["groups"]["system-a"]["entity_typing"] == summary["groups"]["system-a"]["entity_typing"]
    text = (parent.parent / "both" / "REPORT.md").read_text()
    assert "正确且 L2 类型覆盖" in text and "最具体正确类型 L3" not in text
    with pytest.raises(ValueError, match="same metric"):
        combine(parent, [run, run], parent.parent / "twice")


def test_three_level_type_results_cannot_be_reported(parent):
    summary = read(parent / "summary.json")
    summary["groups"]["system-a"]["entity_typing"]["finest_supported_type"] = {"L3": 1}
    write(parent / "summary.json", summary)
    with pytest.raises(ValueError, match="older version"):
        combine(parent, [], parent.parent / "old")
    assert not (parent.parent / "old").exists()


def test_cli_type_stage_and_repeated_stage_flags(parent, monkeypatch):
    monkeypatch.setattr(engine.transport, "Client", FakeClient)
    base = parent.parent
    assert main(["workflow", "type-prepare", "--parent", str(parent), "--run", str(base / "t")]) == 0
    assert main(["workflow", "run", "--run", str(base / "t")]) == 0
    semantic = prepare_stage(parent)
    assert main(["workflow", "run", "--run", str(semantic)]) == 0
    assert main(["workflow", "combine", "--parent", str(parent), "--stage", str(semantic),
                 "--stage", str(base / "t"), "--out", str(base / "c")]) == 0
    assert read(base / "c" / "summary.json")["metric_versions"]["entity_typing"] == "type-boundary-v3-two-level"
