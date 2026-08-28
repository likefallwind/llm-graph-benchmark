from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from openai import NOT_GIVEN, OpenAI

from atlas_rag.kg_construction.triple_config import ProcessingConfig
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.llm_generator import GenerationConfig, LLMGenerator
from llm_graph_benchmark.adapters.triples import submission_from_triples


class OllamaGenerationConfig(GenerationConfig):
    """Transport-only compatibility: Ollama exposes Qwen thinking as `think`."""

    def to_extra_body(self, backend: str) -> dict[str, Any]:
        body = super().to_extra_body(backend)
        if body is NOT_GIVEN:
            body = {}
        return {**body, "think": False}


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
    return "autoschemakg-" + re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(value: object) -> str:
    return str(value or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--document-id", default="d2l-zh-official")
    parser.add_argument("--autoschemakg-repo", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--api-key-env")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--api-key-name", default="GATEWAY_KEYS")
    parser.add_argument("--system-id")
    parser.add_argument("--disable-thinking", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--assemble-only", action="store_true")
    parser.add_argument("--no-assemble", action="store_true")
    args = parser.parse_args()

    chunks = read_jsonl(args.corpus)
    chunks = chunks[args.offset :]
    if args.limit is not None:
        chunks = chunks[: args.limit]
    # Shard workers extract disjoint chunks but share one raw directory, so any
    # worker order still yields the same per-chunk artifacts.
    if args.assemble_only:
        chunks = []
    elif args.shards > 1:
        chunks = chunks[args.shard_index :: args.shards]
    input_dir = args.out_dir / "input"
    raw_dir = args.out_dir / "chunks"
    upstream_dir = args.out_dir / "upstream"
    input_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    upstream_dir.mkdir(parents=True, exist_ok=True)

    api_key = load_api_key(
        env_name=args.api_key_env,
        env_file=args.api_key_file,
        key_name=args.api_key_name,
    ) or "ollama-local"
    client = OpenAI(base_url=args.base_url, api_key=api_key)
    generation_config_class = OllamaGenerationConfig if args.disable_thinking else GenerationConfig
    generator = LLMGenerator(
        client,
        model_name=args.model,
        backend="custom",
        max_workers=1,
        default_config=generation_config_class(
            max_tokens=args.max_tokens,
            temperature=0.0,
            do_sample=False,
            seed=20260820,
        ),
    )

    started = time.time()
    failures: list[dict] = []
    for position, chunk in enumerate(chunks, start=1):
        index = int(chunk["chunk_index"])
        raw_path = raw_dir / f"chunk-{index:04d}.json"
        if raw_path.exists():
            continue
        prefix = f"chunk-{index:04d}"
        input_path = input_dir / f"{prefix}.json"
        write_json(
            input_path,
            [
                {
                    "id": str(index),
                    "text": chunk["text"],
                    "metadata": {"lang": "zh-CN", "unit_ids": chunk["unit_ids"]},
                }
            ],
        )
        chunk_started = time.time()
        try:
            config = ProcessingConfig(
                model_path=args.model,
                data_directory=str(input_dir),
                filename_pattern=prefix,
                batch_size_triple=1,
                output_directory=str(upstream_dir / prefix),
                max_new_tokens=args.max_tokens,
                max_workers=1,
                record=True,
                allow_empty=True,
                include_concept=False,
                chunk_size=8192,
                chunk_overlap=0,
            )
            extractor = KnowledgeGraphExtractor(model=generator, config=config)
            extractor.run_extraction()
            output_files = sorted((upstream_dir / prefix / "kg_extraction").glob("*.json"))
            if not output_files:
                raise RuntimeError("upstream did not create a KG extraction JSON file")
            rows = read_jsonl(output_files[-1])
            if len(rows) != 1:
                raise RuntimeError(f"expected one upstream row, got {len(rows)}")
            result = {
                "status": "done",
                "chunk_index": index,
                "unit_ids": chunk["unit_ids"],
                "elapsed_seconds": time.time() - chunk_started,
                "result": rows[0],
            }
        except Exception as exc:
            result = {
                "status": "failed",
                "chunk_index": index,
                "unit_ids": chunk["unit_ids"],
                "elapsed_seconds": time.time() - chunk_started,
                "error": f"{type(exc).__name__}: {exc}",
            }
            failures.append(result)
        write_json(raw_path, result)
        print(f"[{position}/{len(chunks)}] chunk={index} status={result['status']}", flush=True)

    if args.no_assemble:
        write_json(args.out_dir / f"shard-report-{args.shard_index:02d}.json", {
            "shard_index": args.shard_index,
            "shards": args.shards,
            "requested_chunks": len(chunks),
            "failed_chunks": len(failures),
            "wall_seconds_this_invocation": time.time() - started,
            "failures": failures,
        })
        return

    rows = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(raw_dir.glob("chunk-*.json"))]
    triples: list[dict] = []
    endpoint_types: dict[str, set[str]] = {}

    def mark(name: str, kind: str) -> None:
        if name:
            endpoint_types.setdefault(name, set()).add(kind)

    for row in rows:
        if row.get("status") != "done":
            continue
        result = row["result"]
        evidence = row["unit_ids"]
        for item in result.get("entity_relation_dict", []):
            head, relation, tail = clean(item.get("Head")), clean(item.get("Relation")), clean(item.get("Tail"))
            triples.append({"subject": head, "predicate": relation, "object": tail, "evidence_unit_ids": evidence})
            mark(head, "entity")
            mark(tail, "entity")
        for item in result.get("event_relation_dict", []):
            head, relation, tail = clean(item.get("Head")), clean(item.get("Relation")), clean(item.get("Tail"))
            triples.append({"subject": head, "predicate": relation, "object": tail, "evidence_unit_ids": evidence})
            mark(head, "event")
            mark(tail, "event")
        for item in result.get("event_entity_dict", []):
            event = clean(item.get("Event"))
            mark(event, "event")
            for value in item.get("Entity", []):
                entity = clean(value)
                triples.append({
                    "subject": event,
                    "predicate": "is participated by",
                    "object": entity,
                    "text": f"{event} 由 {entity} 参与。",
                    "evidence_unit_ids": evidence,
                })
                mark(entity, "entity")

    entity_records = [
        {"name": name, "types": sorted(types)} for name, types in sorted(endpoint_types.items())
    ]
    commit = subprocess.check_output(["git", "-C", str(args.autoschemakg_repo), "rev-parse", "HEAD"], text=True).strip()
    elapsed = sum(float(row.get("elapsed_seconds", 0)) for row in rows)
    submission, adapter_report = submission_from_triples(
        triples,
        entity_records=entity_records,
        benchmark_id=args.benchmark_id,
        document_id=args.document_id,
        system_id=args.system_id or default_system_id(args.model),
        system_name="AutoSchemaKG extraction stage",
        system_version=f"0.0.5+{commit[:12]}",
        runtime={"elapsed_seconds": elapsed},
        metadata={
            "upstream_repository": "https://github.com/HKUST-KnowComp/AutoSchemaKG",
            "upstream_commit": commit,
            "model": args.model,
            "language": "zh-CN",
            "temperature": 0.0,
            "api_base": args.base_url,
            "thinking_disabled": args.disable_thinking,
            "credential_source": "runtime environment or untracked env file",
            "scope": "official entity/event extraction stage; schema conceptualization excluded",
            "provenance_granularity": "frozen source chunk",
            "event_entity_relation": "official converter predicate: is participated by",
        },
    )
    write_json(args.out_dir / "submission.json", submission)
    write_json(args.out_dir / "adapter-report.json", adapter_report)
    write_json(args.out_dir / "run-report.json", {
        "requested_chunks": len(chunks),
        "completed_chunks": sum(row.get("status") == "done" for row in rows),
        "failed_chunks": sum(row.get("status") != "done" for row in rows),
        "recorded_chunk_seconds": elapsed,
        "wall_seconds_this_invocation": time.time() - started,
        "raw_triples": len(triples),
        "output_entities": adapter_report["output_entities"],
        "output_assertions": adapter_report["output_assertions"],
        "failures": failures,
    })


if __name__ == "__main__":
    main()
