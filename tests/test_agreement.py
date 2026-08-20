from __future__ import annotations

from llm_graph_benchmark.agreement import judge_agreement


def test_judge_agreement_reports_pairwise_kappa():
    key = [
        {"task_id": "t1", "kind": "entity_typing"},
        {"task_id": "t2", "kind": "entity_typing"},
        {"task_id": "t3", "kind": "entity_typing"},
        {"task_id": "t4", "kind": "entity_typing"},
    ]
    judgments = [
        {"task_id": "t1", "judge_id": "a", "label": "pass"},
        {"task_id": "t2", "judge_id": "a", "label": "pass"},
        {"task_id": "t3", "judge_id": "a", "label": "fail"},
        {"task_id": "t4", "judge_id": "a", "label": "fail"},
        {"task_id": "t1", "judge_id": "b", "label": "pass"},
        {"task_id": "t2", "judge_id": "b", "label": "pass"},
        {"task_id": "t3", "judge_id": "b", "label": "fail"},
        {"task_id": "t4", "judge_id": "b", "label": "pass"},
    ]
    result = judge_agreement(key, judgments)["dimensions"]["entity_typing"]
    assert result["mean_pairwise_agreement"] == 0.75
    assert result["mean_pairwise_cohen_kappa"] == 0.5
