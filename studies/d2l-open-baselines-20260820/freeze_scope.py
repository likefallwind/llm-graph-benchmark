from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--benchmark-documents", type=Path, required=True)
    parser.add_argument("--llmkg-repo", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--chunk-chars", type=int, default=8000)
    parser.add_argument("--overlap-chars", type=int, default=500)
    args = parser.parse_args()

    sys.path.insert(0, str(args.llmkg_repo.resolve()))
    from kg.sources import chunk_text

    connection = sqlite3.connect(f"file:{args.source_db.resolve()}?mode=ro", uri=True)
    try:
        source_key, content, content_hash = connection.execute(
            "SELECT source_key,content,content_hash FROM sources ORDER BY id LIMIT 1"
        ).fetchone()
        processed = [
            int(row[0])
            for row in connection.execute(
                "SELECT DISTINCT chunk_index FROM source_progress WHERE status='done' ORDER BY chunk_index"
            )
        ]
    finally:
        connection.close()

    benchmark_document = json.loads(args.benchmark_documents.read_text(encoding="utf-8").splitlines()[0])
    benchmark_units = {unit["unit_id"]: unit for unit in benchmark_document["units"]}
    all_chunks = chunk_text(content, max_chars=args.chunk_chars, overlap_chars=args.overlap_chars)
    selected = [all_chunks[index] for index in processed]
    scoped_ids = sorted({passage.passage_id for chunk in selected for passage in chunk.passages})
    if set(scoped_ids) != set(benchmark_units):
        raise ValueError(
            f"scope mismatch: chunks_only={set(scoped_ids) - set(benchmark_units)}, "
            f"benchmark_only={set(benchmark_units) - set(scoped_ids)}"
        )
    for chunk in selected:
        for passage in chunk.passages:
            if benchmark_units[passage.passage_id].get("text") != passage.text:
                raise ValueError(f"text mismatch for {passage.passage_id}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = args.out_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in selected:
            row = {
                "chunk_index": chunk.index,
                "content_hash": chunk.content_hash,
                "location": chunk.location,
                "section_path": list(chunk.section_path),
                "unit_ids": [passage.passage_id for passage in chunk.passages],
                "text": chunk.text,
            }
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    commit = subprocess.check_output(
        ["git", "-C", str(args.llmkg_repo), "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = {
        "schema_version": "1.0",
        "source_key": source_key,
        "source_content_hash": "sha256:" + content_hash,
        "source_database_hash": sha256(args.source_db),
        "benchmark_documents_hash": sha256(args.benchmark_documents),
        "llm_knowledge_graph_commit": commit,
        "chunk_chars": args.chunk_chars,
        "overlap_chars": args.overlap_chars,
        "processed_chunk_indices": processed,
        "chunk_count": len(selected),
        "unique_source_unit_count": len(scoped_ids),
        "chunks_file": chunks_path.name,
        "chunks_hash": sha256(chunks_path),
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
