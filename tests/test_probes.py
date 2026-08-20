from __future__ import annotations

import pytest

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.probes import create_fact_probe_tasks


def test_fact_probe_task_is_blind_and_contains_candidates(
    benchmark_dir, submission_path
):
    benchmark = BenchmarkBundle.load(benchmark_dir / "benchmark.json")
    submission = SubmissionBundle.load(submission_path)
    output = create_fact_probe_tasks(
        benchmark,
        [submission],
        [
            {
                "system_id": "system-a",
                "probe_id": "p1",
                "retriever": "test-retriever-v1",
                "assertion_ids": ["a1"],
            }
        ],
        probes_per_document=None,
        seed=7,
    )
    assert output.tasks[0]["kind"] == "fact_recovery"
    assert output.tasks[0]["content"]["candidate_graph_assertions"][0]["subject"] == "Alpha"
    assert "system_id" not in output.tasks[0]
    assert output.key[0]["retriever"] == "test-retriever-v1"
    assert output.key[0]["strata"] == {}


def test_fact_probe_task_rejects_unknown_candidate(
    benchmark_dir, submission_path
):
    benchmark = BenchmarkBundle.load(benchmark_dir / "benchmark.json")
    submission = SubmissionBundle.load(submission_path)
    with pytest.raises(ValueError, match="unknown assertion"):
        create_fact_probe_tasks(
            benchmark,
            [submission],
            [
                {
                    "system_id": "system-a",
                    "probe_id": "p1",
                    "retriever": "test-retriever-v1",
                    "assertion_ids": ["missing"],
                }
            ],
            probes_per_document=None,
            seed=0,
        )
