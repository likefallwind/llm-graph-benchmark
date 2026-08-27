from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import dspy
from kg_gen import KGGen
from kg_gen.models import Graph
from kg_gen.steps._3_deduplicate import DeduplicateMethod
from kg_gen.utils.deduplicate import DeduplicateList
from semhash import SemHash

from llm_graph_benchmark.adapters.triples import submission_from_triples


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_api_key(*, env_name: str | None, env_file: Path | None, key_name: str) -> str | None:
    value = os.environ.get(env_name, "") if env_name else ""
    if not value and env_file:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                name, candidate = stripped.split("=", 1)
                if name.strip() == key_name:
                    value = candidate.strip().strip("'\"")
                    break
    return value.split(",", 1)[0].strip() or None


def default_system_id(model: str) -> str:
    return "kggen-" + re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")


def install_semhash_compatibility() -> str:
    """Bridge KGGen's pre-0.3 SemHash result name to SemHash 0.3.2.

    KGGen 0.4.0 reads ``DeduplicationResult.duplicates`` while its declared
    ``semhash>=0.3.2`` dependency exposes the same records as ``filtered``.
    Keep KGGen's normalization and representative-selection behavior unchanged,
    but accept either released result shape.
    """

    probe = SemHash.from_records(["compatibility probe"]).self_deduplicate()
    if hasattr(probe, "duplicates"):
        return "native-duplicates"

    def deduplicate(self: DeduplicateList, items: list[str]) -> list[str]:
        self.total_items = len(items)
        normalized_items = set()
        for item in items:
            normalized = self.normalize(item)
            singular = self.singularize(normalized)
            self.original_map[item] = singular
            self.items_map[singular] = item
            normalized_items.add(singular)

        result = SemHash.from_records(sorted(normalized_items)).self_deduplicate(
            threshold=self.threshold
        )
        duplicate_records = result.filtered
        self.deduplicated_items = len(result.selected)
        self.duplicate_items = len(duplicate_records)
        self.reduction = (
            self.duplicate_items / self.total_items * 100 if self.total_items else 0.0
        )
        for duplicate in duplicate_records:
            original = duplicate.record
            if duplicate.duplicates:
                duplicate_value = duplicate.duplicates[0][0]
                self.items_map[original] = self.items_map[duplicate_value]
                self.duplicates.setdefault(original, duplicate_value)
        self.deduplicated = result.selected
        return self.deduplicated

    DeduplicateList.deduplicate = deduplicate
    return "kggen-0.4.0-semhash-0.3.2-filtered-bridge"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--document-id", default="d2l-zh-official")
    parser.add_argument("--kggen-repo", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="ollama_chat/qwen3:8b")
    parser.add_argument("--api-base")
    parser.add_argument("--api-key-env")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--api-key-name", default="GATEWAY_KEYS")
    parser.add_argument("--system-id")
    parser.add_argument("--disable-thinking", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--dedup-method",
        choices=["semhash", "exact"],
        default="semhash",
        help=(
            "semhash: KGGen's default semantic dedup. exact: skip semantic dedup "
            "and keep only the exact-string merge the aggregate already performs. "
            "SemHash embeds with an English-only model, so on CJK corpora it "
            "collapses unrelated predicates into one representative."
        ),
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    chunks = read_jsonl(args.corpus)
    if args.limit is not None:
        chunks = chunks[: args.limit]
    raw_dir = args.out_dir / "chunks"
    raw_dir.mkdir(parents=True, exist_ok=True)

    api_key = load_api_key(
        env_name=args.api_key_env,
        env_file=args.api_key_file,
        key_name=args.api_key_name,
    )
    lm_options = {
        "model": args.model,
        "api_key": api_key,
        "api_base": args.api_base,
        "temperature": 0.0,
        "max_tokens": args.max_tokens,
        "cache": False,
        # The gateway implements chat/completions, not the OpenAI Responses API.
        "model_type": "chat",
    }
    if args.disable_thinking:
        lm_options["extra_body"] = {"think": False}

    def build_kg() -> KGGen:
        instance = KGGen(
            model=args.model,
            api_key=api_key,
            api_base=args.api_base,
            max_tokens=args.max_tokens,
            temperature=0.0,
            disable_cache=True,
        )
        instance.lm = dspy.LM(**lm_options)
        return instance

    kg = build_kg()
    worker_state = threading.local()

    def worker_kg() -> KGGen:
        if not hasattr(worker_state, "kg"):
            worker_state.kg = build_kg()
        return worker_state.kg

    def history_usage(entries: list[dict]) -> dict:
        input_tokens = output_tokens = reasoning_tokens = total_tokens = 0
        response_models = set()
        costs = []
        for entry in entries:
            usage = entry.get("usage") or {}
            input_tokens += int(usage.get("prompt_tokens") or 0)
            output_tokens += int(usage.get("completion_tokens") or 0)
            total_tokens += int(usage.get("total_tokens") or 0)
            details = usage.get("completion_tokens_details") or {}
            if hasattr(details, "model_dump"):
                details = details.model_dump()
            reasoning_tokens += int(
                details.get("reasoning_tokens") or 0
                if isinstance(details, dict)
                else getattr(details, "reasoning_tokens", 0) or 0
            )
            if entry.get("response_model"):
                response_models.add(str(entry["response_model"]))
            if entry.get("cost") is not None:
                costs.append(float(entry["cost"]))
        return {
            "requests": len(entries),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens or input_tokens + output_tokens,
            "response_models": sorted(response_models),
            "cost_usd": round(sum(costs), 9) if len(costs) == len(entries) else None,
        }

    started = time.time()
    failures = []
    pending = []
    for chunk in chunks:
        output_path = raw_dir / f"chunk-{chunk['chunk_index']:04d}.json"
        if output_path.exists():
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if existing.get("status") == "done":
                continue
        pending.append(chunk)

    def extract(chunk: dict) -> tuple[Path, dict]:
        output_path = raw_dir / f"chunk-{chunk['chunk_index']:04d}.json"
        previous_attempts: list[dict] = []
        if output_path.exists():
            previous = json.loads(output_path.read_text(encoding="utf-8"))
            previous_attempts = list(previous.get("attempts") or [])
            if not previous_attempts:
                previous_attempts.append(
                    {
                        "status": previous.get("status"),
                        "elapsed_seconds": previous.get("elapsed_seconds", 0),
                        "usage": previous.get("usage", {}),
                        "error": previous.get("error"),
                    }
                )
        chunk_started = time.time()
        extractor = worker_kg()
        history_start = len(extractor.lm.history)
        try:
            graph = extractor.generate(chunk["text"], deduplication_method=None)
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
        row["usage"] = history_usage(extractor.lm.history[history_start:])
        row["attempts"] = previous_attempts + [
            {
                "status": row["status"],
                "elapsed_seconds": row["elapsed_seconds"],
                "usage": row["usage"],
                "error": row.get("error"),
            }
        ]
        return output_path, row

    completed_this_invocation = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(extract, chunk): chunk for chunk in pending}
        for future in as_completed(futures):
            output_path, row = future.result()
            write_json(output_path, row)
            completed_this_invocation += 1
            if row["status"] != "done":
                failures.append(row)
            print(
                f"[{completed_this_invocation}/{len(pending)} pending; {len(chunks)} total] "
                f"chunk={row['chunk_index']} status={row['status']}",
                flush=True,
            )

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
    if args.dedup_method == "semhash":
        semhash_compatibility = install_semhash_compatibility()
        final_graph = (
            kg.deduplicate(aggregate, method=DeduplicateMethod.SEMHASH)
            if aggregate.entities and aggregate.edges
            else aggregate
        )
    else:
        semhash_compatibility = None
        final_graph = aggregate
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
    def attempts(row: dict) -> list[dict]:
        return row.get("attempts") or [row]

    elapsed = sum(
        float(attempt.get("elapsed_seconds", 0))
        for row in rows
        for attempt in attempts(row)
    )
    usage_available = all("usage" in row for row in completed)
    input_tokens = sum(
        int(attempt.get("usage", {}).get("input_tokens") or 0)
        for row in rows
        for attempt in attempts(row)
    )
    output_tokens = sum(
        int(attempt.get("usage", {}).get("output_tokens") or 0)
        for row in rows
        for attempt in attempts(row)
    )
    reasoning_tokens = sum(
        int(attempt.get("usage", {}).get("reasoning_tokens") or 0)
        for row in rows
        for attempt in attempts(row)
    )
    response_models = sorted(
        {
            model
            for row in rows
            for attempt in attempts(row)
            for model in attempt.get("usage", {}).get("response_models", [])
        }
    )
    runtime = {"elapsed_seconds": elapsed}
    if usage_available:
        runtime.update(input_tokens=input_tokens, output_tokens=output_tokens)
    submission, adapter_report = submission_from_triples(
        final_triples,
        entity_records=entity_records,
        benchmark_id=args.benchmark_id,
        document_id=args.document_id,
        system_id=args.system_id or default_system_id(args.model),
        system_name="KGGen",
        system_version=f"0.4.0+{commit[:12]}",
        runtime=runtime,
        metadata={
            "upstream_repository": "https://github.com/stair-lab/kg-gen",
            "upstream_commit": commit,
            "model": args.model,
            "temperature": 0.0,
            "deduplication_method": args.dedup_method,
            "semhash_similarity_threshold": (
                0.95 if args.dedup_method == "semhash" else None
            ),
            "semhash_compatibility": semhash_compatibility,
            "provenance_granularity": "source chunk; shared endpoint provenance after changed dedup triples",
            "api_base": args.api_base,
            "thinking_disabled": args.disable_thinking,
            "credential_source": "runtime environment or untracked env file",
        },
    )
    write_json(args.out_dir / "submission.json", submission)
    write_json(args.out_dir / "adapter-report.json", adapter_report)
    write_json(args.out_dir / "run-report.json", {
        "requested_chunks": len(chunks),
        "completed_chunks": len(completed),
        "failed_chunks": len(rows) - len(completed),
        "workers": args.workers,
        "wall_seconds_this_invocation": time.time() - started,
        "recorded_chunk_seconds": elapsed,
        "raw_entities": len(endpoint_names),
        "raw_triples": len(raw_triples),
        "final_entities": len(final_graph.entities),
        "final_triples": len(final_graph.relations),
        "usage": {
            "available_for_all_completed_chunks": usage_available,
            "input_tokens": input_tokens if usage_available else None,
            "output_tokens": output_tokens if usage_available else None,
            "reasoning_tokens": reasoning_tokens if usage_available else None,
            "response_models": response_models,
            "cost_usd": None,
            "cost_limitation": "Provider responses expose token usage, but no authoritative per-request price was recorded.",
        },
        "failures": failures,
    })
    if len(rows) != len(chunks) or len(completed) != len(chunks):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
