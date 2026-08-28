"""Run AutoSchemaKG's schema-induction stage on a finished extraction run.

The extraction runner processes one frozen chunk per upstream invocation so that
every chunk keeps its own resumable artifact. Conceptualization instead needs the
whole corpus in one upstream output directory, so this script consolidates the
per-chunk rows first and then drives the official pipeline.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from openai import OpenAI

from atlas_rag.kg_construction.triple_config import ProcessingConfig
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.llm_generator import GenerationConfig, LLMGenerator


def load_api_key(env_file: Path | None, key_name: str) -> str | None:
    if not env_file or not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            name, candidate = stripped.split("=", 1)
            if name.strip() == key_name:
                return candidate.strip().strip("'\"").split(",", 1)[0].strip() or None
    return None


def consolidate(run_dir: Path, stage_dir: Path, pattern: str) -> int:
    """Merge every per-chunk upstream row into one JSONL the pipeline can scan."""
    target_dir = stage_dir / "kg_extraction"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{pattern}_consolidated.json"
    rows = 0
    with target.open("w", encoding="utf-8") as handle:
        for chunk_path in sorted((run_dir / "chunks").glob("chunk-*.json")):
            record = json.loads(chunk_path.read_text(encoding="utf-8"))
            if record.get("status") != "done":
                continue
            handle.write(json.dumps(record["result"], ensure_ascii=False) + "\n")
            rows += 1
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--pattern", default="d2lfull1105")
    parser.add_argument("--model", default="MiniMax-M3")
    parser.add_argument("--base-url", default="https://api.minimaxi.com/v1")
    parser.add_argument("--api-key-env", default="MINIMAX_API_KEY")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--api-key-name", default="GATEWAY_KEYS")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--batch-size-concept", type=int, default=64)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--stop-after-csv", action="store_true",
                        help="Consolidate and build the triple CSVs, then stop before any LLM call.")
    args = parser.parse_args()

    stage_dir = args.run_dir / "concept-stage"
    rows = consolidate(args.run_dir, stage_dir, args.pattern)
    print(f"consolidated {rows} chunk rows into {stage_dir}/kg_extraction", flush=True)

    import os
    api_key = os.environ.get(args.api_key_env or "", "") or load_api_key(args.api_key_file, args.api_key_name)
    if not api_key:
        raise SystemExit("no API key available")
    client = OpenAI(base_url=args.base_url, api_key=api_key)
    generator = LLMGenerator(
        client,
        model_name=args.model,
        backend="custom",
        max_workers=args.max_workers,
        default_config=GenerationConfig(
            max_tokens=args.max_tokens,
            temperature=0.0,
            do_sample=False,
            seed=20260828,
        ),
    )

    config = ProcessingConfig(
        model_path=args.model,
        data_directory=str(stage_dir / "kg_extraction"),
        filename_pattern=args.pattern,
        output_directory=str(stage_dir),
        batch_size_concept=args.batch_size_concept,
        max_new_tokens=args.max_tokens,
        max_workers=args.max_workers,
        record=True,
        include_concept=True,
    )
    extractor = KnowledgeGraphExtractor(model=generator, config=config)

    started = time.time()
    extractor.convert_json_to_csv()
    csv_seconds = time.time() - started
    missing = stage_dir / "triples_csv" / f"missing_concepts_{args.pattern}_from_json.csv"
    missing_rows = sum(1 for _ in missing.open(encoding="utf-8")) - 1 if missing.exists() else -1
    print(f"convert_json_to_csv done in {csv_seconds:.0f}s; missing concepts to generate: {missing_rows}", flush=True)

    if args.stop_after_csv:
        return

    concept_started = time.time()
    extractor.generate_concept_csv_temp(language=args.language)
    extractor.create_concept_csv()
    print(f"conceptualization done in {time.time() - concept_started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
