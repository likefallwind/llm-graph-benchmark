from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.identity import create_identity_tasks
from llm_graph_benchmark.io import write_json, write_jsonl
from llm_graph_benchmark.metrics import submission_metrics
from llm_graph_benchmark.probes import create_fact_probe_tasks
from llm_graph_benchmark.qa import create_qa_tasks
from llm_graph_benchmark.retrieval import retrieve_fact_probes, retrieve_qa_probes
from llm_graph_benchmark.sampling import create_blind_sample
from llm_graph_benchmark.validation import validate_benchmark, validate_submission


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()

    benchmark = BenchmarkBundle.load(args.benchmark)
    submission = SubmissionBundle.load(args.submission)
    bv = validate_benchmark(benchmark)
    sv = validate_submission(submission, benchmark)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "validation.json", {"benchmark": bv.as_dict(), "submission": sv.as_dict()})
    if not bv.ok or not sv.ok:
        raise ValueError("benchmark or submission validation failed")
    write_json(args.out_dir / "structural-metrics.json", submission_metrics(submission))
    sample = create_blind_sample(benchmark, [submission], entities_per_document=30, assertions_per_document=30, seed=args.seed)
    write_jsonl(args.out_dir / "tasks.jsonl", sample.tasks)
    write_jsonl(args.out_dir / "task-key.jsonl", sample.key)
    identity = create_identity_tasks(benchmark, [submission], aliases_per_document=30, collision_pairs_per_document=30, seed=args.seed)
    write_jsonl(args.out_dir / "identity-tasks.jsonl", identity.tasks)
    write_jsonl(args.out_dir / "identity-task-key.jsonl", identity.key)
    fact_retrieval = retrieve_fact_probes(benchmark, [submission], top_k=10, k1=1.2, b=0.75)
    write_jsonl(args.out_dir / "retrieval-lexical.jsonl", fact_retrieval)
    fact = create_fact_probe_tasks(
        benchmark,
        [submission],
        fact_retrieval,
        probes_per_document=None,
        seed=args.seed,
    )
    write_jsonl(args.out_dir / "probe-tasks.jsonl", fact.tasks)
    write_jsonl(args.out_dir / "probe-task-key.jsonl", fact.key)
    qa_retrieval = retrieve_qa_probes(benchmark, [submission], top_k=10, k1=1.2, b=0.75)
    write_jsonl(args.out_dir / "qa-retrieval-lexical.jsonl", qa_retrieval)
    qa = create_qa_tasks(benchmark, [submission], qa_retrieval, seed=args.seed)
    write_jsonl(args.out_dir / "qa-tasks.jsonl", qa.tasks)
    write_jsonl(args.out_dir / "qa-task-key.jsonl", qa.key)
    print(json.dumps({"sample_tasks": len(sample.tasks), "identity_tasks": len(identity.tasks), "fact_tasks": len(fact.tasks), "qa_tasks": len(qa.tasks)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
