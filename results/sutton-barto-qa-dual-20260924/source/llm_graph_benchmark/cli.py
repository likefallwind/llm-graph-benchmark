from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .adapters.llm_knowledge_graph import adapt_sqlite
from .agreement import judge_agreement
from .aggregation import aggregate_judgments
from .bundle import BenchmarkBundle, SubmissionBundle
from .comparison import compare_paired
from .identity import create_identity_tasks
from .io import read_json, read_jsonl, write_json, write_jsonl
from .metrics import submission_metrics
from .probes import create_fact_probe_tasks
from .qa import create_qa_tasks
from .quality import prepare_quality_tasks
from .report import markdown_report
from .retrieval import retrieve_fact_probes, retrieve_qa_probes
from .sampling import create_blind_sample
from .stability import compare_submissions
from .validation import validate_benchmark, validate_submission


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-graph-benchmark",
        description="Method-neutral evaluation for document-to-KG systems",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    workflow = commands.add_parser("workflow", help="Run the current selected-metrics workflow")
    actions = workflow.add_subparsers(dest="workflow_action", required=True)
    prepare = actions.add_parser("prepare", help="Freeze tasks locally; no API calls")
    prepare.add_argument("--config", required=True)
    prepare.add_argument("--run", required=True)
    for action in ("run", "launch", "status", "report"):
        command = actions.add_parser(action)
        command.add_argument("--run", required=True)
        if action in ("run", "launch"):
            command.add_argument("--retry-failed", action="store_true",
                                 help="Retry technical failures only, preserving successful labels")
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

    identity = commands.add_parser("identity-tasks")
    identity.add_argument("--benchmark", required=True)
    identity.add_argument("--submission", action="append", required=True)
    identity.add_argument("--aliases-per-document", type=int, default=30)
    identity.add_argument("--collision-pairs-per-document", type=int, default=30)
    identity.add_argument("--seed", type=int, default=0)
    identity.add_argument("--tasks-out", required=True)
    identity.add_argument("--key-out", required=True)

    probes = commands.add_parser("probe-tasks")
    probes.add_argument("--benchmark", required=True)
    probes.add_argument("--submission", action="append", required=True)
    probes.add_argument("--retrieval-results", required=True)
    probes.add_argument("--probes-per-document", type=int)
    probes.add_argument("--seed", type=int, default=0)
    probes.add_argument("--tasks-out", required=True)
    probes.add_argument("--key-out", required=True)

    retrieve = commands.add_parser("retrieve-lexical")
    retrieve.add_argument("--benchmark", required=True)
    retrieve.add_argument("--submission", action="append", required=True)
    retrieve.add_argument("--top-k", type=int, default=10)
    retrieve.add_argument("--k1", type=float, default=1.2)
    retrieve.add_argument("--b", type=float, default=0.75)
    retrieve.add_argument("--out", required=True)

    retrieve_qa = commands.add_parser("retrieve-qa-lexical")
    retrieve_qa.add_argument("--benchmark", required=True)
    retrieve_qa.add_argument("--submission", action="append", required=True)
    retrieve_qa.add_argument("--top-k", type=int, default=10)
    retrieve_qa.add_argument("--k1", type=float, default=1.2)
    retrieve_qa.add_argument("--b", type=float, default=0.75)
    retrieve_qa.add_argument("--out", required=True)

    qa_tasks = commands.add_parser("qa-tasks")
    qa_tasks.add_argument("--benchmark", required=True)
    qa_tasks.add_argument("--submission", action="append", required=True)
    qa_tasks.add_argument("--retrieval-results", required=True)
    qa_tasks.add_argument("--seed", type=int, default=0)
    qa_tasks.add_argument("--tasks-out", required=True)
    qa_tasks.add_argument("--key-out", required=True)

    metrics = commands.add_parser("metrics")
    metrics.add_argument("submission")
    metrics.add_argument("--benchmark", required=True)
    metrics.add_argument("--out")

    stability = commands.add_parser("compare-stability")
    stability.add_argument("--reference", required=True)
    stability.add_argument("--candidate", required=True)
    stability.add_argument("--reference-benchmark")
    stability.add_argument("--document-id", required=True)
    stability.add_argument("--out")

    aggregate = commands.add_parser("aggregate")
    aggregate.add_argument("--key", required=True)
    aggregate.add_argument("--judgments", required=True)
    aggregate.add_argument("--out")

    agreement = commands.add_parser("agreement")
    agreement.add_argument("--key", required=True)
    agreement.add_argument("--judgments", required=True)
    agreement.add_argument("--out")

    quality = commands.add_parser("quality-tasks", help="Prepare versioned blind judgments locally; no API calls")
    quality.add_argument("--version", choices=("v1", "v2", "v2.1", "v2.2"), default="v1")
    quality.add_argument("--tasks", required=True)
    quality.add_argument("--key", required=True)
    quality.add_argument("--tasks-out", required=True)
    quality.add_argument("--key-out", required=True)

    paired = commands.add_parser("compare-paired")
    paired.add_argument("--key", required=True)
    paired.add_argument("--judgments", required=True)
    paired.add_argument("--left", required=True)
    paired.add_argument("--right", required=True)
    paired.add_argument("--kind", default="fact_recovery_strict_v1")
    paired.add_argument("--judge-id", required=True)
    paired.add_argument("--out")

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
    adapt.add_argument("--qa-probes")
    adapt.add_argument("--source-id", type=int)
    adapt.add_argument("--allow-incomplete", action="store_true")
    adapt.add_argument("--filter-probes-to-scope", action="store_true")
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
        if args.command == "workflow":
            from .workflow.preparation import prepare, verify
            from .workflow.engine import execute, launch, status
            from .workflow.reporting import report as workflow_report
            action = args.workflow_action
            if action == "prepare":
                _print(prepare(args.config, args.run))
            elif action == "run":
                code = execute(args.run, retry_failed=args.retry_failed)
                _print(status(args.run))
                return code
            elif action == "launch":
                outcome = launch(args.run, retry_failed=args.retry_failed)
                _print(outcome)
                return 0 if outcome.get("worker_exit_code", 0) == 0 else outcome["worker_exit_code"]
            elif action == "status":
                _print(status(args.run))
            else:
                verify(args.run)
                result = workflow_report(args.run)
                _print({"run": str(Path(args.run).resolve()), "complete": result["complete"],
                        "done": result["done"], "total": result["total"]})
            return 0
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
        if args.command == "identity-tasks":
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
            output = create_identity_tasks(
                benchmark,
                submissions,
                aliases_per_document=args.aliases_per_document,
                collision_pairs_per_document=args.collision_pairs_per_document,
                seed=args.seed,
            )
            write_jsonl(args.tasks_out, output.tasks)
            write_jsonl(args.key_out, output.key)
            _print({"tasks": len(output.tasks), "tasks_out": args.tasks_out, "key_out": args.key_out})
            return 0
        if args.command == "retrieve-lexical":
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
            rows = retrieve_fact_probes(
                benchmark,
                submissions,
                top_k=args.top_k,
                k1=args.k1,
                b=args.b,
            )
            write_jsonl(args.out, rows)
            _print({"rows": len(rows), "output": args.out})
            return 0
        if args.command in {"retrieve-qa-lexical", "qa-tasks"}:
            benchmark = BenchmarkBundle.load(args.benchmark)
            if not validate_benchmark(benchmark).ok:
                raise ValueError("benchmark is invalid; run validate-benchmark for details")
            if not benchmark.qa_probes:
                raise ValueError("benchmark has no QA probes")
            submissions = []
            for path in args.submission:
                submission = SubmissionBundle.load(path)
                result = validate_submission(submission, benchmark)
                if not result.ok:
                    raise ValueError(f"invalid submission {path}: {result.as_dict()}")
                submissions.append(submission)
            _require_unique_systems(submissions)
            if args.command == "retrieve-qa-lexical":
                rows = retrieve_qa_probes(
                    benchmark,
                    submissions,
                    top_k=args.top_k,
                    k1=args.k1,
                    b=args.b,
                )
                write_jsonl(args.out, rows)
                _print({"rows": len(rows), "output": args.out})
            else:
                output = create_qa_tasks(
                    benchmark,
                    submissions,
                    read_jsonl(args.retrieval_results),
                    seed=args.seed,
                )
                write_jsonl(args.tasks_out, output.tasks)
                write_jsonl(args.key_out, output.key)
                _print(
                    {"tasks": len(output.tasks), "tasks_out": args.tasks_out, "key_out": args.key_out}
                )
            return 0
        if args.command == "metrics":
            _, submission = _valid_pair(args.benchmark, args.submission)
            result = submission_metrics(submission)
            if args.out:
                write_json(args.out, result)
            else:
                _print(result)
            return 0
        if args.command == "compare-stability":
            overlap_unit_ids = None
            if args.reference_benchmark:
                benchmark = BenchmarkBundle.load(args.reference_benchmark)
                overlap_unit_ids = set(
                    benchmark.unit_by_document.get(args.document_id, {})
                )
            result = compare_submissions(
                SubmissionBundle.load(args.reference),
                SubmissionBundle.load(args.candidate),
                document_id=args.document_id,
                overlap_unit_ids=overlap_unit_ids,
            )
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
        if args.command == "quality-tasks":
            input_paths = {Path(args.tasks).resolve(), Path(args.key).resolve()}
            output_paths = {Path(args.tasks_out).resolve(), Path(args.key_out).resolve()}
            if len(output_paths) != 2 or input_paths & output_paths:
                raise ValueError("use distinct output paths; never overwrite frozen input tasks")
            if any(path.exists() for path in output_paths):
                raise ValueError("quality output already exists; choose a new output directory")
            output = prepare_quality_tasks(read_jsonl(args.tasks), read_jsonl(args.key), version=args.version)
            write_jsonl(args.tasks_out, output.tasks)
            write_jsonl(args.key_out, output.key)
            _print({"status": "prepared-not-judged", "tasks": len(output.tasks)})
            return 0
        if args.command == "compare-paired":
            result = compare_paired(read_jsonl(args.key), read_jsonl(args.judgments),
                                    left=args.left, right=args.right, kind=args.kind, judge_id=args.judge_id)
            if args.out:
                write_json(args.out, result)
            else:
                _print(result)
            return 0 if result["status"] == "complete" else 1
        if args.command == "agreement":
            result = judge_agreement(read_jsonl(args.key), read_jsonl(args.judgments))
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
                qa_probes_path=args.qa_probes,
                source_id=args.source_id,
                allow_incomplete=args.allow_incomplete,
                filter_probes_to_scope=args.filter_probes_to_scope,
                chunk_chars=args.chunk_chars,
                overlap_chars=args.overlap_chars,
            )
            _print(result)
            return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
