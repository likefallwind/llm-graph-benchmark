from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Iterable


def _pair_metrics(left: dict[str, str], right: dict[str, str]) -> dict[str, Any]:
    shared = sorted(left.keys() & right.keys())
    if not shared:
        return {"shared_tasks": 0, "agreement": None, "cohen_kappa": None}
    labels = sorted(set(left.values()) | set(right.values()))
    agreed = sum(left[task_id] == right[task_id] for task_id in shared)
    observed = agreed / len(shared)
    left_counts = Counter(left[task_id] for task_id in shared)
    right_counts = Counter(right[task_id] for task_id in shared)
    pair_counts = Counter((left[task_id], right[task_id]) for task_id in shared)
    expected = sum(
        left_counts[label] / len(shared) * right_counts[label] / len(shared)
        for label in labels
    )
    kappa = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return {
        "shared_tasks": len(shared),
        "agreement": round(observed, 6),
        "cohen_kappa": round(kappa, 6),
        "confusion": {
            f"{left_label}->{right_label}": count
            for (left_label, right_label), count in sorted(pair_counts.items())
        },
    }


def judge_agreement(
    key_rows: Iterable[dict[str, Any]], judgments: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    key = {str(row["task_id"]): row for row in key_rows}
    by_kind_judge: dict[str, dict[str, dict[str, str]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(judgments):
        task_id = str(row.get("task_id", ""))
        judge_id = str(row.get("judge_id", ""))
        label = str(row.get("label", ""))
        if task_id not in key:
            raise ValueError(f"judgments[{index}] references unknown task {task_id}")
        if not judge_id or not label:
            raise ValueError(f"judgments[{index}] requires judge_id and label")
        pair = (task_id, judge_id)
        if pair in seen:
            raise ValueError(f"duplicate judgment for task {task_id} by {judge_id}")
        seen.add(pair)
        kind = str(key[task_id]["kind"])
        by_kind_judge[kind][judge_id][task_id] = label

    dimensions: dict[str, Any] = {}
    for kind, judges in sorted(by_kind_judge.items()):
        pairs = []
        for left_id, right_id in combinations(sorted(judges), 2):
            result = _pair_metrics(judges[left_id], judges[right_id])
            pairs.append({"left_judge": left_id, "right_judge": right_id, **result})
        comparable = [item for item in pairs if item["agreement"] is not None]
        dimensions[kind] = {
            "judge_count": len(judges),
            "pair_count": len(comparable),
            "mean_pairwise_agreement": (
                round(sum(item["agreement"] for item in comparable) / len(comparable), 6)
                if comparable
                else None
            ),
            "mean_pairwise_cohen_kappa": (
                round(sum(item["cohen_kappa"] for item in comparable) / len(comparable), 6)
                if comparable
                else None
            ),
            "pairs": pairs,
        }
    return {"schema_version": "1.0", "dimensions": dimensions}
