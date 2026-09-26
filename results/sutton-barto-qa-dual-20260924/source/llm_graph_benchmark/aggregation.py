from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable


ALLOWED_LABELS = {"pass", "fail", "uncertain", "error"}


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total == 0:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)]


def _score(expected: int, counts: Counter[str]) -> dict[str, Any]:
    decided = counts["pass"] + counts["fail"]
    judged = decided + counts["uncertain"]
    return {
        "expected": expected,
        "judged": judged,
        "unjudged": expected - judged - counts["error"],
        "error": counts["error"],
        "pass": counts["pass"],
        "fail": counts["fail"],
        "uncertain": counts["uncertain"],
        "decided": decided,
        "pass_rate": round(counts["pass"] / decided, 6) if decided else None,
        "pass_rate_95ci": _wilson(counts["pass"], decided),
        "pass_rate_all": round(counts["pass"] / expected, 6) if expected else None,
        "judgment_coverage": round(judged / expected, 6) if expected else None,
        "decision_coverage": round(decided / expected, 6) if expected else None,
        "status": "complete" if judged == expected else "incomplete",
    }


def _strata(row: dict[str, Any]) -> list[tuple[str, str]]:
    raw = row.get("strata", {})
    if not isinstance(raw, dict):
        return []
    return sorted(
        (str(dimension), str(value))
        for dimension, value in raw.items()
        if isinstance(value, (str, int, float, bool)) and str(value).strip()
    )


def aggregate_judgments(
    key_rows: Iterable[dict[str, Any]], judgments: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    key_list = list(key_rows)
    key = {str(row["task_id"]): row for row in key_list}
    if len(key) != len(key_list):
        raise ValueError("task key contains duplicate task_id")
    versions: dict[str, set[str | None]] = defaultdict(set)
    for row in key_list:
        versions[str(row["kind"])].add(row.get("rubric_sha256"))
    if any(len(values) > 1 for values in versions.values()):
        raise ValueError("cannot aggregate different rubric versions under the same kind")
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
    majorities: dict[str, str] = {}
    adjudicated = 0
    ties = 0
    for task_id, labels in votes.items():
        # A failed call is not a semantic vote. Keep error-only tasks visible.
        counts = Counter(label for label in labels if label != "error") or Counter({"error": 1})
        best = counts.most_common()
        if len(best) > 1 and best[0][1] == best[1][1]:
            majority = "uncertain"
            ties += 1
        else:
            majority = best[0][0]
        row = key[task_id]
        grouped[(str(row["system_id"]), str(row["kind"]))][majority] += 1
        majorities[task_id] = majority
        adjudicated += majority != "error"

    systems: dict[str, dict[str, Any]] = defaultdict(dict)
    for system_id, kind in sorted(expected):
        counts = grouped[(system_id, kind)]
        systems[system_id][kind] = _score(expected[(system_id, kind)], counts)

    stratum_expected: Counter[tuple[str, str, str, str]] = Counter()
    stratum_grouped: dict[tuple[str, str, str, str], Counter[str]] = defaultdict(Counter)
    for row in key_list:
        prefix = (str(row["system_id"]), str(row["kind"]))
        for dimension, value in _strata(row):
            stratum_expected[(*prefix, dimension, value)] += 1
    for task_id, majority in majorities.items():
        row = key[task_id]
        prefix = (str(row["system_id"]), str(row["kind"]))
        for dimension, value in _strata(row):
            stratum_grouped[(*prefix, dimension, value)][majority] += 1

    stratified: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    for system_id, kind, dimension, value in sorted(stratum_expected):
        group = (system_id, kind, dimension, value)
        stratified[system_id][kind][dimension][value] = _score(
            stratum_expected[group], stratum_grouped[group]
        )
    return {
        "schema_version": "1.0",
        "expected_task_count": len(key_list),
        "adjudicated_task_count": adjudicated,
        "unjudged_task_count": len(key_list) - len(majorities),
        "error_task_count": sum(label == "error" for label in majorities.values()),
        "error_judgment_count": sum(labels.count("error") for labels in votes.values()),
        "tie_count": ties,
        "systems": dict(systems),
        "strata": {
            system_id: {
                kind: {
                    dimension: dict(values)
                    for dimension, values in dimensions.items()
                }
                for kind, dimensions in kinds.items()
            }
            for system_id, kinds in stratified.items()
        },
    }
