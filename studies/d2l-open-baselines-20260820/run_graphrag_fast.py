from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pandas as pd

from llm_graph_benchmark.adapters.triples import submission_from_triples


UNIT_ID = re.compile(r"\[(P\d{6})\]")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--document-id", default="d2l-zh-official")
    parser.add_argument("--graphrag-repo", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    chunks = read_jsonl(args.corpus)
    project = args.out_dir / "project"
    input_dir = project / "input"
    if project.exists():
        shutil.rmtree(project)
    input_dir.mkdir(parents=True)
    for chunk in chunks:
        (input_dir / f"chunk-{chunk['chunk_index']:04d}.txt").write_text(
            chunk["text"], encoding="utf-8"
        )

    settings = """\
completion_models: {}
embedding_models: {}
input:
  type: text
  file_pattern: '.*\\.txt$$'
  encoding: utf-8
input_storage:
  type: file
  base_dir: input
output_storage:
  type: file
  base_dir: output
reporting:
  type: file
  base_dir: logs
cache:
  type: json
  storage:
    type: file
    base_dir: cache
chunking:
  type: tokens
  size: 100
  overlap: 0
  encoding_model: cl100k_base
extract_graph_nlp:
  normalize_edge_weights: true
  text_analyzer:
    extractor_type: regex_english
workflows:
  - load_input_documents
  - create_base_text_units
  - create_final_documents
  - extract_graph_nlp
  - prune_graph
  - finalize_graph
"""
    (project / "settings.yaml").write_text(settings, encoding="utf-8")

    executable = args.graphrag_repo / ".venv" / "bin" / "graphrag"
    started = time.time()
    command = [
        str(executable), "index", "--root", str(project), "--method", "fast",
        "--skip-validation", "--no-cache",
    ]
    completed = subprocess.run(command, text=True, capture_output=True)
    (args.out_dir / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (args.out_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    output = project / "output"
    entities = pd.read_parquet(output / "entities.parquet")
    relationships = pd.read_parquet(output / "relationships.parquet")
    text_units = pd.read_parquet(output / "text_units.parquet")
    unit_ids_by_text_unit = {
        str(row["id"]): sorted(set(UNIT_ID.findall(str(row["text"]))))
        for row in text_units.to_dict(orient="records")
    }

    def evidence(text_unit_ids: object) -> list[str]:
        return sorted({unit_id for text_unit_id in as_list(text_unit_ids) for unit_id in unit_ids_by_text_unit.get(text_unit_id, [])})

    entity_records = [
        {
            "name": str(row["title"]),
            "definition": str(row.get("description") or ""),
            "types": [str(row.get("type") or "NOUN PHRASE")],
            "evidence_unit_ids": evidence(row.get("text_unit_ids")),
        }
        for row in entities.to_dict(orient="records")
    ]
    triples = [
        {
            "subject": str(row["source"]),
            "predicate": "co_occurs_with",
            "object": str(row["target"]),
            "text": str(row.get("description") or "").strip() or f"{row['source']} 与 {row['target']} 在同一文本窗口中出现。",
            "evidence_unit_ids": evidence(row.get("text_unit_ids")),
        }
        for row in relationships.to_dict(orient="records")
    ]
    commit = subprocess.check_output(["git", "-C", str(args.graphrag_repo), "rev-parse", "HEAD"], text=True).strip()
    submission, adapter_report = submission_from_triples(
        triples,
        entity_records=entity_records,
        benchmark_id=args.benchmark_id,
        document_id=args.document_id,
        system_id="graphrag-fast-default",
        system_name="Microsoft GraphRAG Fast",
        system_version=f"3.1.1+{commit[:12]}",
        runtime={"elapsed_seconds": time.time() - started, "cost_usd": 0.0},
        metadata={
            "upstream_repository": "https://github.com/microsoft/graphrag",
            "upstream_commit": commit,
            "indexing_method": "fast",
            "extractor_type": "regex_english",
            "chunk_size_tokens": 100,
            "chunk_overlap_tokens": 0,
            "scope": "official extraction, pruning, and finalization workflows only",
            "known_applicability_limit": "upstream regex_english extractor is primarily English",
            "relation_semantics": "co-occurrence in an upstream text window",
        },
    )
    write_json(args.out_dir / "submission.json", submission)
    write_json(args.out_dir / "adapter-report.json", adapter_report)
    write_json(args.out_dir / "run-report.json", {
        "chunks": len(chunks), "text_units": len(text_units), "entities": len(entities),
        "relationships": len(relationships), "elapsed_seconds": time.time() - started,
        "command": command, "upstream_commit": commit,
    })


if __name__ == "__main__":
    main()
