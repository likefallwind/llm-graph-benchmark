from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any, Iterable

from .bundle import BenchmarkBundle, SubmissionBundle


RETRIEVER_ID = "char-ngram-bm25-v1"
_PARTS = re.compile(r"[\u3400-\u9fff]+|[a-z0-9_]+")


def _tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).lower()
    tokens: list[str] = []
    for part in _PARTS.findall(normalized):
        if all("\u3400" <= char <= "\u9fff" for char in part):
            tokens.extend(part)
            tokens.extend(part[index : index + 2] for index in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


def _assertion_text(
    assertion: dict[str, Any], entities: dict[str, dict[str, Any]]
) -> str:
    return " ".join(
        (
            str(entities[str(assertion["subject_id"])]["name"]),
            str(assertion.get("predicate", "")),
            str(entities[str(assertion["object_id"])]["name"]),
            str(assertion.get("text", "")),
            str(assertion.get("scope", "")),
        )
    )


def _index(document: dict[str, Any]):
    entities = {str(item["id"]): item for item in document.get("entities", [])}
    assertions = list(document.get("assertions", []))
    token_counts = [Counter(_tokens(_assertion_text(item, entities))) for item in assertions]
    lengths = [sum(counts.values()) for counts in token_counts]
    average_length = sum(lengths) / len(lengths) if lengths else 0.0
    document_frequency: Counter[str] = Counter()
    for counts in token_counts:
        document_frequency.update(counts.keys())
    return assertions, token_counts, lengths, average_length, document_frequency


def _rank(
    query: str,
    document: dict[str, Any],
    *,
    top_k: int,
    k1: float,
    b: float,
    _prepared=None,
) -> list[str]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if k1 <= 0:
        raise ValueError("k1 must be positive")
    if b < 0 or b > 1:
        raise ValueError("b must satisfy 0 <= b <= 1")
    assertions, token_counts, lengths, average_length, document_frequency = (
        _prepared if _prepared is not None else _index(document)
    )
    if not token_counts:
        return []
    query_tokens = set(_tokens(query))
    scored: list[tuple[float, str]] = []
    total = len(assertions)
    for assertion, counts, length in zip(assertions, token_counts, lengths):
        score = 0.0
        for token in query_tokens:
            frequency = counts[token]
            if not frequency:
                continue
            df = document_frequency[token]
            inverse_frequency = math.log(1 + (total - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (
                1 - b + b * length / average_length
            )
            score += inverse_frequency * frequency * (k1 + 1) / denominator
        if score > 0:
            scored.append((score, str(assertion["id"])))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [assertion_id for _, assertion_id in scored[:top_k]]


def retrieve_fact_probes(
    benchmark: BenchmarkBundle,
    submissions: Iterable[SubmissionBundle],
    *,
    top_k: int = 10,
    k1: float = 1.2,
    b: float = 0.75,
) -> tuple[dict[str, Any], ...]:
    """Retrieve candidate assertions using graph text only.

    Source passages and submitted evidence references are deliberately excluded
    from indexing, so systems with native provenance do not receive an advantage.
    """

    rows: list[dict[str, Any]] = []
    for submission in sorted(submissions, key=lambda item: item.system_id):
        documents = {
            str(item["document_id"]): item
            for item in submission.payload.get("documents", [])
        }
        indexes = {did: _index(document) for did, document in documents.items()}
        for probe in sorted(benchmark.fact_probes, key=lambda item: str(item["probe_id"])):
            document_id = str(probe["document_id"])
            rows.append(
                {
                    "system_id": submission.system_id,
                    "probe_id": str(probe["probe_id"]),
                    "retriever": RETRIEVER_ID,
                    "assertion_ids": _rank(
                        str(probe["statement"]),
                        documents[document_id],
                        top_k=top_k,
                        k1=k1,
                        b=b,
                        _prepared=indexes[document_id],
                    ),
                    "retriever_params": {"top_k": top_k, "k1": k1, "b": b},
                }
            )
    return tuple(rows)


def retrieve_qa_probes(
    benchmark: BenchmarkBundle,
    submissions: Iterable[SubmissionBundle],
    *,
    top_k: int = 10,
    k1: float = 1.2,
    b: float = 0.75,
) -> tuple[dict[str, Any], ...]:
    """Retrieve graph assertions for frozen book-QA questions without source text."""

    rows: list[dict[str, Any]] = []
    for submission in sorted(submissions, key=lambda item: item.system_id):
        documents = {
            str(item["document_id"]): item
            for item in submission.payload.get("documents", [])
        }
        indexes = {did: _index(document) for did, document in documents.items()}
        for probe in sorted(benchmark.qa_probes, key=lambda item: str(item["qa_id"])):
            document_id = str(probe["document_id"])
            rows.append(
                {
                    "system_id": submission.system_id,
                    "qa_id": str(probe["qa_id"]),
                    "retriever": RETRIEVER_ID,
                    "assertion_ids": _rank(
                        str(probe["question"]),
                        documents[document_id],
                        top_k=top_k,
                        k1=k1,
                        b=b,
                        _prepared=indexes[document_id],
                    ),
                    "retriever_params": {"top_k": top_k, "k1": k1, "b": b},
                }
            )
    return tuple(rows)
