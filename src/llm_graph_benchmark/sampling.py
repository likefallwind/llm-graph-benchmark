from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Iterable

from .bundle import BenchmarkBundle, SubmissionBundle


@dataclass(frozen=True)
class SampleOutput:
    tasks: tuple[dict[str, Any], ...]
    key: tuple[dict[str, Any], ...]


ENTITY_DIMENSIONS = (
    "entity_admission",
    "entity_typing",
    "entity_definition_grounding",
)


def _task_id(seed: int, submission_hash: str, kind: str, document_id: str, item_id: str) -> str:
    raw = f"{seed}|{submission_hash}|{kind}|{document_id}|{item_id}".encode()
    return "t_" + hashlib.sha256(raw).hexdigest()[:20]


def _choose(items: list[dict[str, Any]], limit: int, rng: random.Random) -> list[dict[str, Any]]:
    if limit < 0:
        raise ValueError("sample limits must be non-negative")
    ordered = sorted(items, key=lambda item: str(item.get("id", "")))
    if len(ordered) <= limit:
        return ordered
    return sorted(rng.sample(ordered, limit), key=lambda item: str(item.get("id", "")))


def create_blind_sample(
    benchmark: BenchmarkBundle,
    submissions: Iterable[SubmissionBundle],
    *,
    entities_per_document: int,
    assertions_per_document: int,
    seed: int,
) -> SampleOutput:
    tasks: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    units = benchmark.unit_by_document
    for submission in sorted(submissions, key=lambda item: item.submission_hash):
        rng = random.Random(f"{seed}:{submission.submission_hash}")
        for document in sorted(
            submission.payload.get("documents", []),
            key=lambda item: str(item.get("document_id", "")),
        ):
            document_id = str(document["document_id"])
            entities = {str(item["id"]): item for item in document.get("entities", [])}
            selected_entities = _choose(
                document.get("entities", []), entities_per_document, rng
            )
            selected = (
                *((kind, selected_entities) for kind in ENTITY_DIMENSIONS),
                (
                    "assertion_grounding",
                    _choose(document.get("assertions", []), assertions_per_document, rng),
                ),
            )
            for kind, items in selected:
                for item in items:
                    item_id = str(item["id"])
                    task_id = _task_id(
                        seed, submission.submission_hash, kind, document_id, item_id
                    )
                    refs = item.get("evidence", [])
                    evidence = [
                        {
                            "unit": units[document_id][str(ref["unit_id"])],
                            "submitted_ref": ref,
                        }
                        for ref in refs
                    ]
                    if kind in ENTITY_DIMENSIONS:
                        content = {
                            "name": item["name"],
                            "definition": item["definition"],
                            "types": item.get("types", []),
                            "aliases": item.get("aliases", []),
                        }
                    else:
                        content = {
                            "subject": entities[str(item["subject_id"])]["name"],
                            "predicate": item["predicate"],
                            "object": entities[str(item["object_id"])]["name"],
                            "text": item["text"],
                            "scope": item.get("scope", ""),
                            "polarity": item.get("polarity", "positive"),
                        }
                    tasks.append(
                        {
                            "schema_version": "1.0",
                            "task_id": task_id,
                            "kind": kind,
                            "content": content,
                            "evidence": evidence,
                        }
                    )
                    key.append(
                        {
                            "task_id": task_id,
                            "system_id": submission.system_id,
                            "submission_hash": submission.submission_hash,
                            "document_id": document_id,
                            "kind": kind,
                            "item_id": item_id,
                        }
                    )
    paired = sorted(zip(tasks, key), key=lambda pair: pair[0]["task_id"])
    return SampleOutput(
        tuple(pair[0] for pair in paired), tuple(pair[1] for pair in paired)
    )
