from __future__ import annotations

from typing import Any

from .bundle import SubmissionBundle
from .identity import normalize_surface


def _jaccard(left: set[Any], right: set[Any]) -> float:
    union = left | right
    return round(len(left & right) / len(union), 6) if union else 1.0


def _retention(reference: set[Any], candidate: set[Any]) -> float:
    return round(len(reference & candidate) / len(reference), 6) if reference else 1.0


def _has_overlap_evidence(item: dict[str, Any], unit_ids: set[str]) -> bool:
    return any(str(ref.get("unit_id", "")) in unit_ids for ref in item.get("evidence", []))


def _document_items(
    submission: SubmissionBundle, document_id: str, unit_ids: set[str] | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    document = next(
        item
        for item in submission.payload.get("documents", [])
        if str(item.get("document_id")) == document_id
    )
    entities = document.get("entities", [])
    assertions = document.get("assertions", [])
    if unit_ids is None:
        return entities, assertions
    filtered_entities = [item for item in entities if _has_overlap_evidence(item, unit_ids)]
    entity_ids = {str(item["id"]) for item in filtered_entities}
    filtered_assertions = [
        item
        for item in assertions
        if _has_overlap_evidence(item, unit_ids)
        and str(item["subject_id"]) in entity_ids
        and str(item["object_id"]) in entity_ids
    ]
    return filtered_entities, filtered_assertions


def _entity_names(entities: list[dict[str, Any]]) -> set[str]:
    return {normalize_surface(str(item["name"])) for item in entities}


def _entity_surfaces(entities: list[dict[str, Any]]) -> set[str]:
    return {
        normalize_surface(str(value))
        for item in entities
        for value in [item["name"], *item.get("aliases", [])]
        if normalize_surface(str(value))
    }


def _assertion_sets(
    entities: list[dict[str, Any]], assertions: list[dict[str, Any]]
) -> tuple[set[tuple[str, str, str]], set[tuple[str, str]]]:
    names = {str(item["id"]): normalize_surface(str(item["name"])) for item in entities}
    triplets = {
        (
            names[str(item["subject_id"])],
            normalize_surface(str(item["predicate"])),
            names[str(item["object_id"])],
        )
        for item in assertions
    }
    endpoint_pairs = {(subject, object_) for subject, _, object_ in triplets}
    return triplets, endpoint_pairs


def compare_submissions(
    reference: SubmissionBundle,
    candidate: SubmissionBundle,
    *,
    document_id: str,
    overlap_unit_ids: set[str] | None = None,
) -> dict[str, Any]:
    reference_entities, reference_assertions = _document_items(reference, document_id, None)
    overlap_units = overlap_unit_ids or {
        str(ref["unit_id"])
        for item in [*reference_entities, *reference_assertions]
        for ref in item.get("evidence", [])
    }
    candidate_entities, candidate_assertions = _document_items(
        candidate, document_id, overlap_units
    )
    reference_names = _entity_names(reference_entities)
    candidate_names = _entity_names(candidate_entities)
    reference_surfaces = _entity_surfaces(reference_entities)
    candidate_surfaces = _entity_surfaces(candidate_entities)
    reference_triplets, reference_pairs = _assertion_sets(
        reference_entities, reference_assertions
    )
    candidate_triplets, candidate_pairs = _assertion_sets(
        candidate_entities, candidate_assertions
    )
    return {
        "schema_version": "1.0",
        "reference_system_id": reference.system_id,
        "candidate_system_id": candidate.system_id,
        "document_id": document_id,
        "overlap_unit_count": len(overlap_units),
        "counts": {
            "reference_entities": len(reference_entities),
            "candidate_entities": len(candidate_entities),
            "reference_assertions": len(reference_assertions),
            "candidate_assertions": len(candidate_assertions),
        },
        "entity_canonical_name_jaccard": _jaccard(reference_names, candidate_names),
        "entity_reference_retention": _retention(reference_names, candidate_names),
        "entity_surface_vocabulary_jaccard": _jaccard(
            reference_surfaces, candidate_surfaces
        ),
        "assertion_triplet_jaccard": _jaccard(reference_triplets, candidate_triplets),
        "assertion_reference_retention": _retention(reference_triplets, candidate_triplets),
        "assertion_endpoint_pair_jaccard": _jaccard(reference_pairs, candidate_pairs),
    }
