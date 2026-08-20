from __future__ import annotations

import json

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.identity import create_identity_tasks, document_identity_metrics


def test_identity_tasks_cover_aliases_and_ambiguous_splits(
    benchmark_dir, submission_path, submission_payload
):
    submission_payload["documents"][0]["entities"][0]["aliases"] = ["A", "Shared"]
    submission_payload["documents"][0]["entities"][1]["aliases"] = ["Shared"]
    submission_path.write_text(json.dumps(submission_payload), encoding="utf-8")
    output = create_identity_tasks(
        BenchmarkBundle.load(benchmark_dir / "benchmark.json"),
        [SubmissionBundle.load(submission_path)],
        aliases_per_document=10,
        collision_pairs_per_document=10,
        seed=7,
    )
    assert {task["kind"] for task in output.tasks} == {
        "alias_identity",
        "identity_split",
    }
    assert all("system_id" not in task for task in output.tasks)
    split = next(task for task in output.tasks if task["kind"] == "identity_split")
    assert split["content"]["shared_surfaces"] == ["shared"]


def test_identity_metrics_count_ambiguous_surfaces(submission_payload):
    document = submission_payload["documents"][0]
    document["entities"][0]["aliases"] = ["Shared"]
    document["entities"][1]["aliases"] = ["Shared"]
    result = document_identity_metrics(document)
    assert result["ambiguous_surface_group_count"] == 1
    assert result["entities_in_ambiguous_surface_groups"] == 2
