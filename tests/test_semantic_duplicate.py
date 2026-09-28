"""Semantic-duplicate stage: frozen candidates, strict pairwise judging, entity-level rate."""
import json

import pytest

from test_workflow import config_path, FakeClient, prepared, wire
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.cli import main
from llm_graph_benchmark.workflow import engine, identity_judge, protocol, semantic_duplicate as sd
from llm_graph_benchmark.workflow.preparation import read, sha
from llm_graph_benchmark.workflow.reporting import combine, report
from llm_graph_benchmark.workflow.transport import write


@pytest.fixture
def parent(config_path):
    path = config_path.parent / "submission.json"
    sub = read(path)
    entities = sub["documents"][0]["entities"]
    entities.append({"id": "e3", "name": "Gamma", "definition": "A third entity.",
                     "types": ["concept"], "evidence": [{"unit_id": "u1"}]})
    entities[1]["aliases"] = ["second one"]
    write(path, sub)
    run = prepared(config_path)
    assert engine.execute(run, client_factory=FakeClient) == 0
    return run


def keys_for(run):
    state = sd.load_parent(run)
    return state, {r["name"]: r["key"] for r in sd.target_sheet(state)}


def test_target_sheet_is_blinded_and_search_uses_names_only(parent):
    state, keys = keys_for(parent)
    sheet = sd.target_sheet(state)
    assert set(keys) == {"Alpha", "Beta", "Gamma"}
    assert "system-a" not in json.dumps(sheet) and "e1" not in json.dumps(sheet)
    expansions = {k: [] for k in keys.values()}
    expansions[keys["Alpha"]] = ["second one"]
    found = sd.candidates(state, expansions)
    alpha = [c["entity_id"] for c in found[keys["Alpha"]]["candidates"]]
    assert alpha == ["e2"]  # Matched Beta's alias; never the target itself or description words.
    assert sd.candidates(state, expansions) == found
    with pytest.raises(ValueError, match="cover exactly"):
        sd.candidates(state, {keys["Alpha"]: []})


def test_oversized_entities_leave_sample_and_pool(parent, monkeypatch):
    monkeypatch.setattr(sd, "SOURCE_LIMIT", 10)
    scope = sd.targets(sd.load_parent(parent))["system-a"]["doc-1"]
    assert scope["targets"] == [] and scope["pool"] == []
    assert sorted(scope["ineligible_targets"]) == ["e1", "e2", "e3"]


def prepare_stage(parent, flag_names=("Beta",)):
    state, keys = keys_for(parent)
    expansions = {k: [] for k in keys.values()}
    expansions[keys["Alpha"]] = ["second one"]
    found = sd.candidates(state, expansions)
    by_name = {e["id"]: e["name"] for e in state["submissions"]["system-a"].payload["documents"][0]["entities"]}
    screening = {k: [c["key"] for c in row["candidates"] if by_name[c["entity_id"]] in flag_names]
                 for k, row in found.items()}
    screening = {k: (v if k == keys["Alpha"] else []) for k, v in screening.items()}
    write(parent.parent / "expansions.json", expansions)
    write(parent.parent / "screening.json", screening)
    run = parent.parent / "semantic"
    sd.prepare(parent, parent.parent / "expansions.json", parent.parent / "screening.json", run)
    return run


def test_stage_judges_only_screened_pairs_with_native_sources(parent):
    run = prepare_stage(parent)
    tasks = read(run / "tasks.json")
    assert len(tasks) == 1
    task = tasks[0]
    assert task["messages"][0]["content"] == identity_judge.DUPLICATE_PROMPT
    shown = json.loads(task["messages"][1]["content"])
    assert shown["entity_a"]["name"] == "Alpha" and shown["entity_b"]["name"] == "Beta"
    assert shown["entity_a"]["evidence"] == [{"id": "u1", "text": "Alpha relates to beta."}]
    assert "system-a" not in task["messages"][1]["content"]
    assert "含义严格相同" in identity_judge.DUPLICATE_PROMPT
    assert "不能单独证明两者同指" in identity_judge.DUPLICATE_PROMPT


