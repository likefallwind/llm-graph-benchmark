"""Freeze the from-zero RL graph (pipeline-v3) as a workflow submission, read-only.

Same evidence/type policy as studies/rl-workflow-20260923/prepare_book.py. The graph
was built from the RL book alone (source_id=1); its 2,920 passages are byte-identical
to the frozen benchmark's S2 units (same text, offsets and source hash), so passage
P is cited as unit S2:P of studies/rl-source-fontfix-20260926/frozen-benchmark.
"""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "llm-knowledge-graph"
NATIVE = ORIGINAL / "outputs/rl-from-zero-m3-c6-20261004-pipeline-v3"
RUN_DIR = NATIVE / "runs/20261004T150935-0f11945e"
BENCHMARK = ROOT / "studies/rl-source-fontfix-20260926/frozen-benchmark"
OUT = ROOT / "outputs/rl-fromzero-v3-20261008"
sys.path.insert(0, str(ROOT / "src"))
from llm_graph_benchmark.adapters.llm_knowledge_graph import _submission_document
from llm_graph_benchmark.workflow.transport import write

BOOK_ID = "sutton-barto-2e-rl-book2-v1"
SOURCE_ID = 1


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
    db = NATIVE / "graph.db"
    wal = Path(str(db) + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError("Nonempty WAL: obtain a consistent backup before exporting")
    status, check = read(RUN_DIR / "status.json"), read(RUN_DIR / "final-check.json")
    if not (status["stage"] == "complete" and status["exit_code"] == 0
            and check["integrity"]["ok"] and check["quick_check"] == ["ok"]):
        raise ValueError("RL construction is incomplete")
    db_hash = sha(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity failure")
    progress = conn.execute("select status,count(*) n from source_progress group by status").fetchall()
    if {r["status"]: r["n"] for r in progress} != {"done": 324}:
        raise ValueError("Not every chunk is done")
    source = conn.execute("select * from sources where id=?", (SOURCE_ID,)).fetchone()
    assert conn.execute("select count(*) from sources").fetchone()[0] == 1
    frozen = json.loads((BENCHMARK / "documents.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert frozen["document_id"] == source["source_key"]
    # The frozen benchmark repaired glyphs in place; the graph read the pre-repair text.
    assert frozen["metadata"]["previous_content_hash"] == "sha256:" + hashlib.sha256(source["content"].encode()).hexdigest()
    frozen_units = {u["unit_id"]: u for u in frozen["units"]}
    units = {}
    for row in conn.execute("select * from source_passages where source_id=? order by passage_id", (SOURCE_ID,)):
        pid = row["passage_id"]
        text = source["content"][row["start_offset"]:row["end_offset"]]
        assert hashlib.sha256(text.encode()).hexdigest() == row["content_hash"].removeprefix("sha256:")
        loc = frozen_units[f"S2:{pid}"]["location"]
        assert (loc["native_passage_id"], loc["start_offset"], loc["end_offset"]) == (
            pid, row["start_offset"], row["end_offset"])
        units[(SOURCE_ID, str(pid))] = f"S2:{pid}"
    assert len(units) == 2920
    native_doc = _submission_document(conn, source)
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
    for entity in native_doc["entities"]:
        eid = entity["metadata"]["native_entity_id"]
        entity["evidence"] = [{"unit_id": units[x]} for x in sorted(entity_refs[eid])]
        entity["types"] = sorted(entity_types[eid])
        entity["metadata"]["evidence_scope"] = "all declared native observations and evidence; no added source"
    for assertion in native_doc["assertions"]:
        aid = assertion["metadata"]["native_assertion_id"]
        refs = set()
        for row in conn.execute("select source_id,passage_ids from evidence where assertion_id=?", (aid,)):
            refs.update((row["source_id"], str(pid)) for pid in json.loads(row["passage_ids"] or "[]"))
        assertion["evidence"] = [{"unit_id": units[x]} for x in sorted(refs)]
    counts = {"entities": len(native_doc["entities"]), "assertions": len(native_doc["assertions"])}
    conn.close()
    assert sha(db) == db_hash
    usage = {"input_tokens": None, "output_tokens": None,
             "source": str(RUN_DIR),
             "note": "llm-knowledge-graph pipeline-v3 does not log token usage; construction tokens unavailable."}
    submission = {
        "schema_version": "1.0", "benchmark_id": BOOK_ID,
        "system": {"id": "ours-sutton-barto-fromzero-m3-v3",
                   "name": "我们的方法（强化学习，从零构图）", "version": "pipeline-v3-20261004"},
        "documents": [native_doc], "runtime": {"input_tokens": None, "output_tokens": None},
        "metadata": {"native_db_sha256": db_hash, "native_source_id": SOURCE_ID,
                     "unit_mapping": "native passage P -> frozen benchmark unit S2:P (identical text and offsets)"},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "submission.json", submission)
    write(OUT / "construction-usage.json", usage)
    write(OUT / "source-freeze.json", {
        "db": str(db), "db_sha256": db_hash, "source_id": SOURCE_ID, "book": source["name"],
        "native_run": str(RUN_DIR), "native_manifest_sha256": sha(RUN_DIR / "manifest.json"),
        "benchmark": str(BENCHMARK), "source_units": len(units), **counts,
        "evidence_policy": "All declared native observations/evidence; RL book only.",
        "files": {name: sha(OUT / name) for name in ["submission.json", "construction-usage.json"]},
    })
    print(json.dumps({"out": str(OUT), **counts}, ensure_ascii=False))


if __name__ == "__main__":
    freeze()
