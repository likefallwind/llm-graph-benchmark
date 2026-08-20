from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from .bundle import BenchmarkBundle, SubmissionBundle


@dataclass(frozen=True)
class ProbeTaskOutput:
    tasks: tuple[dict[str, Any], ...]
    key: tuple[dict[str, Any], ...]


def _id(seed: int, submission_hash: str, probe_id: str) -> str:
    raw = f"{seed}|{submission_hash}|fact_recovery|{probe_id}".encode()
    return "t_" + hashlib.sha256(raw).hexdigest()[:20]


def _selected_probes(
    benchmark: BenchmarkBundle, per_document: int | None, seed: int
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in benchmark.fact_probes:
        grouped[str(probe["document_id"])].append(probe)
    selected: list[dict[str, Any]] = []
    rng = random.Random(seed)
    for document_id, probes in sorted(grouped.items()):
        ordered = sorted(probes, key=lambda item: str(item["probe_id"]))
        if per_document is not None:
            if per_document < 0:
                raise ValueError("fact probe limit must be non-negative")
            if len(ordered) > per_document:
                ordered = sorted(
                    rng.sample(ordered, per_document),
                    key=lambda item: str(item["probe_id"]),
                )
        selected.extend(ordered)
    return selected


def create_fact_probe_tasks(
    benchmark: BenchmarkBundle,
    submissions: Iterable[SubmissionBundle],
    retrieval_rows: Iterable[dict[str, Any]],
    *,
    probes_per_document: int | None,
    seed: int,
) -> ProbeTaskOutput:
    """Build blind fact-recovery tasks from method-neutral retrieval results.

    Each retrieval row identifies candidate assertion IDs for one system/probe.
    Retrieval is deliberately outside this core so every benchmark can freeze and
    report an appropriate lexical, embedding, or graph retriever independently.
    """

    retrieval: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(retrieval_rows):
        system_id = str(row.get("system_id", ""))
        probe_id = str(row.get("probe_id", ""))
        if not system_id or not probe_id:
            raise ValueError(f"retrieval_rows[{index}] requires system_id and probe_id")
        pair = (system_id, probe_id)
        if pair in retrieval:
            raise ValueError(f"duplicate retrieval result for {system_id}/{probe_id}")
        assertion_ids = row.get("assertion_ids")
        if not isinstance(assertion_ids, list) or any(
            not isinstance(item, str) for item in assertion_ids
        ):
            raise ValueError(f"retrieval_rows[{index}].assertion_ids must be strings")
        if not isinstance(row.get("retriever"), str) or not row["retriever"].strip():
            raise ValueError(f"retrieval_rows[{index}] requires retriever")
        retrieval[pair] = row

    selected = _selected_probes(benchmark, probes_per_document, seed)
    unit_maps = benchmark.unit_by_document
    tasks: list[dict[str, Any]] = []
    keys: list[dict[str, Any]] = []
    for submission in sorted(submissions, key=lambda item: item.submission_hash):
        documents = {
            str(item["document_id"]): item
            for item in submission.payload.get("documents", [])
        }
        for probe in selected:
            probe_id = str(probe["probe_id"])
            document_id = str(probe["document_id"])
            row = retrieval.get((submission.system_id, probe_id))
            if row is None:
                raise ValueError(
                    f"missing retrieval result for {submission.system_id}/{probe_id}"
                )
            document = documents[document_id]
            entities = {str(item["id"]): item for item in document.get("entities", [])}
            assertions = {
                str(item["id"]): item for item in document.get("assertions", [])
            }
            candidates: list[dict[str, Any]] = []
            for assertion_id in row["assertion_ids"]:
                if assertion_id not in assertions:
                    raise ValueError(
                        f"retrieval result {submission.system_id}/{probe_id} references "
                        f"unknown assertion {assertion_id}"
                    )
                assertion = assertions[assertion_id]
                candidates.append(
                    {
                        "subject": entities[str(assertion["subject_id"])]["name"],
                        "predicate": assertion["predicate"],
                        "object": entities[str(assertion["object_id"])]["name"],
                        "text": assertion["text"],
                        "scope": assertion.get("scope", ""),
                        "polarity": assertion.get("polarity", "positive"),
                    }
                )
            task_id = _id(seed, submission.submission_hash, probe_id)
            evidence = [
                unit_maps[document_id][str(unit_id)]
                for unit_id in probe["evidence_unit_ids"]
            ]
            tasks.append(
                {
                    "schema_version": "1.0",
                    "task_id": task_id,
                    "kind": "fact_recovery",
                    "content": {
                        "source_fact": probe["statement"],
                        "importance": probe.get("importance", ""),
                        "candidate_graph_assertions": candidates,
                    },
                    "source_evidence": evidence,
                }
            )
            keys.append(
                {
                    "task_id": task_id,
                    "system_id": submission.system_id,
                    "submission_hash": submission.submission_hash,
                    "document_id": document_id,
                    "kind": "fact_recovery",
                    "item_id": probe_id,
                    "retriever": row["retriever"],
                }
            )
    paired = sorted(zip(tasks, keys), key=lambda pair: pair[0]["task_id"])
    return ProbeTaskOutput(
        tuple(pair[0] for pair in paired), tuple(pair[1] for pair in paired)
    )
