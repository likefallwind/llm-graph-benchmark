from __future__ import annotations

import pytest

from llm_graph_benchmark.aggregation import aggregate_judgments


def test_aggregation_uses_majority_vote_and_excludes_uncertain():
    key = [
        {"task_id": "t1", "system_id": "a", "kind": "entity_admission"},
        {"task_id": "t2", "system_id": "a", "kind": "entity_admission"},
    ]
    judgments = [
        {"task_id": "t1", "judge_id": "j1", "label": "pass"},
        {"task_id": "t1", "judge_id": "j2", "label": "pass"},
        {"task_id": "t1", "judge_id": "j3", "label": "fail"},
        {"task_id": "t2", "judge_id": "j1", "label": "uncertain"},
    ]
    result = aggregate_judgments(key, judgments)
    score = result["systems"]["a"]["entity_admission"]
    assert score["pass"] == 1
    assert score["uncertain"] == 1
    assert score["unjudged"] == 0
    assert score["pass_rate"] == 1.0


def test_aggregation_reports_missing_judgments():
    key = [
        {"task_id": "t1", "system_id": "a", "kind": "entity_admission"},
        {"task_id": "t2", "system_id": "a", "kind": "entity_admission"},
    ]
    judgments = [{"task_id": "t1", "judge_id": "j1", "label": "pass"}]
    result = aggregate_judgments(key, judgments)
    score = result["systems"]["a"]["entity_admission"]
    assert result["unjudged_task_count"] == 1
    assert score["unjudged"] == 1


def test_aggregation_rejects_duplicate_judge_vote():
    key = [{"task_id": "t1", "system_id": "a", "kind": "entity_admission"}]
    judgments = [
        {"task_id": "t1", "judge_id": "j1", "label": "pass"},
        {"task_id": "t1", "judge_id": "j1", "label": "fail"},
    ]
    with pytest.raises(ValueError, match="duplicate judgment"):
        aggregate_judgments(key, judgments)


def test_aggregation_rejects_duplicate_task_key():
    key = [
        {"task_id": "t1", "system_id": "a", "kind": "entity_admission"},
        {"task_id": "t1", "system_id": "b", "kind": "entity_admission"},
    ]
    with pytest.raises(ValueError, match="duplicate task_id"):
        aggregate_judgments(key, [])


def test_aggregation_reports_scores_by_frozen_strata():
    key = [
        {
            "task_id": "t1",
            "system_id": "a",
            "kind": "fact_recovery",
            "strata": {"complexity": "atomic", "position_band": "early"},
        },
        {
            "task_id": "t2",
            "system_id": "a",
            "kind": "fact_recovery",
            "strata": {"complexity": "scoped", "position_band": "early"},
        },
    ]
    judgments = [
        {"task_id": "t1", "judge_id": "j1", "label": "pass"},
        {"task_id": "t2", "judge_id": "j1", "label": "fail"},
    ]

    result = aggregate_judgments(key, judgments)

    complexity = result["strata"]["a"]["fact_recovery"]["complexity"]
    assert complexity["atomic"]["pass_rate"] == 1.0
    assert complexity["scoped"]["pass_rate"] == 0.0
    assert result["strata"]["a"]["fact_recovery"]["position_band"]["early"][
        "expected"
    ] == 2
