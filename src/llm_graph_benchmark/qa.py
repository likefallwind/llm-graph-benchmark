from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable

from .bundle import BenchmarkBundle, SubmissionBundle


@dataclass(frozen=True)
class QATaskOutput:
    tasks: tuple[dict[str, Any], ...]
    key: tuple[dict[str, Any], ...]


def _task_id(seed: int, submission_hash: str, qa_id: str) -> str:
    raw = f"{seed}|{submission_hash}|book_qa|{qa_id}".encode()
    return "t_" + hashlib.sha256(raw).hexdigest()[:20]


def create_qa_tasks(
    benchmark: BenchmarkBundle,
    submissions: Iterable[SubmissionBundle],
    retrieval_rows: Iterable[dict[str, Any]],
    *,
    seed: int,
) -> QATaskOutput:
    retrieval: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(retrieval_rows):
        system_id = str(row.get("system_id", ""))
        qa_id = str(row.get("qa_id", ""))
        if not system_id or not qa_id:
            raise ValueError(f"retrieval_rows[{index}] requires system_id and qa_id")
        pair = (system_id, qa_id)
        if pair in retrieval:
            raise ValueError(f"duplicate QA retrieval result for {system_id}/{qa_id}")
        assertion_ids = row.get("assertion_ids")
        if not isinstance(assertion_ids, list) or any(
            not isinstance(item, str) for item in assertion_ids
        ):
            raise ValueError(f"retrieval_rows[{index}].assertion_ids must be strings")
        retrieval[pair] = row

    tasks: list[dict[str, Any]] = []
    keys: list[dict[str, Any]] = []
    for submission in sorted(submissions, key=lambda item: item.submission_hash):
        documents = {
            str(item["document_id"]): item
            for item in submission.payload.get("documents", [])
        }
        for probe in sorted(benchmark.qa_probes, key=lambda item: str(item["qa_id"])):
            qa_id = str(probe["qa_id"])
            document_id = str(probe["document_id"])
            row = retrieval.get((submission.system_id, qa_id))
            if row is None:
                raise ValueError(f"missing QA retrieval result for {submission.system_id}/{qa_id}")
            document = documents[document_id]
            entities = {str(item["id"]): item for item in document.get("entities", [])}
            assertions = {
                str(item["id"]): item for item in document.get("assertions", [])
            }
            candidates = []
            for assertion_id in row["assertion_ids"]:
                if assertion_id not in assertions:
                    raise ValueError(
                        f"QA retrieval {submission.system_id}/{qa_id} references "
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
            task_id = _task_id(seed, submission.submission_hash, qa_id)
            tasks.append(
                {
                    "schema_version": "1.0",
                    "task_id": task_id,
                    "kind": "book_qa",
                    "content": {
                        "question": probe["question"],
                        "reference_answer": probe["reference_answer"],
                        "candidate_graph_assertions": candidates,
                    },
                    "source_evidence": [
                        benchmark.unit_by_document[document_id][str(unit_id)]
                        for unit_id in probe["evidence_unit_ids"]
                    ],
                }
            )
            keys.append(
                {
                    "task_id": task_id,
                    "system_id": submission.system_id,
                    "submission_hash": submission.submission_hash,
                    "document_id": document_id,
                    "kind": "book_qa",
                    "item_id": qa_id,
                    "retriever": row["retriever"],
                    "strata": (
                        dict(probe["metadata"])
                        if isinstance(probe.get("metadata"), dict)
                        else {}
                    ),
                }
            )
    paired = sorted(zip(tasks, keys), key=lambda pair: pair[0]["task_id"])
    return QATaskOutput(
        tuple(task for task, _ in paired), tuple(item for _, item in paired)
    )
