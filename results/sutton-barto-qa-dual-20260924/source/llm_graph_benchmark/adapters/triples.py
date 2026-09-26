from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Iterable


MISSING_DEFINITION = "（该方法未输出实体定义）"


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "\u241f".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:20]}"


def submission_from_triples(
    records: Iterable[dict[str, Any]],
    *,
    entity_records: Iterable[dict[str, Any]] = (),
    benchmark_id: str,
    document_id: str,
    system_id: str,
    system_name: str,
    system_version: str,
    runtime: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert provenance-bearing triples without inventing missing semantics.

    Each input record requires ``subject``, ``predicate`` and ``object``. Optional
    ``evidence_unit_ids``, endpoint definitions/types/aliases, and per-record
    metadata are retained. Blank endpoints or predicates are rejected instead of
    being repaired with evaluator-generated content.
    """

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        subject = str(raw.get("subject", "")).strip()
        predicate = str(raw.get("predicate", "")).strip()
        obj = str(raw.get("object", "")).strip()
        if not subject or not predicate or not obj or subject == obj:
            rejected.append(
                {
                    "index": index,
                    "reason": "blank_component" if not all((subject, predicate, obj)) else "self_loop",
                    "record": raw,
                }
            )
            continue
        accepted.append({**raw, "subject": subject, "predicate": predicate, "object": obj})

    endpoint_rows: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    accepted_entities = 0
    rejected_entities: list[dict[str, Any]] = []
    for index, raw in enumerate(entity_records):
        name = str(raw.get("name", "")).strip()
        if not name:
            rejected_entities.append({"index": index, "reason": "blank_name", "record": raw})
            continue
        accepted_entities += 1
        endpoint_rows[name].append(
            (
                {
                    "evidence_unit_ids": raw.get("evidence_unit_ids", []),
                    "entity_definition": raw.get("definition", ""),
                    "entity_types": raw.get("types", []),
                    "entity_aliases": raw.get("aliases", []),
                },
                "entity",
            )
        )
    assertion_rows: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        endpoint_rows[row["subject"]].append((row, "subject"))
        endpoint_rows[row["object"]].append((row, "object"))
        assertion_rows[(row["subject"], row["predicate"], row["object"])].append(row)

    entity_id_by_name = {
        name: _stable_id("e", document_id, name) for name in sorted(endpoint_rows)
    }
    entities = []
    for name in sorted(endpoint_rows):
        rows = endpoint_rows[name]
        evidence_ids = sorted(
            {
                str(unit_id)
                for row, _ in rows
                for unit_id in row.get("evidence_unit_ids", [])
                if str(unit_id).strip()
            }
        )
        definitions = [
            str(row.get(f"{role}_definition", "")).strip()
            for row, role in rows
            if str(row.get(f"{role}_definition", "")).strip()
        ]
        types = sorted(
            {
                str(value).strip()
                for row, role in rows
                for value in row.get(f"{role}_types", [])
                if str(value).strip()
            }
        )
        aliases = sorted(
            {
                str(value).strip()
                for row, role in rows
                for value in row.get(f"{role}_aliases", [])
                if str(value).strip() and str(value).strip() != name
            }
        )
        entities.append(
            {
                "id": entity_id_by_name[name],
                "name": name,
                "definition": definitions[0] if definitions else MISSING_DEFINITION,
                "types": types,
                "aliases": aliases,
                "evidence": [{"unit_id": unit_id} for unit_id in evidence_ids],
                "metadata": {"definition_available": bool(definitions)},
            }
        )

    assertions = []
    for subject, predicate, obj in sorted(assertion_rows):
        rows = assertion_rows[(subject, predicate, obj)]
        evidence_ids = sorted(
            {
                str(unit_id)
                for row in rows
                for unit_id in row.get("evidence_unit_ids", [])
                if str(unit_id).strip()
            }
        )
        assertions.append(
            {
                "id": _stable_id("a", document_id, subject, predicate, obj),
                "subject_id": entity_id_by_name[subject],
                "predicate": predicate,
                "object_id": entity_id_by_name[obj],
                "text": next(
                    (
                        str(row.get("text", "")).strip()
                        for row in rows
                        if str(row.get("text", "")).strip()
                    ),
                    f"{subject} {predicate} {obj}",
                ),
                "scope": next(
                    (
                        str(row.get("scope", "")).strip()
                        for row in rows
                        if str(row.get("scope", "")).strip()
                    ),
                    "",
                ),
                "polarity": "positive",
                "evidence": [{"unit_id": unit_id} for unit_id in evidence_ids],
            }
        )

    submission = {
        "schema_version": "1.0",
        "benchmark_id": benchmark_id,
        "system": {
            "id": system_id,
            "name": system_name,
            "version": system_version,
        },
        "documents": [
            {
                "document_id": document_id,
                "entities": entities,
                "assertions": assertions,
            }
        ],
        "runtime": runtime or {},
        "metadata": metadata or {},
    }
    report = {
        "input_records": len(accepted) + len(rejected),
        "accepted_records": len(accepted),
        "rejected_records": len(rejected),
        "rejections": rejected,
        "input_entity_records": accepted_entities + len(rejected_entities),
        "accepted_entity_records": accepted_entities,
        "rejected_entity_records": len(rejected_entities),
        "entity_rejections": rejected_entities,
        "output_entities": len(entities),
        "output_assertions": len(assertions),
        "missing_definition_entities": sum(
            entity["definition"] == MISSING_DEFINITION for entity in entities
        ),
    }
    return submission, report
