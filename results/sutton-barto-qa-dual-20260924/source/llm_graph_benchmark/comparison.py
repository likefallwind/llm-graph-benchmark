"""Paired comparisons of frozen fact probes under one explicitly selected judge."""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable


def compare_paired(
    key_rows: Iterable[dict[str, Any]], judgments: Iterable[dict[str, Any]], *,
    left: str, right: str, kind: str, judge_id: str,
) -> dict[str, Any]:
    if left == right or not judge_id:
        raise ValueError("select two different systems and one judge_id")
    if kind not in {"fact_recovery_strict_v1", "fact_recovery_core_v1"}:
        raise ValueError("paired comparison supports versioned fact recovery tasks only")
    rows = list(key_rows)
    keys = {r["task_id"]: r for r in rows}
    if len(keys) != len(rows):
        raise ValueError("duplicate task_id in key")
    groups = {left: {}, right: {}}
    for row in rows:
        if row["kind"] != kind or row["system_id"] not in groups:
            continue
        item = (row["document_id"], row["item_id"])
        group = groups[row["system_id"]]
        if item in group:
            raise ValueError("duplicate probe within a system")
        if not row.get("rubric_sha256") or not row.get("comparison_context"):
            raise ValueError("comparison requires frozen rubric and retrieval/source context")
        group[item] = row
    a, b = groups[left], groups[right]
    if not a or a.keys() != b.keys():
        raise ValueError("systems must contain exactly the same nonempty probe set")
    if len({r['rubric_sha256'] for g in groups.values() for r in g.values()}) != 1:
        raise ValueError("cannot compare different rubric versions")
    for item in a:
        if a[item]["comparison_context"] != b[item]["comparison_context"]:
            raise ValueError("source fact, evidence or retrieval configuration differs")
    votes, seen = {}, set()
    for row in judgments:
        tid = row.get("task_id")
        if tid not in keys:
            raise ValueError("judgment references unknown task")
        if row.get("judge_id") != judge_id:
            continue
        if tid in seen:
            raise ValueError("duplicate judgment; resolve retries explicitly before comparing")
        seen.add(tid)
        if row.get("label") not in {"pass", "fail", "uncertain", "error"}:
            raise ValueError("invalid judgment label")
        votes[tid] = row["label"]
    missing = {s: sum(r['task_id'] not in votes for r in g.values()) for s, g in groups.items()}
    errors = {s: sum(votes.get(r['task_id']) == 'error' for r in g.values()) for s, g in groups.items()}
    result = {"kind": kind, "judge_id": judge_id, "left": left, "right": right,
              "expected_pairs": len(a), "missing": missing, "errors": errors,
              "status": "incomplete", "exact_mcnemar_p": None,
              "interpretation": "Uncertain is not pass. An exploratory unadjusted paired test over these probes; not proof of equivalence or cross-document generalization."}
    if any(missing.values()) or any(errors.values()):
        return result
    transitions = Counter((votes[a[i]['task_id']], votes[b[i]['task_id']]) for i in a)
    wins = sum(n for (x, y), n in transitions.items() if x == 'pass' and y != 'pass')
    losses = sum(n for (x, y), n in transitions.items() if y == 'pass' and x != 'pass')
    discordant = wins + losses
    # Stable log-space binomial tail; no scipy dependency or 2**n float overflow.
    k = min(wins, losses)
    if discordant:
        log_max = math.lgamma(discordant + 1) - math.lgamma(k + 1) - math.lgamma(discordant - k + 1)
        term, tail = 1.0, 1.0
        for j in range(k, 0, -1):
            term *= j / (discordant - j + 1)
            tail += term
        p = min(1.0, math.exp(math.log(2) + log_max - discordant * math.log(2) + math.log(tail)))
    else:
        p = 1.0
    result.update(status="complete", left_only_pass=wins, right_only_pass=losses,
                  pass_rate_difference=(wins - losses) / len(a), exact_mcnemar_p=p,
                  transitions={f"{x}->{y}": n for (x, y), n in sorted(transitions.items())})
    return result
