from __future__ import annotations

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.sampling import create_blind_sample


def test_blind_sample_is_reproducible_and_hides_system(
    benchmark_dir, submission_path
):
    benchmark = BenchmarkBundle.load(benchmark_dir / "benchmark.json")
    submission = SubmissionBundle.load(submission_path)
    first = create_blind_sample(
        benchmark,
        [submission],
        entities_per_document=1,
        assertions_per_document=1,
        seed=42,
    )
    second = create_blind_sample(
        benchmark,
        [submission],
        entities_per_document=1,
        assertions_per_document=1,
        seed=42,
    )
    assert first == second
    assert all("system_id" not in task for task in first.tasks)
    assert {item["kind"] for item in first.tasks} == {
        "entity_admission",
        "entity_typing",
        "entity_definition_grounding",
        "assertion_grounding",
    }
    assert len(first.tasks) == 4


def test_blind_sample_rejects_negative_limit(benchmark_dir, submission_path):
    benchmark = BenchmarkBundle.load(benchmark_dir / "benchmark.json")
    submission = SubmissionBundle.load(submission_path)
    try:
        create_blind_sample(
            benchmark,
            [submission],
            entities_per_document=-1,
            assertions_per_document=1,
            seed=0,
        )
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative sample limit must fail")
