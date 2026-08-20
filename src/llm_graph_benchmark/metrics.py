from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .bundle import SubmissionBundle


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _surface_key(value: str) -> str:
    return re.sub(r"[^\w]+", "", value.casefold(), flags=re.UNICODE)


def submission_metrics(submission: SubmissionBundle) -> dict[str, Any]:
    per_document: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    runtime = submission.payload.get("runtime", {})
    for document in submission.payload.get("documents", []):
        entities = document.get("entities", [])
        assertions = document.get("assertions", [])
        entity_ids = {str(item["id"]) for item in entities}
        adjacency = {item_id: set() for item_id in entity_ids}
        predicates: set[str] = set()
        for assertion in assertions:
            subject = str(assertion["subject_id"])
            object_ = str(assertion["object_id"])
            predicates.add(str(assertion["predicate"]))
            if subject in adjacency and object_ in adjacency:
                adjacency[subject].add(object_)
                adjacency[object_].add(subject)
        seen: set[str] = set()
        components: list[int] = []
        for entity_id in sorted(entity_ids):
            if entity_id in seen:
                continue
            pending = [entity_id]
            seen.add(entity_id)
            size = 0
            while pending:
                current = pending.pop()
                size += 1
                for neighbor in adjacency[current] - seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
            components.append(size)
        names = Counter(_surface_key(str(item["name"])) for item in entities)
        duplicate_groups = sum(1 for count in names.values() if count > 1)
        entity_evidence = sum(bool(item.get("evidence")) for item in entities)
        assertion_evidence = sum(bool(item.get("evidence")) for item in assertions)
        isolated = sum(not neighbors for neighbors in adjacency.values())
        metric = {
            "document_id": str(document["document_id"]),
            "entity_count": len(entities),
            "assertion_count": len(assertions),
            "unique_predicate_count": len(predicates),
            "entity_evidence_coverage": _ratio(entity_evidence, len(entities)),
            "assertion_evidence_coverage": _ratio(assertion_evidence, len(assertions)),
            "isolated_entity_count": isolated,
            "component_count": len(components),
            "largest_component_ratio": _ratio(max(components, default=0), len(entities)),
            "surface_duplicate_group_count": duplicate_groups,
        }
        per_document.append(metric)
        for key in (
            "entity_count",
            "assertion_count",
            "unique_predicate_count",
            "isolated_entity_count",
            "surface_duplicate_group_count",
        ):
            totals[key] += int(metric[key])
        totals["entity_with_evidence"] += entity_evidence
        totals["assertion_with_evidence"] += assertion_evidence
    entity_total = totals["entity_count"]
    assertion_total = totals["assertion_count"]
    return {
        "schema_version": "1.0",
        "system_id": submission.system_id,
        "submission_hash": submission.submission_hash,
        "summary": {
            "document_count": len(per_document),
            "entity_count": entity_total,
            "assertion_count": assertion_total,
            "unique_predicate_count_sum": totals["unique_predicate_count"],
            "entity_evidence_coverage": _ratio(totals["entity_with_evidence"], entity_total),
            "assertion_evidence_coverage": _ratio(
                totals["assertion_with_evidence"], assertion_total
            ),
            "isolated_entity_rate": _ratio(totals["isolated_entity_count"], entity_total),
            "surface_duplicate_group_count": totals["surface_duplicate_group_count"],
            "elapsed_seconds": runtime.get("elapsed_seconds"),
            "cost_usd": runtime.get("cost_usd"),
            "input_tokens": runtime.get("input_tokens"),
            "output_tokens": runtime.get("output_tokens"),
        },
        "documents": per_document,
    }
