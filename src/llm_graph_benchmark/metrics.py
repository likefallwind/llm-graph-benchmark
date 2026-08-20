from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .bundle import SubmissionBundle
from .identity import document_identity_metrics


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _surface_key(value: str) -> str:
    return re.sub(r"[^\w]+", "", value.casefold(), flags=re.UNICODE)


def _per(
    numerator: int | float | None, denominator: int | float | None
) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return round(numerator / denominator, 6)


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
            "identity": document_identity_metrics(document),
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
        for key in (
            "alias_count",
            "nontrivial_alias_count",
            "entities_with_aliases",
            "ambiguous_surface_group_count",
            "entities_in_ambiguous_surface_groups",
        ):
            totals[f"identity_{key}"] += int(metric["identity"][key])
        totals["entity_with_evidence"] += entity_evidence
        totals["assertion_with_evidence"] += assertion_evidence
    entity_total = totals["entity_count"]
    assertion_total = totals["assertion_count"]
    elapsed_seconds = runtime.get("elapsed_seconds")
    cost_usd = runtime.get("cost_usd")
    input_tokens = runtime.get("input_tokens")
    output_tokens = runtime.get("output_tokens")
    total_tokens = (
        input_tokens + output_tokens
        if isinstance(input_tokens, (int, float))
        and isinstance(output_tokens, (int, float))
        else None
    )
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
            "identity": {
                "alias_count": totals["identity_alias_count"],
                "nontrivial_alias_count": totals["identity_nontrivial_alias_count"],
                "entities_with_aliases": totals["identity_entities_with_aliases"],
                "ambiguous_surface_group_count": totals[
                    "identity_ambiguous_surface_group_count"
                ],
                "entities_in_ambiguous_surface_groups": totals[
                    "identity_entities_in_ambiguous_surface_groups"
                ],
                "ambiguous_surface_rate": _ratio(
                    totals["identity_entities_in_ambiguous_surface_groups"],
                    entity_total,
                ),
            },
            "elapsed_seconds": elapsed_seconds,
            "cost_usd": cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "entities_per_second": _per(entity_total, elapsed_seconds),
            "assertions_per_second": _per(assertion_total, elapsed_seconds),
            "tokens_per_entity": _per(total_tokens, entity_total),
            "tokens_per_assertion": _per(total_tokens, assertion_total),
            "cost_per_100_entities_usd": (
                _per(cost_usd * 100, entity_total)
                if isinstance(cost_usd, (int, float))
                else None
            ),
            "cost_per_100_assertions_usd": (
                _per(cost_usd * 100, assertion_total)
                if isinstance(cost_usd, (int, float))
                else None
            ),
        },
        "documents": per_document,
    }
