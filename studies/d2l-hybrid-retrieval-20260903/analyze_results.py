#!/usr/bin/env python3
"""Build the paired BM25-versus-union pilot result for the LKG submission."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if not total:
        return [0.0, 0.0]
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)]


def score(labels: Counter[str]) -> dict[str, Any]:
    total = sum(labels.values())
    yes = labels["yes"]
    return {
        "total": total,
        "yes": yes,
        "no": labels["no"],
        "uncertain": labels["uncertain"],
        "coverage_rate": round(yes / total, 6),
        "coverage_rate_95ci": wilson(yes, total),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-id", required=True)
    parser.add_argument("--baseline-pool-map", type=Path, required=True)
    parser.add_argument("--baseline-judgments", type=Path, required=True)
    parser.add_argument("--retrieval-summary", type=Path, required=True)
    parser.add_argument("--delta-review", type=Path, required=True)
    parser.add_argument("--embedding-task-key", type=Path)
    parser.add_argument("--embedding-review", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    system_map = json.loads(args.baseline_pool_map.read_text(encoding="utf-8"))["systems"]
    latest = {row["task_id"]: row for row in read_jsonl(args.baseline_judgments)}
    baseline = {
        task_id: str(latest[task_id]["covered"])
        for task_id, system_id in system_map.items()
        if system_id == args.system_id
    }
    review = {row["task_id"]: row for row in read_jsonl(args.delta_review)}
    needs_review = {task_id for task_id, label in baseline.items() if label != "yes"}
    if set(review) != needs_review:
        raise ValueError(
            f"delta review mismatch: expected {sorted(needs_review)}, got {sorted(review)}"
        )
    for task_id, row in review.items():
        if row["baseline_covered"] != baseline[task_id]:
            raise ValueError(f"baseline label mismatch for {task_id}")

    union = dict(baseline)
    for task_id, row in review.items():
        union[task_id] = str(row["union_covered"])
    baseline_counts = Counter(baseline.values())
    union_counts = Counter(union.values())
    embedding_result = None
    paired_transitions = None
    if args.embedding_task_key or args.embedding_review:
        if not args.embedding_task_key or not args.embedding_review:
            raise ValueError("embedding task key and review must be supplied together")
        probe_by_task = {
            row["task_id"]: row["item_id"] for row in read_jsonl(args.embedding_task_key)
        }
        embedding_by_probe = {
            row["probe_id"]: row for row in read_jsonl(args.embedding_review)
        }
        expected_probes = set(probe_by_task.values())
        if set(embedding_by_probe) != expected_probes:
            raise ValueError("embedding review does not cover the exact frozen probe set")
        embedding = {
            task_id: str(embedding_by_probe[probe_id]["covered"])
            for task_id, probe_id in probe_by_task.items()
        }
        embedding_result = score(Counter(embedding.values()))
        paired_transitions = dict(
            sorted(
                Counter(
                    f"{baseline[task]}->{embedding[task]}" for task in baseline
                ).items()
            )
        )
    retrieval = json.loads(args.retrieval_summary.read_text(encoding="utf-8"))
    per_probe = retrieval["per_probe"]
    overlap_counts = Counter(str(row["overlap_count"]) for row in per_probe)
    result = {
        "schema_version": "1.0",
        "experiment": "paired-bm25-10-vs-e5-10-vs-union",
        "system_id": args.system_id,
        "baseline": score(baseline_counts),
        "union": score(union_counts),
        "embedding_only": embedding_result,
        "bm25_to_embedding_transitions": paired_transitions,
        "paired_delta": {
            "new_yes": union_counts["yes"] - baseline_counts["yes"],
            "percentage_points": round(
                100
                * (union_counts["yes"] - baseline_counts["yes"])
                / sum(baseline_counts.values()),
                3,
            ),
            "changed_tasks": [
                row for row in review.values() if row["union_covered"] != row["baseline_covered"]
            ],
        },
        "retrieval": {
            "mean_bm25_embedding_overlap_at_10": retrieval["mean_overlap_count"],
            "mean_embedding_only_candidates": retrieval["mean_embedding_only_count"],
            "mean_union_candidates": retrieval["mean_union_count"],
            "min_union_candidates": min(row["union_count"] for row in per_probe),
            "max_union_candidates": max(row["union_count"] for row in per_probe),
            "overlap_count_histogram": dict(sorted(overlap_counts.items(), key=lambda x: int(x[0]))),
        },
        "judging": {
            "baseline": "existing MiniMax-M3 CaRB judgments",
            "union_yes_reuse": "valid by monotonic multi-match covered rule",
            "union_delta": "local Codex source-grounded review of all baseline non-yes tasks",
            "embedding_only": "local Codex source-grounded review of all 48 frozen probes",
            "external_union_rerun": "not performed; network data egress was not authorized",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
