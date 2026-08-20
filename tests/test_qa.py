from __future__ import annotations

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.qa import create_qa_tasks
from llm_graph_benchmark.retrieval import retrieve_qa_probes


def test_book_qa_retrieval_and_task_are_blind(benchmark_dir, submission_path):
    benchmark = BenchmarkBundle.load(benchmark_dir / "benchmark.json")
    submission = SubmissionBundle.load(submission_path)
    retrieval = retrieve_qa_probes(benchmark, [submission], top_k=1)
    output = create_qa_tasks(benchmark, [submission], retrieval, seed=9)
    assert retrieval[0]["assertion_ids"] == ["a1"]
    assert output.tasks[0]["kind"] == "book_qa"
    assert output.tasks[0]["content"]["question"] == "What relates to beta?"
    assert "system_id" not in output.tasks[0]
    assert output.key[0]["system_id"] == "system-a"
