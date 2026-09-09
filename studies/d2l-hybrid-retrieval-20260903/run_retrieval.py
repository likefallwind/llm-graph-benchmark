#!/usr/bin/env python3
"""Compare the frozen BM25 retriever with multilingual E5 and their union.

This is an experiment driver, not a core package dependency.  Run it with a
Python environment that already provides numpy and sentence-transformers.
The benchmark package itself deliberately remains dependency-free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.io import write_json, write_jsonl
from llm_graph_benchmark.probes import create_fact_probe_tasks
from llm_graph_benchmark.retrieval import retrieve_fact_probes


def parse_submission(value: str) -> tuple[str, Path]:
    system_id, separator, raw_path = value.partition("=")
    if not separator or not system_id or not raw_path:
        raise argparse.ArgumentTypeError("expected SYSTEM_ID=/path/to/submission.json")
    return system_id, Path(raw_path)


def assertion_texts(submission: SubmissionBundle) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    texts: list[str] = []
    for document in submission.payload.get("documents", []):
        entities = {str(item["id"]): item for item in document.get("entities", [])}
        for assertion in document.get("assertions", []):
            ids.append(str(assertion["id"]))
            texts.append(
                " ".join(
                    (
                        str(entities[str(assertion["subject_id"])]["name"]),
                        str(assertion.get("predicate", "")),
                        str(entities[str(assertion["object_id"])]["name"]),
                        str(assertion.get("text", "")),
                        str(assertion.get("scope", "")),
                    )
                )
            )
    return ids, texts


def embedding_retrieval(
    benchmark: BenchmarkBundle,
    submission: SubmissionBundle,
    model: SentenceTransformer,
    *,
    model_id: str,
    top_k: int,
    batch_size: int,
) -> list[dict[str, Any]]:
    assertion_ids, texts = assertion_texts(submission)
    passage_embeddings = model.encode(
        [f"passage: {text}" for text in texts],
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    probes = sorted(benchmark.fact_probes, key=lambda item: str(item["probe_id"]))
    query_embeddings = model.encode(
        [f"query: {probe['statement']}" for probe in probes],
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    similarities = np.asarray(query_embeddings) @ np.asarray(passage_embeddings).T
    rows: list[dict[str, Any]] = []
    for probe, scores in zip(probes, similarities):
        ordered = np.argsort(-scores, kind="stable")[:top_k]
        rows.append(
            {
                "system_id": submission.system_id,
                "probe_id": str(probe["probe_id"]),
                "retriever": f"multilingual-e5-small-cosine-v1:{model_id}",
                "assertion_ids": [assertion_ids[int(index)] for index in ordered],
                "scores": [round(float(scores[int(index)]), 8) for index in ordered],
                "retriever_params": {
                    "top_k": top_k,
                    "query_prefix": "query: ",
                    "passage_prefix": "passage: ",
                    "normalized": True,
                    "similarity": "cosine",
                },
            }
        )
    return rows


def union_retrieval(
    bm25_rows: list[dict[str, Any]], embedding_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    embedding_by_probe = {str(row["probe_id"]): row for row in embedding_rows}
    union_rows: list[dict[str, Any]] = []
    probe_stats: list[dict[str, Any]] = []
    for bm25 in bm25_rows:
        probe_id = str(bm25["probe_id"])
        embedding = embedding_by_probe[probe_id]
        bm25_ids = list(bm25["assertion_ids"])
        embedding_ids = list(embedding["assertion_ids"])
        overlap = set(bm25_ids) & set(embedding_ids)
        # Preserve the existing BM25 presentation order, then append genuinely
        # new semantic candidates.  This isolates candidate-set expansion from
        # reranking effects in the paired judge comparison.
        union_ids = [*bm25_ids, *(item for item in embedding_ids if item not in set(bm25_ids))]
        union_rows.append(
            {
                "system_id": bm25["system_id"],
                "probe_id": probe_id,
                "retriever": "union-bm25-10-plus-e5-10-v1",
                "assertion_ids": union_ids,
                "retriever_params": {
                    "bm25_retriever": bm25["retriever"],
                    "embedding_retriever": embedding["retriever"],
                    "ordering": "bm25_first_then_embedding_only",
                },
            }
        )
        probe_stats.append(
            {
                "probe_id": probe_id,
                "bm25_count": len(bm25_ids),
                "embedding_count": len(embedding_ids),
                "overlap_count": len(overlap),
                "union_count": len(union_ids),
                "embedding_only_count": len(set(embedding_ids) - set(bm25_ids)),
                "overlap_ids": sorted(overlap),
            }
        )
    return union_rows, {
        "probe_count": len(probe_stats),
        "mean_overlap_count": round(
            sum(item["overlap_count"] for item in probe_stats) / len(probe_stats), 6
        ),
        "mean_union_count": round(
            sum(item["union_count"] for item in probe_stats) / len(probe_stats), 6
        ),
        "mean_embedding_only_count": round(
            sum(item["embedding_only_count"] for item in probe_stats) / len(probe_stats),
            6,
        ),
        "per_probe": probe_stats,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--submission", action="append", type=parse_submission, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", default="cpu")
    # Match evaluate_submission.py so task IDs pair exactly with the existing
    # BM25 judgments.  The CaRB judging pool used a different shuffle seed but
    # did not regenerate task IDs.
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()

    benchmark = BenchmarkBundle.load(args.benchmark)
    model = SentenceTransformer(str(args.model), device=args.device)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, Any] = {}
    manifest_systems: dict[str, Any] = {}

    for requested_system_id, path in args.submission:
        submission = SubmissionBundle.load(path)
        if requested_system_id != submission.system_id:
            raise ValueError(
                f"requested system id {requested_system_id!r} does not match "
                f"submission system id {submission.system_id!r}"
            )
        system_out = args.out_dir / requested_system_id
        system_out.mkdir(parents=True, exist_ok=True)
        bm25_rows = list(
            retrieve_fact_probes(
                benchmark, [submission], top_k=args.top_k, k1=1.2, b=0.75
            )
        )
        embedding_rows = embedding_retrieval(
            benchmark,
            submission,
            model,
            model_id=args.model_id,
            top_k=args.top_k,
            batch_size=args.batch_size,
        )
        union_rows, summary = union_retrieval(bm25_rows, embedding_rows)
        embedding_tasks = create_fact_probe_tasks(
            benchmark,
            [submission],
            embedding_rows,
            probes_per_document=None,
            seed=args.seed,
        )
        union_tasks = create_fact_probe_tasks(
            benchmark,
            [submission],
            union_rows,
            probes_per_document=None,
            seed=args.seed,
        )
        write_jsonl(system_out / "retrieval-bm25.jsonl", bm25_rows)
        write_jsonl(system_out / "retrieval-embedding.jsonl", embedding_rows)
        write_jsonl(system_out / "retrieval-union.jsonl", union_rows)
        write_jsonl(system_out / "embedding-tasks.jsonl", embedding_tasks.tasks)
        write_jsonl(system_out / "embedding-task-key.jsonl", embedding_tasks.key)
        # Keep the conventional names for compatibility with judge_carb.py.
        write_jsonl(system_out / "all-tasks.jsonl", union_tasks.tasks)
        write_jsonl(system_out / "all-task-key.jsonl", union_tasks.key)
        write_json(system_out / "retrieval-summary.json", summary)
        summaries[requested_system_id] = summary
        manifest_systems[requested_system_id] = {
            "submission_path": str(path.resolve()),
            "submission_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "assertion_count": sum(
                len(document.get("assertions", []))
                for document in submission.payload.get("documents", [])
            ),
        }

    write_json(
        args.out_dir / "manifest.json",
        {
            "schema_version": "1.0",
            "experiment": "bm25-10-vs-e5-10-vs-union",
            "benchmark_path": str(args.benchmark.resolve()),
            "benchmark_sha256": hashlib.sha256(args.benchmark.read_bytes()).hexdigest(),
            "embedding_model_path": str(args.model.resolve()),
            "embedding_model_id": args.model_id,
            "device": args.device,
            "top_k": args.top_k,
            "seed": args.seed,
            "systems": manifest_systems,
        },
    )
    write_json(args.out_dir / "retrieval-summary.json", summaries)


if __name__ == "__main__":
    main()
