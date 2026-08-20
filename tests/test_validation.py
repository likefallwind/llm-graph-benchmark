from __future__ import annotations

import json

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.validation import validate_benchmark, validate_submission


def test_valid_benchmark_has_no_issues(benchmark_dir):
    result = validate_benchmark(BenchmarkBundle.load(benchmark_dir / "benchmark.json"))
    assert result.ok


def test_submission_rejects_unknown_evidence_unit(
    benchmark_dir, submission_path, submission_payload
):
    submission_payload["documents"][0]["entities"][0]["evidence"][0]["unit_id"] = "missing"
    submission_path.write_text(json.dumps(submission_payload), encoding="utf-8")
    result = validate_submission(
        SubmissionBundle.load(submission_path),
        BenchmarkBundle.load(benchmark_dir / "benchmark.json"),
    )
    assert any(issue.code == "unknown_unit" for issue in result.issues)


def test_submission_rejects_unknown_assertion_endpoint(
    benchmark_dir, submission_path, submission_payload
):
    submission_payload["documents"][0]["assertions"][0]["object_id"] = "missing"
    submission_path.write_text(json.dumps(submission_payload), encoding="utf-8")
    result = validate_submission(
        SubmissionBundle.load(submission_path),
        BenchmarkBundle.load(benchmark_dir / "benchmark.json"),
    )
    assert any(issue.code == "unknown_entity" for issue in result.issues)


def test_submission_rejects_benchmark_mismatch(
    benchmark_dir, submission_path, submission_payload
):
    submission_payload["benchmark_id"] = "another-benchmark"
    submission_path.write_text(json.dumps(submission_payload), encoding="utf-8")
    result = validate_submission(
        SubmissionBundle.load(submission_path),
        BenchmarkBundle.load(benchmark_dir / "benchmark.json"),
    )
    assert any(issue.code == "benchmark_mismatch" for issue in result.issues)
