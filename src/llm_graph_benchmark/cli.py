from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .adapters.llm_knowledge_graph import adapt_sqlite
from .aggregation import aggregate_judgments
from .bundle import BenchmarkBundle, SubmissionBundle
from .io import read_json, read_jsonl, write_json, write_jsonl
from .metrics import submission_metrics
from .probes import create_fact_probe_tasks
from .report import markdown_report
from .sampling import create_blind_sample
from .validation import validate_benchmark, validate_submission


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-graph-benchmark",
        description="Method-neutral evaluation for document-to-KG systems",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check_benchmark = commands.add_parser("validate-benchmark")
    check_benchmark.add_argument("benchmark")
    check_submission = commands.add_parser("validate-submission")
    check_submission.add_argument("submission")
    check_submission.add_argument("--benchmark", required=True)

    sample = commands.add_parser("sample")
    sample.add_argument("--benchmark", required=True)
    sample.add_argument("--submission", action="append", required=True)
    sample.add_argument("--entities-per-document", type=int, default=30)
    sample.add_argument("--assertions-per-document", type=int, default=30)
    sample.add_argument("--seed", type=int, default=0)
    sample.add_argument("--tasks-out", required=True)
    sample.add_argument("--key-out", required=True)

    probes = commands.add_parser("probe-tasks")
    probes.add_argument("--benchmark", required=True)
    probes.add_argument("--submission", action="append", required=True)
    probes.add_argument("--retrieval-results", required=True)
    probes.add_argument("--probes-per-document", type=int)
    probes.add_argument("--seed", type=int, default=0)
    probes.add_argument("--tasks-out", required=True)
    probes.add_argument("--key-out", required=True)

    metrics = commands.add_parser("metrics")
    metrics.add_argument("submission")
    metrics.add_argument("--benchmark", required=True)
    metrics.add_argument("--out")

    aggregate = commands.add_parser("aggregate")
    aggregate.add_argument("--key", required=True)
    aggregate.add_argument("--judgments", required=True)
    aggregate.add_argument("--out")

    report = commands.add_parser("report")
    report.add_argument("--metrics", action="append", required=True)
    report.add_argument("--judged")
    report.add_argument("--out", required=True)

    adapt = commands.add_parser("adapt-llmkg-sqlite")
    adapt.add_argument("--db", required=True)
    adapt.add_argument("--out-dir", required=True)
    adapt.add_argument("--benchmark-id", required=True)
    adapt.add_argument("--system-id", required=True)
    adapt.add_argument("--system-name", required=True)
    adapt.add_argument("--system-version", required=True)
    adapt.add_argument("--fact-probes", required=True)
    adapt.add_argument("--source-id", type=int)
    adapt.add_argument("--allow-incomplete", action="store_true")
    adapt.add_argument("--chunk-chars", type=int, default=8000)
    adapt.add_argument("--overlap-chars", type=int, default=500)
    return parser


def _valid_pair(benchmark_path: str, submission_path: str) -> tuple[BenchmarkBundle, SubmissionBundle]:
    benchmark = BenchmarkBundle.load(benchmark_path)
    benchmark_result = validate_benchmark(benchmark)
    if not benchmark_result.ok:
        raise ValueError(json.dumps(benchmark_result.as_dict(), ensure_ascii=False))
    submission = SubmissionBundle.load(submission_path)
    submission_result = validate_submission(submission, benchmark)
    if not submission_result.ok:
        raise ValueError(json.dumps(submission_result.as_dict(), ensure_ascii=False))
    return benchmark, submission


def _require_unique_systems(submissions: list[SubmissionBundle]) -> None:
    system_ids = [item.system_id for item in submissions]
    duplicates = sorted({item for item in system_ids if system_ids.count(item) > 1})
    if duplicates:
        raise ValueError(f"duplicate system_id across submissions: {duplicates}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-benchmark":
            result = validate_benchmark(BenchmarkBundle.load(args.benchmark))
            _print(result.as_dict())
            return 0 if result.ok else 1
        if args.command == "validate-submission":
            benchmark = BenchmarkBundle.load(args.benchmark)
            result = validate_submission(SubmissionBundle.load(args.submission), benchmark)
            _print(result.as_dict())
            return 0 if result.ok else 1
        if args.command == "sample":
            benchmark = BenchmarkBundle.load(args.benchmark)
            if not validate_benchmark(benchmark).ok:
                raise ValueError("benchmark is invalid; run validate-benchmark for details")
            submissions = []
            for path in args.submission:
                submission = SubmissionBundle.load(path)
                result = validate_submission(submission, benchmark)
                if not result.ok:
                    raise ValueError(f"invalid submission {path}: {result.as_dict()}")
                submissions.append(submission)
            _require_unique_systems(submissions)
            output = create_blind_sample(
                benchmark,
                submissions,
                entities_per_document=args.entities_per_document,
                assertions_per_document=args.assertions_per_document,
                seed=args.seed,
            )
            write_jsonl(args.tasks_out, output.tasks)
            write_jsonl(args.key_out, output.key)
            _print({"tasks": len(output.tasks), "tasks_out": args.tasks_out, "key_out": args.key_out})
            return 0
        if args.command == "probe-tasks":
            benchmark = BenchmarkBundle.load(args.benchmark)
            if not validate_benchmark(benchmark).ok:
                raise ValueError("benchmark is invalid; run validate-benchmark for details")
            submissions = []
            for path in args.submission:
                submission = SubmissionBundle.load(path)
                result = validate_submission(submission, benchmark)
                if not result.ok:
                    raise ValueError(f"invalid submission {path}: {result.as_dict()}")
                submissions.append(submission)
            _require_unique_systems(submissions)
            output = create_fact_probe_tasks(
                benchmark,
                submissions,
                read_jsonl(args.retrieval_results),
                probes_per_document=args.probes_per_document,
                seed=args.seed,
            )
            write_jsonl(args.tasks_out, output.tasks)
            write_jsonl(args.key_out, output.key)
            _print({"tasks": len(output.tasks), "tasks_out": args.tasks_out, "key_out": args.key_out})
            return 0
        if args.command == "metrics":
            _, submission = _valid_pair(args.benchmark, args.submission)
            result = submission_metrics(submission)
            if args.out:
                write_json(args.out, result)
            else:
                _print(result)
            return 0
        if args.command == "aggregate":
            result = aggregate_judgments(read_jsonl(args.key), read_jsonl(args.judgments))
            if args.out:
                write_json(args.out, result)
            else:
                _print(result)
            return 0
        if args.command == "report":
            metric_payloads = [read_json(path) for path in args.metrics]
            judged = read_json(args.judged) if args.judged else None
            output = Path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(markdown_report(metric_payloads, judged), encoding="utf-8")
            _print({"output": str(output)})
            return 0
        if args.command == "adapt-llmkg-sqlite":
            result = adapt_sqlite(
                args.db,
                args.out_dir,
                benchmark_id=args.benchmark_id,
                system_id=args.system_id,
                system_name=args.system_name,
                system_version=args.system_version,
                fact_probes_path=args.fact_probes,
                source_id=args.source_id,
                allow_incomplete=args.allow_incomplete,
                chunk_chars=args.chunk_chars,
                overlap_chars=args.overlap_chars,
            )
            _print(result)
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
