from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable


ALLOWED_LABELS = {"pass", "fail", "uncertain"}


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)]


def aggregate_judgments(
    key_rows: Iterable[dict[str, Any]], judgments: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    key_list = list(key_rows)
    key = {str(row["task_id"]): row for row in key_list}
    if len(key) != len(key_list):
        raise ValueError("task key contains duplicate task_id")
    votes: dict[str, list[str]] = defaultdict(list)
    seen_judges: set[tuple[str, str]] = set()
    for index, judgment in enumerate(judgments):
        task_id = str(judgment.get("task_id", ""))
        judge_id = str(judgment.get("judge_id", ""))
        label = str(judgment.get("label", ""))
        if task_id not in key:
            raise ValueError(f"judgments[{index}] references unknown task {task_id}")
        if not judge_id:
            raise ValueError(f"judgments[{index}] requires judge_id")
        if label not in ALLOWED_LABELS:
            raise ValueError(f"judgments[{index}] has invalid label {label}")
        pair = (task_id, judge_id)
        if pair in seen_judges:
            raise ValueError(f"duplicate judgment for task {task_id} by {judge_id}")
        seen_judges.add(pair)
        votes[task_id].append(label)

    expected: Counter[tuple[str, str]] = Counter(
        (str(row["system_id"]), str(row["kind"])) for row in key_list
    )
    grouped: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    adjudicated = 0
    ties = 0
    for task_id, labels in votes.items():
        counts = Counter(labels)
        best = counts.most_common()
        if len(best) > 1 and best[0][1] == best[1][1]:
            majority = "uncertain"
            ties += 1
        else:
            majority = best[0][0]
        row = key[task_id]
        grouped[(str(row["system_id"]), str(row["kind"]))][majority] += 1
        adjudicated += 1

    systems: dict[str, dict[str, Any]] = defaultdict(dict)
    for system_id, kind in sorted(expected):
        counts = grouped[(system_id, kind)]
        decided = counts["pass"] + counts["fail"]
        judged = counts["pass"] + counts["fail"] + counts["uncertain"]
        systems[system_id][kind] = {
            "expected": expected[(system_id, kind)],
            "judged": judged,
            "unjudged": expected[(system_id, kind)] - judged,
            "pass": counts["pass"],
            "fail": counts["fail"],
            "uncertain": counts["uncertain"],
            "decided": decided,
            "pass_rate": round(counts["pass"] / decided, 6) if decided else None,
            "pass_rate_95ci": _wilson(counts["pass"], decided),
        }
    return {
        "schema_version": "1.0",
        "expected_task_count": len(key_list),
        "adjudicated_task_count": adjudicated,
        "unjudged_task_count": len(key_list) - adjudicated,
        "tie_count": ties,
        "systems": dict(systems),
    }
