from __future__ import annotations

import json

import pytest

from llm_graph_benchmark.cli import main


@pytest.mark.integration
def test_cli_end_to_end(benchmark_dir, submission_path, tmp_path):
    benchmark = benchmark_dir / "benchmark.json"
    tasks = tmp_path / "out" / "tasks.jsonl"
    key = tmp_path / "out" / "key.jsonl"
    metrics = tmp_path / "out" / "metrics.json"
    judged = tmp_path / "out" / "judged.json"
    report = tmp_path / "out" / "report.md"
    probe_tasks = tmp_path / "out" / "probe-tasks.jsonl"
    probe_key = tmp_path / "out" / "probe-key.jsonl"
    retrieval = tmp_path / "out" / "retrieval.jsonl"
    identity_tasks = tmp_path / "out" / "identity-tasks.jsonl"
    identity_key = tmp_path / "out" / "identity-key.jsonl"
    qa_retrieval = tmp_path / "out" / "qa-retrieval.jsonl"
    qa_tasks = tmp_path / "out" / "qa-tasks.jsonl"
    qa_key = tmp_path / "out" / "qa-key.jsonl"
    stability = tmp_path / "out" / "stability.json"
    agreement = tmp_path / "out" / "agreement.json"

    assert main(["validate-benchmark", str(benchmark)]) == 0
    assert main(
        ["validate-submission", str(submission_path), "--benchmark", str(benchmark)]
    ) == 0
    assert main(
        [
            "identity-tasks",
            "--benchmark",
            str(benchmark),
            "--submission",
            str(submission_path),
            "--tasks-out",
            str(identity_tasks),
            "--key-out",
            str(identity_key),
        ]
    ) == 0
    assert main(
        [
            "retrieve-qa-lexical",
            "--benchmark",
            str(benchmark),
            "--submission",
            str(submission_path),
            "--out",
            str(qa_retrieval),
        ]
    ) == 0
    assert main(
        [
            "qa-tasks",
            "--benchmark",
            str(benchmark),
            "--submission",
            str(submission_path),
            "--retrieval-results",
            str(qa_retrieval),
            "--tasks-out",
            str(qa_tasks),
            "--key-out",
            str(qa_key),
        ]
    ) == 0
    assert main(
        [
            "compare-stability",
            "--reference",
            str(submission_path),
            "--candidate",
            str(submission_path),
            "--reference-benchmark",
            str(benchmark),
            "--document-id",
            "doc-1",
            "--out",
            str(stability),
        ]
    ) == 0
    assert main(
        [
            "retrieve-lexical",
            "--benchmark",
            str(benchmark),
            "--submission",
            str(submission_path),
            "--top-k",
            "1",
            "--out",
            str(retrieval),
        ]
    ) == 0
    assert main(
        [
            "probe-tasks",
            "--benchmark",
            str(benchmark),
            "--submission",
            str(submission_path),
            "--retrieval-results",
            str(retrieval),
            "--tasks-out",
            str(probe_tasks),
            "--key-out",
            str(probe_key),
        ]
    ) == 0
    assert main(
        [
            "sample",
            "--benchmark",
            str(benchmark),
            "--submission",
            str(submission_path),
            "--tasks-out",
            str(tasks),
            "--key-out",
            str(key),
        ]
    ) == 0
    assert main(
        ["metrics", str(submission_path), "--benchmark", str(benchmark), "--out", str(metrics)]
    ) == 0
    key_rows = [json.loads(line) for line in key.read_text().splitlines()]
    judgments_path = tmp_path / "out" / "judgments.jsonl"
    judgments_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "task_id": row["task_id"],
                    "judge_id": "human-1",
                    "label": "pass",
                }
            )
            for row in key_rows
        )
        + "\n",
        encoding="utf-8",
    )
    assert main(
        ["aggregate", "--key", str(key), "--judgments", str(judgments_path), "--out", str(judged)]
    ) == 0
    assert main(
        ["agreement", "--key", str(key), "--judgments", str(judgments_path), "--out", str(agreement)]
    ) == 0
    assert main(
        ["report", "--metrics", str(metrics), "--judged", str(judged), "--out", str(report)]
    ) == 0
    assert "system-a" in report.read_text(encoding="utf-8")
