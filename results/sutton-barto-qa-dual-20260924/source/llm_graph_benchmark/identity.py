from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from .bundle import BenchmarkBundle, SubmissionBundle


@dataclass(frozen=True)
class IdentityTaskOutput:
    tasks: tuple[dict[str, Any], ...]
    key: tuple[dict[str, Any], ...]


def normalize_surface(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _usable_surface(value: str) -> str:
    normalized = normalize_surface(value)
    if len(normalized) < 3 or "$" in value or "\\" in value:
        return ""
    return normalized


def _entity_surfaces(entity: dict[str, Any]) -> set[str]:
    return {
        normalized
        for value in [entity.get("name", ""), *entity.get("aliases", [])]
        if (normalized := _usable_surface(str(value)))
    }


def document_identity_metrics(document: dict[str, Any]) -> dict[str, Any]:
    entities = document.get("entities", [])
    owners: dict[str, set[str]] = defaultdict(set)
    alias_count = 0
    nontrivial_alias_count = 0
    entities_with_aliases = 0
    for entity in entities:
        entity_id = str(entity["id"])
        canonical = normalize_surface(str(entity["name"]))
        aliases = [str(value) for value in entity.get("aliases", [])]
        alias_count += len(aliases)
        if aliases:
            entities_with_aliases += 1
        nontrivial_alias_count += sum(
            bool(_usable_surface(alias)) and normalize_surface(alias) != canonical
            for alias in aliases
        )
        for surface in _entity_surfaces(entity):
            owners[surface].add(entity_id)
    collisions = {surface: ids for surface, ids in owners.items() if len(ids) > 1}
    collision_entities = set().union(*collisions.values()) if collisions else set()
    return {
        "entity_count": len(entities),
        "alias_count": alias_count,
        "nontrivial_alias_count": nontrivial_alias_count,
        "entities_with_aliases": entities_with_aliases,
        "ambiguous_surface_group_count": len(collisions),
        "entities_in_ambiguous_surface_groups": len(collision_entities),
        "ambiguous_surface_rate": (
            round(len(collision_entities) / len(entities), 6) if entities else 0.0
        ),
    }


def _task_id(seed: int, submission_hash: str, kind: str, item_id: str) -> str:
    raw = f"{seed}|{submission_hash}|{kind}|{item_id}".encode()
    return "t_" + hashlib.sha256(raw).hexdigest()[:20]


def _evidence(
    entity: dict[str, Any], units: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        {"unit": units[str(ref["unit_id"])], "submitted_ref": ref}
        for ref in entity.get("evidence", [])
    ]


def _entity_content(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": entity["name"],
        "definition": entity["definition"],
        "types": entity.get("types", []),
    }


def create_identity_tasks(
    benchmark: BenchmarkBundle,
    submissions: Iterable[SubmissionBundle],
    *,
    aliases_per_document: int,
    collision_pairs_per_document: int,
    seed: int,
) -> IdentityTaskOutput:
    if aliases_per_document < 0 or collision_pairs_per_document < 0:
        raise ValueError("identity sample limits must be non-negative")
    tasks: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    for submission in sorted(submissions, key=lambda item: item.submission_hash):
        rng = random.Random(f"identity:{seed}:{submission.submission_hash}")
        for document in submission.payload.get("documents", []):
            document_id = str(document["document_id"])
            units = benchmark.unit_by_document[document_id]
            entities = document.get("entities", [])
            alias_items = []
            for entity in entities:
                canonical = normalize_surface(str(entity["name"]))
                for index, alias in enumerate(entity.get("aliases", [])):
                    alias = str(alias)
                    if _usable_surface(alias) and normalize_surface(alias) != canonical:
                        alias_items.append((str(entity["id"]), index, entity, alias))
            alias_items.sort(key=lambda item: (item[0], item[1], item[3]))
            if len(alias_items) > aliases_per_document:
                alias_items = sorted(
                    rng.sample(alias_items, aliases_per_document),
                    key=lambda item: (item[0], item[1], item[3]),
                )
            for entity_id, alias_index, entity, alias in alias_items:
                item_id = f"{entity_id}:alias:{alias_index}"
                task_id = _task_id(seed, submission.submission_hash, "alias_identity", item_id)
                tasks.append(
                    {
                        "schema_version": "1.0",
                        "task_id": task_id,
                        "kind": "alias_identity",
                        "content": {**_entity_content(entity), "alias": alias},
                        "evidence": _evidence(entity, units),
                    }
                )
                key.append(
                    {
                        "task_id": task_id,
                        "system_id": submission.system_id,
                        "submission_hash": submission.submission_hash,
                        "document_id": document_id,
                        "kind": "alias_identity",
                        "item_id": item_id,
                    }
                )

            surface_owners: dict[str, set[str]] = defaultdict(set)
            by_id = {str(entity["id"]): entity for entity in entities}
            for entity in entities:
                for surface in _entity_surfaces(entity):
                    surface_owners[surface].add(str(entity["id"]))
            pair_surfaces: dict[tuple[str, str], set[str]] = defaultdict(set)
            for surface, owners in surface_owners.items():
                ordered = sorted(owners)
                for left_index, left in enumerate(ordered):
                    for right in ordered[left_index + 1 :]:
                        pair_surfaces[(left, right)].add(surface)
            pair_items = sorted(pair_surfaces.items())
            if len(pair_items) > collision_pairs_per_document:
                pair_items = sorted(rng.sample(pair_items, collision_pairs_per_document))
            for (left_id, right_id), shared in pair_items:
                left = by_id[left_id]
                right = by_id[right_id]
                item_id = f"{left_id}:split:{right_id}"
                task_id = _task_id(seed, submission.submission_hash, "identity_split", item_id)
                tasks.append(
                    {
                        "schema_version": "1.0",
                        "task_id": task_id,
                        "kind": "identity_split",
                        "content": {
                            "left": _entity_content(left),
                            "right": _entity_content(right),
                            "shared_surfaces": sorted(shared),
                        },
                        "evidence": {
                            "left": _evidence(left, units),
                            "right": _evidence(right, units),
                        },
                    }
                )
                key.append(
                    {
                        "task_id": task_id,
                        "system_id": submission.system_id,
                        "submission_hash": submission.submission_hash,
                        "document_id": document_id,
                        "kind": "identity_split",
                        "item_id": item_id,
                    }
                )
    paired = sorted(zip(tasks, key), key=lambda pair: pair[0]["task_id"])
    return IdentityTaskOutput(
        tuple(task for task, _ in paired), tuple(item for _, item in paired)
    )
