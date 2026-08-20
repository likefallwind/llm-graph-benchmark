from __future__ import annotations

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.retrieval import RETRIEVER_ID, retrieve_fact_probes


def test_lexical_retriever_uses_graph_text_and_is_deterministic(
    benchmark_dir, submission_path
):
    benchmark = BenchmarkBundle.load(benchmark_dir / "benchmark.json")
    submission = SubmissionBundle.load(submission_path)

    first = retrieve_fact_probes(benchmark, [submission], top_k=1)
    second = retrieve_fact_probes(benchmark, [submission], top_k=1)

    assert first == second
    assert first[0]["retriever"] == RETRIEVER_ID
    assert first[0]["assertion_ids"] == ["a1"]
    assert set(first[0]) == {
        "system_id",
        "probe_id",
        "retriever",
        "assertion_ids",
        "retriever_params",
    }
