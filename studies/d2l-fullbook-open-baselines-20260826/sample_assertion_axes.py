"""Draw a larger assertion sample and fan it out over three quality axes.

The v2 pass asked one bundled question per assertion ("does the source support
the complete directed assertion, including polarity and restrictive scope?"),
so grounding, projection fidelity and scope faithfulness shared a single label
and could not be told apart. This script re-samples assertions at a size that
can separate the systems (n=30 gives a +/-16pp interval) and emits one task per
axis per assertion.

The sample is drawn with the study's original seed and the same
entities_per_document value, so the RNG stream up to the assertion draw is
unchanged; only the assertion limit differs. task_id is content-addressed by
(seed, submission_hash, kind, document_id, item_id), so the axis kinds keep the
v2 assertion_grounding ids distinct.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.io import write_jsonl
from llm_graph_benchmark.sampling import create_blind_sample

AXES = ("assertion_grounding_v3", "assertion_projection", "assertion_scope")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--submission", action="append", required=True,
                        help="system_id=/path/to/submission.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--assertions", type=int, default=200)
    parser.add_argument("--entities", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()

    benchmark = BenchmarkBundle.load(args.benchmark)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    all_tasks: list[dict] = []
    all_key: list[dict] = []
    summary: dict[str, int] = {}

    for entry in args.submission:
        system_id, _, path = entry.partition("=")
        submission = SubmissionBundle.load(Path(path))
        sample = create_blind_sample(
            benchmark, [submission],
            entities_per_document=args.entities,
            assertions_per_document=args.assertions,
            seed=args.seed,
        )
        base = [
            (task, key)
            for task, key in zip(sample.tasks, sample.key)
            if task["kind"] == "assertion_grounding"
        ]
        summary[system_id] = len(base)
        for axis in AXES:
            for task, key in base:
                axis_task = json.loads(json.dumps(task))
                axis_key = dict(key)
                # Keep the v2 id recoverable so the two passes can be paired.
                axis_task["kind"] = axis
                axis_task["source_task_id"] = task["task_id"]
                axis_task["task_id"] = f"{task['task_id']}_{axis[10:]}"
                axis_key["kind"] = axis
                axis_key["source_task_id"] = key["task_id"]
                axis_key["task_id"] = axis_task["task_id"]
                axis_key["system_id"] = system_id
                all_tasks.append(axis_task)
                all_key.append(axis_key)

    all_tasks.sort(key=lambda item: item["task_id"])
    all_key.sort(key=lambda item: item["task_id"])
    write_jsonl(args.out_dir / "axis-tasks.jsonl", all_tasks)
    write_jsonl(args.out_dir / "axis-task-key.jsonl", all_key)
    print(json.dumps(
        {"assertions_sampled": summary, "axes": list(AXES),
         "total_tasks": len(all_tasks), "seed": args.seed},
        ensure_ascii=False))


if __name__ == "__main__":
    main()
