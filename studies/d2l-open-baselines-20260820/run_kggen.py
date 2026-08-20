from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import dspy
from kg_gen import KGGen
from kg_gen.models import Graph
from kg_gen.steps._3_deduplicate import DeduplicateMethod

from llm_graph_benchmark.adapters.triples import submission_from_triples


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--document-id", default="d2l-zh-official")
    parser.add_argument("--kggen-repo", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="ollama_chat/qwen3:8b")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    chunks = read_jsonl(args.corpus)
    if args.limit is not None:
        chunks = chunks[: args.limit]
    raw_dir = args.out_dir / "chunks"
    raw_dir.mkdir(parents=True, exist_ok=True)

    kg = KGGen(model=args.model, max_tokens=args.max_tokens, temperature=0.0, disable_cache=True)
    kg.lm = dspy.LM(
        model=args.model,
        temperature=0.0,
        max_tokens=args.max_tokens,
        cache=False,
        extra_body={"think": False},
    )

    started = time.time()
    failures = []
    for position, chunk in enumerate(chunks, start=1):
        output_path = raw_dir / f"chunk-{chunk['chunk_index']:04d}.json"
        if output_path.exists():
            continue
        chunk_started = time.time()
        try:
            graph = kg.generate(chunk["text"], deduplication_method=None)
            row = {
                "status": "done",
                "chunk_index": chunk["chunk_index"],
                "unit_ids": chunk["unit_ids"],
                "elapsed_seconds": time.time() - chunk_started,
                "graph": graph.model_dump(mode="json"),
            }
        except Exception as exc:
            row = {
                "status": "failed",
                "chunk_index": chunk["chunk_index"],
                "unit_ids": chunk["unit_ids"],
                "elapsed_seconds": time.time() - chunk_started,
                "error": f"{type(exc).__name__}: {exc}",
            }
            failures.append(row)
        write_json(output_path, row)
        print(f"[{position}/{len(chunks)}] chunk={chunk['chunk_index']} status={row['status']}", flush=True)

    rows = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(raw_dir.glob("chunk-*.json"))]
    completed = [row for row in rows if row.get("status") == "done"]
    raw_triples: list[dict] = []
    entity_units: dict[str, set[str]] = defaultdict(set)
    for row in completed:
        unit_ids = row["unit_ids"]
        graph = row["graph"]
        for entity in graph.get("entities", []):
            if str(entity).strip():
                entity_units[str(entity).strip()].update(unit_ids)
        for relation in graph.get("relations", []):
            if len(relation) != 3:
                continue
            subject, predicate, obj = map(str, relation)
            raw_triples.append({"subject": subject, "predicate": predicate, "object": obj, "evidence_unit_ids": unit_ids})
            entity_units[subject.strip()].update(unit_ids)
            entity_units[obj.strip()].update(unit_ids)

    endpoint_names = {name for name in entity_units if name}
    aggregate = Graph(
        entities=endpoint_names,
        edges={row["predicate"] for row in raw_triples if row["predicate"].strip()},
        relations={
            (row["subject"], row["predicate"], row["object"])
            for row in raw_triples
            if all(str(row[key]).strip() for key in ("subject", "predicate", "object"))
        },
        entity_metadata={name: units for name, units in entity_units.items() if name},
    )
    final_graph = (
        kg.deduplicate(aggregate, method=DeduplicateMethod.SEMHASH)
        if aggregate.entities and aggregate.edges
        else aggregate
    )
    final_entity_units = final_graph.entity_metadata or {}
    entity_records = [
        {"name": name, "evidence_unit_ids": sorted(final_entity_units.get(name, set()))}
        for name in sorted(final_graph.entities)
    ]
    exact_evidence = defaultdict(set)
    for row in raw_triples:
        exact_evidence[(row["subject"], row["predicate"], row["object"])].update(row["evidence_unit_ids"])
    final_triples = []
    for subject, predicate, obj in sorted(final_graph.relations):
        evidence = exact_evidence.get((subject, predicate, obj), set())
        if not evidence:
            left = set(final_entity_units.get(subject, set()))
            right = set(final_entity_units.get(obj, set()))
            evidence = left & right or left | right
        final_triples.append({"subject": subject, "predicate": predicate, "object": obj, "evidence_unit_ids": sorted(evidence)})

    commit = subprocess.check_output(["git", "-C", str(args.kggen_repo), "rev-parse", "HEAD"], text=True).strip()
    elapsed = sum(float(row.get("elapsed_seconds", 0)) for row in rows)
    submission, adapter_report = submission_from_triples(
        final_triples,
        entity_records=entity_records,
        benchmark_id=args.benchmark_id,
        document_id=args.document_id,
        system_id="kggen-qwen3-8b-local",
        system_name="KGGen",
        system_version=f"0.4.0+{commit[:12]}",
        runtime={"elapsed_seconds": elapsed, "cost_usd": 0.0},
        metadata={
            "upstream_repository": "https://github.com/stair-lab/kg-gen",
            "upstream_commit": commit,
            "model": args.model,
            "temperature": 0.0,
            "deduplication_method": "semhash",
            "semhash_similarity_threshold": 0.95,
            "provenance_granularity": "source chunk; shared endpoint provenance after changed dedup triples",
            "thinking_disabled": True,
        },
    )
    write_json(args.out_dir / "submission.json", submission)
    write_json(args.out_dir / "adapter-report.json", adapter_report)
    write_json(args.out_dir / "run-report.json", {
        "requested_chunks": len(chunks),
        "completed_chunks": len(completed),
        "failed_chunks": len(rows) - len(completed),
        "wall_seconds_this_invocation": time.time() - started,
        "recorded_chunk_seconds": elapsed,
        "raw_entities": len(endpoint_names),
        "raw_triples": len(raw_triples),
        "final_entities": len(final_graph.entities),
        "final_triples": len(final_graph.relations),
        "failures": failures,
    })


if __name__ == "__main__":
    main()
