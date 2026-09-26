"""Freeze the RL subgraph and source-only benchmark-generation inputs, read-only."""
from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import json
import random
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "llm-knowledge-graph"
NATIVE = ORIGINAL / "tmp/rl-full-structured-m3-official-c6-20260912"
OUT = ROOT / "outputs/rl-book2-20260923"
sys.path.insert(0, str(ROOT / "src"))
from llm_graph_benchmark.adapters.llm_knowledge_graph import _submission_document
from llm_graph_benchmark.workflow.transport import write, digest
from llm_graph_benchmark.workflow.protocol import METRICS, VERSIONS

SEED = 20260923
BOOK_ID = "sutton-barto-2e-rl-book2-v1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def freeze():
    if (OUT / "source-freeze.json").exists():
        raise ValueError("Already frozen")
    db = NATIVE / "full.db"
    wal = Path(str(db) + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError("Nonempty WAL: obtain a consistent backup before exporting")
    summary = read(NATIVE / "summary.json")
    if not (summary["completed_chunks"] == summary["expected_chunks"] == 324
            and summary["integrity_ok"] and (NATIVE / ".exit").read_text().strip() == "0"):
        raise ValueError("RL construction is incomplete")
    db_hash = sha(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity failure")
    sources = {r["id"]: dict(r) for r in conn.execute("select * from sources")}
    sections = {r["id"]: dict(r) for r in conn.execute("select * from source_sections")}
    doc_id = sources[2]["source_key"]
    units, source_units = {}, defaultdict(list)
    for row in conn.execute("select * from source_passages order by source_id,passage_id"):
        sid, pid = row["source_id"], row["passage_id"]
        text = sources[sid]["content"][row["start_offset"]:row["end_offset"]]
        h = hashlib.sha256(text.encode()).hexdigest()
        assert h == row["content_hash"].removeprefix("sha256:")
        unit = {
            "unit_id": f"S{sid}:{pid}", "modality": "text", "text": text,
            "content_hash": "sha256:" + h,
            "location": {"description": row["location"], "source_id": sid,
                         "native_passage_id": pid, "section_id": row["section_id"],
                         "start_offset": row["start_offset"], "end_offset": row["end_offset"]},
            "metadata": {"context_only": sid != 2, "source_name": sources[sid]["name"]},
        }
        units[(sid, pid)] = unit
        source_units[sid].append(unit)
    native_doc = _submission_document(conn, conn.execute("select * from sources where id=2").fetchone())
    native_ids = {e["metadata"]["native_entity_id"] for e in native_doc["entities"]}
    entity_refs = defaultdict(set)
    for table in ("entity_observations", "evidence"):
        for row in conn.execute(f"select entity_id,source_id,passage_ids from {table} where entity_id is not null"):
            if row["entity_id"] in native_ids:
                entity_refs[row["entity_id"]].update((row["source_id"], str(pid)) for pid in json.loads(row["passage_ids"] or "[]"))
    entity_types = defaultdict(set)
    for row in conn.execute("""
        select o.entity_id,t.canonical_name from entity_observation_types ot
        join entity_observations o on o.id=ot.observation_id
        join entity_type_vocab t on t.id=ot.type_id where o.entity_id is not null
    """):
        if row["entity_id"] in native_ids:
            entity_types[row["entity_id"]].add(row["canonical_name"])
    cross_book = []
    for entity in native_doc["entities"]:
        eid = entity["metadata"]["native_entity_id"]
        refs = sorted(entity_refs[eid])
        if any(sid != 2 for sid, _ in refs):
            cross_book.append(entity["id"])
        entity["evidence"] = [{"unit_id": units[x]["unit_id"]} for x in refs]
        entity["types"] = sorted(entity_types[eid])
        entity["metadata"]["evidence_scope"] = "all declared native observations and evidence; no added source"
    for assertion in native_doc["assertions"]:
        aid = assertion["metadata"]["native_assertion_id"]
        refs = set()
        for row in conn.execute("select source_id,passage_ids from evidence where assertion_id=?", (aid,)):
            refs.update((row["source_id"], str(pid)) for pid in json.loads(row["passage_ids"] or "[]"))
        assertion["evidence"] = [{"unit_id": units[x]["unit_id"]} for x in sorted(refs)]
    # One evaluation document; D2L passages are evidence context only, not sampled
    # graph objects, questions, or fact-probe targets.
    all_units = source_units[2] + source_units[1]
    assert len(source_units[2]) == 2920
    assert len(native_doc["entities"]) == 1354 and len(native_doc["assertions"]) == 2708
    document = {
        "document_id": doc_id, "title": sources[2]["name"], "language": "en",
        "content_hash": "sha256:" + hashlib.sha256(sources[2]["content"].encode()).hexdigest(),
        "uri": sources[2]["uri"], "units": all_units,
        "metadata": {"target_source_id": 2, "support_context_source_ids": [1],
                     "track": "cross-book incremental RL subgraph",
                     "rl_units": 2920, "cross_book_entity_count": len(cross_book)},
    }
    provenance = read(ORIGINAL / "tmp/rl-assessment-20260920/provenance.json")
    usage = {"input_tokens": provenance["usage"]["prompt_tokens"],
             "output_tokens": provenance["usage"]["completion_tokens"],
             "source": str(ORIGINAL / "tmp/rl-assessment-20260920/provenance.json"),
             "note": "All logged successful construction responses including resume and definition synthesis; not all failed attempts or an invoice."}
    submission = {
        "schema_version": "1.0", "benchmark_id": BOOK_ID,
        "system": {"id": "ours-sutton-barto-incremental-m3",
                   "name": "我们的方法（强化学习，跨书增量）", "version": "structured-m3-20260916"},
        "documents": [native_doc], "runtime": {k: usage[k] for k in ("input_tokens", "output_tokens")},
        "metadata": {"native_db_sha256": db_hash, "target_source_id": 2,
                     "cross_book_entity_ids": cross_book, "native_source_scoped_claim_count": 2583},
    }
    benchmark = {
        "schema_version": "1.0", "benchmark_id": BOOK_ID, "title": sources[2]["name"],
        "documents_file": "documents.jsonl", "fact_probes_file": "fact_probes.jsonl",
        "qa_probes_file": "qa_probes.jsonl", "rubric_file": "rubric.json",
    }
    # Select source windows without querying entities, relations, or old scores.
    chapter_sections = defaultdict(list)
    section_units = defaultdict(list)
    for unit in source_units[2]:
        section_units[unit["location"]["section_id"]].append(unit)
    for section in sections.values():
        if section["source_id"] != 2:
            continue
        path = json.loads(section["path_json"])
        match = next((re.match(r"Chapter (\d+):", part) for part in path if re.match(r"Chapter (\d+):", part)), None)
        if not match or re.search(r"Bibliographical|Historical Remarks|Exercises|Summary", section["title"], re.I):
            continue
        ch = int(match[1])
        candidates = [u for u in section_units[section["id"]]
                      if len(u["text"]) >= 650
                      and sum(c.isalpha() for c in u["text"]) / len(u["text"]) >= .65
                      and not re.match(r"\s*(Exercise|Example|Figure)\s", u["text"])]
        if candidates:
            chapter_sections[ch].append((section, candidates))
    jobs = []
    for ch in range(1, 18):
        fact_count = 3 if ch <= 14 else 2
        qa_count = 2 if ch <= 7 else 1
        pool = sorted(chapter_sections[ch], key=lambda pair: pair[0]["id"])
        rng = random.Random(f"{SEED}:source-only:chapter:{ch}")
        chosen = rng.sample(pool, min(fact_count, len(pool)))
        # Few-section chapters may use distinct paragraphs of the same section.
        while len(chosen) < fact_count:
            chosen.append(pool[len(chosen) % len(pool)])
        blocks = []
        used = set()
        for index, (section, candidates) in enumerate(chosen):
            options = [u for u in candidates if u["unit_id"] not in used] or candidates
            center = rng.choice(options)
            used.add(center["unit_id"])
            seq = section_units[section["id"]]
            position = next(i for i, u in enumerate(seq) if u["unit_id"] == center["unit_id"])
            window = seq[max(0, position - 1):position + 2]
            blocks.append({
                "block_id": f"B{index + 1}", "section": section["title"],
                "evidence": [{"id": u["unit_id"], "text": u["text"]} for u in window],
            })
        jobs.append({"id": f"chapter-{ch:02d}", "chapter": ch, "fact_count": fact_count,
                     "qa_count": qa_count, "blocks": blocks})
    assert sum(j["fact_count"] for j in jobs) == 48
    assert sum(j["qa_count"] for j in jobs) == 24
    conn.close()
    assert sha(db) == db_hash
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "documents.jsonl").write_text(json.dumps(document, ensure_ascii=False) + "\n")
    write(OUT / "submission.json", submission)
    write(OUT / "benchmark.json", benchmark)
    write(OUT / "rubric.json", {"labels": ["pass", "fail", "uncertain"],
                               "dimensions": [{"id": k, "question": v, "version": VERSIONS[k]} for k, v in METRICS.items()]})
    write(OUT / "construction-usage.json", usage)
    write(OUT / "probe-jobs.json", jobs)
    write(OUT / "source-freeze.json", {
        "db": str(db), "db_sha256": db_hash, "source_id": 2, "book": sources[2]["name"],
        "pdf": str(ORIGINAL / "data/docs/sutton-barto.pdf"),
        "pdf_sha256": sha(ORIGINAL / "data/docs/sutton-barto.pdf"),
        "native_manifest": str(NATIVE / "manifest.json"), "source_units": 2920,
        "entities": len(native_doc["entities"]), "assertions": len(native_doc["assertions"]),
        "cross_book_entities": len(cross_book), "seed": SEED,
        "facts": 48, "qa": 24, "generation_jobs": 17,
        "generation_input_sha256": digest(jobs),
        "evidence_policy": "All original declared observations/evidence across both books; graph population and source probes are RL only.",
        "source_limitation": "Grounding is to frozen parsed text. Known PDF math-symbol loss is not corrected by this workflow.",
        "files": {name: sha(OUT / name) for name in ["documents.jsonl", "submission.json", "benchmark.json", "rubric.json", "probe-jobs.json", "construction-usage.json"]},
    })
    print(json.dumps({"out": str(OUT), "entities": 1354, "assertions": 2708,
                      "cross_book_entities": len(cross_book), "probe_jobs": len(jobs)}, ensure_ascii=False))


if __name__ == "__main__":
    freeze()


