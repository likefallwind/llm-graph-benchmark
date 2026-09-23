from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


STUDY = Path(__file__).resolve().parents[1] / "studies/d2l-reliability-20260920/sampling.py"
spec = importlib.util.spec_from_file_location("reliability_sampling_tested", STUDY)
sampling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampling)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


@pytest.fixture
def frozen_repo(tmp_path, monkeypatch):
    repo = tmp_path / "benchmark"
    units = [{"unit_id": f"P{i}", "text": f"Full parent paragraph {i}, not just quoted text."}
             for i in range(4)]
    save(repo / sampling.OURS / "documents.jsonl", {"document_id": "d", "units": units})
    for system, path in sampling._input_paths(repo).items():
        entities = [{"id": f"e{i}", "name": f"{system} entity {i}",
                     "definition": "Placeholder" if system == "kggen" else f"Definition {i}",
                     "metadata": {"definition_available": system != "kggen"},
                     "evidence": [{"unit_id": "P1", "quote": "paragraph"}, {"unit_id": "P1"}]}
                    for i in range(4)]
        assertions = [{"id": f"a{i}", "subject_id": "e0", "object_id": "e1",
                       "predicate": "related_to", "text": f"{system} assertion {i}",
                       "scope": "under a condition", "polarity": "positive",
                       "evidence": [{"unit_id": "P1"}]}
                      for i in range(5)]
        save(path, {"system": {"id": f"native-{system}"}, "documents": [{
            "document_id": "d", "entities": entities, "assertions": assertions}]})
    monkeypatch.setattr(sampling, "_history_paths", lambda _: [])
    return repo


def test_excludes_prior_ids_entity_names_and_unlabelled_fact_candidates(frozen_repo, monkeypatch):
    history = frozen_repo / "history.json"
    save(history, {
        "quality_key": [{"system_id": "native-ours", "kind": "assertion_quality_v2_2",
                         "document_id": "d", "item_id": "a0"}],
        "fact_tasks": [{"kind": "fact_recovery", "content": {"candidate_graph_assertions": [{
            "subject": "ours entity 0", "predicate": "related_to", "object": "ours entity 1",
            "text": "ours assertion 1", "scope": "under a condition", "polarity": "positive"}]}}],
        "old_entity": {"kind": "entity", "payload": {"target": {"name": "ours entity 2"}}},
    })
    monkeypatch.setattr(sampling, "_history_paths", lambda _: [history])
    result = sampling.prepare_samples(frozen_repo, entities=3, assertions=3)
    ours = {(row["kind"], row["item_id"]) for row in result["key"].values() if row["system"] == "ours"}
    assert ("entity", "e2") not in ours
    assert not {("assertion", "a0"), ("assertion", "a1")} & ours
    assert result["sampling"]["groups"]["ours"]["assertion"]["excluded"] == 2
    assert str(history) in result["sources"]


def test_entity_name_only_hides_placeholder_and_keeps_definition_audit(frozen_repo):
    result = sampling.prepare_samples(frozen_repo, entities=4, assertions=1)
    entities = [task for task in result["tasks"] if task["payload"]["kind"] == "entity"]
    assert all(set(task["payload"]["target"]) == {"name"} for task in entities)
    audits = [row["audit"] for row in result["key"].values()
              if row["system"] == "kggen" and row["kind"] == "entity"]
    assert all(not audit["definition_available"] and audit["definition"] is None for audit in audits)
    other = [row["audit"] for row in result["key"].values()
             if row["system"] == "ours" and row["kind"] == "entity"]
    assert all(audit["definition_available"] and audit["definition"].startswith("Definition") for audit in other)


def test_citations_are_deduplicated_parents_context_is_separate_and_targets_complete(frozen_repo):
    result = sampling.prepare_samples(frozen_repo, entities=1, assertions=1)
    for task in result["tasks"]:
        payload = task["payload"]
        assert [row["id"] for row in payload["submitted_sources"]] == ["P1"]
        assert [row["id"] for row in payload["reference_context"]] == ["P0", "P1", "P2"]
        assert payload["submitted_sources"][0]["text"].startswith("Full parent paragraph")
        assert not {"system", "system_id", "audit", "item_id", "doc_id"} & payload.keys()
        if payload["kind"] == "assertion":
            assert set(payload["target"]) == {"subject", "predicate", "object", "description", "scope", "polarity"}
            assert payload["target"]["scope"] == "under a condition"


def test_sampling_is_reproducible_and_input_order_independent(frozen_repo):
    before = sampling.prepare_samples(frozen_repo, entities=2, assertions=2)
    for path in sampling._input_paths(frozen_repo).values():
        data = json.loads(path.read_text())
        data["documents"][0]["entities"].reverse()
        data["documents"][0]["assertions"].reverse()
        save(path, data)
    after = sampling.prepare_samples(frozen_repo, entities=2, assertions=2)
    assert before["tasks"] == after["tasks"]
    assert before["key"] == after["key"]
    assert len(set(task["id"] for task in before["tasks"])) == len(before["tasks"])


def test_exhausted_pool_fails_instead_of_reusing_seen_items(frozen_repo, monkeypatch):
    history = frozen_repo / "history.json"
    save(history, [{"system": "ours", "kind": "entity", "item_id": f"e{i}"} for i in range(3)])
    monkeypatch.setattr(sampling, "_history_paths", lambda _: [history])
    with pytest.raises(ValueError, match="only 1 unseen eligible"):
        sampling.prepare_samples(frozen_repo, entities=2, assertions=1)


def test_oversized_and_missing_citations_stay_in_selected_sample(frozen_repo, monkeypatch):
    path = sampling._input_paths(frozen_repo)["ours"]
    data = json.loads(path.read_text())
    data["documents"][0]["entities"][0]["evidence"] = []
    save(path, data)
    monkeypatch.setattr(sampling, "SOURCE_CHARACTER_LIMIT", 1)
    result = sampling.prepare_samples(frozen_repo, entities=4, assertions=5)
    assert len(result["tasks"]) == 36
    assert result["sampling"]["replacements"] == 0
    task = next(task for task in result["tasks"]
                if result["key"][task["id"]]["system"] == "ours"
                and result["key"][task["id"]]["kind"] == "entity"
                and result["key"][task["id"]]["item_id"] == "e0")
    assert task["payload"]["submitted_sources"] == []
    assert task["payload"]["reference_context"] == []
    assert result["sampling"]["oversized_selected"] == 35


def test_unknown_native_citation_aborts_without_repair(frozen_repo):
    path = sampling._input_paths(frozen_repo)["ours"]
    data = json.loads(path.read_text())
    data["documents"][0]["entities"][0]["evidence"] = [{"unit_id": "missing"}]
    save(path, data)
    with pytest.raises(ValueError, match="Unknown native evidence"):
        sampling.prepare_samples(frozen_repo, entities=4, assertions=1)