def test_rate_is_per_sampled_entity_and_uncertain_stays_in_denominator(parent):
    run = prepare_stage(parent)
    task = read(run / "tasks.json")[0]
    group = report(run)["groups"]["system-a"]["semantic_duplicate"]
    assert group["status"] == "incomplete" and group["rate"] is None
    for label, expected in (("pass", 1 / 3), ("uncertain", 0), ("fail", 0)):
        value = protocol.parse(wire({"label": label, "confidence": 1, "reason": "fixture"}), task)
        write(run / "results" / (task["id"] + ".json"),
              {"task_id": task["id"], "task_hash": canonical_hash(task), "status": "done",
               "value": value, "value_hash": canonical_hash(value)})
        group = report(run)["groups"]["system-a"]["semantic_duplicate"]
        assert group["denominator"] == 3 and group["rate"] == expected
        if label == "uncertain":
            assert group["labels"] == {"uncertain": 1, "none": 2} and group["uncertain_rate"] == 1 / 3
    text = (run / "REPORT.md").read_text()
    assert "语义重复率（越低越好）" in text and "完整断言正确率" not in text


def test_bad_screening_is_rejected(parent):
    state, keys = keys_for(parent)
    expansions = {k: [] for k in keys.values()}
    write(parent.parent / "expansions.json", expansions)
    write(parent.parent / "screening.json", {k: (["c-invented"] if n == "Alpha" else []) for n, k in keys.items()})
    with pytest.raises(ValueError, match="distinct candidates"):
        sd.prepare(parent, parent.parent / "expansions.json", parent.parent / "screening.json",
                   parent.parent / "bad")


def test_engine_runs_stage_and_combine_drops_retired_split(parent):
    run = prepare_stage(parent)
    assert engine.execute(run, client_factory=FakeClient) == 0  # Fake judge says pass.
    summary = read(run / "summary.json")
    assert set(summary["groups"]["system-a"]) == {"semantic_duplicate"}
    assert summary["groups"]["system-a"]["semantic_duplicate"]["rate"] == 1 / 3
    parent_summary = sha(parent / "summary.json")
    out = parent.parent / "combined"
    combined = combine(parent, run, out)
    assert sha(parent / "summary.json") == parent_summary
    groups = combined["groups"]["system-a"]
    assert groups["semantic_duplicate"]["numerator"] == 1
    assert groups["assertion_correctness"]["rate"] == 1
    text = (out / "REPORT.md").read_text()
    assert "语义重复率（越低越好）" in text and "完整断言正确率" in text and "实体拆分正确率" not in text


def test_cli_stage_commands(parent, capsys):
    base = parent.parent
    assert main(["workflow", "semantic-targets", "--parent", str(parent), "--out", str(base / "t.json")]) == 0
    rows = read(base / "t.json")
    write(base / "e.json", {r["key"]: [] for r in rows})
    assert main(["workflow", "semantic-candidates", "--parent", str(parent), "--expansions",
                 str(base / "e.json"), "--out", str(base / "s.json")]) == 0
    write(base / "f.json", {r["key"]: [] for r in rows})
    assert main(["workflow", "semantic-prepare", "--parent", str(parent), "--expansions", str(base / "e.json"),
                 "--screening", str(base / "f.json"), "--run", str(base / "stage")]) == 0
    assert main(["workflow", "run", "--run", str(base / "stage")]) == 0
    group = read(base / "stage" / "summary.json")["groups"]["system-a"]["semantic_duplicate"]
    assert group["rate"] == 0 and group["denominator"] == 3
    assert main(["workflow", "combine", "--parent", str(parent), "--stage", str(base / "stage"),
                 "--out", str(base / "both")]) == 0
