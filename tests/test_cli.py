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

    assert main(["validate-benchmark", str(benchmark)]) == 0
    assert main(
        ["validate-submission", str(submission_path), "--benchmark", str(benchmark)]
    ) == 0
    retrieval = tmp_path / "retrieval.jsonl"
    retrieval.write_text(
        json.dumps(
            {
                "system_id": "system-a",
                "probe_id": "p1",
                "retriever": "test-v1",
                "assertion_ids": ["a1"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
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
        ["report", "--metrics", str(metrics), "--judged", str(judged), "--out", str(report)]
    ) == 0
    assert "system-a" in report.read_text(encoding="utf-8")
