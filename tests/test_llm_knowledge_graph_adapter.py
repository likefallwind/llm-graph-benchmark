from __future__ import annotations

import json
import sqlite3

import pytest

from llm_graph_benchmark.adapters.llm_knowledge_graph import adapt_sqlite
from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
from llm_graph_benchmark.validation import validate_benchmark, validate_submission


def _fixture_db(path, *, schema_version="10", progress_status="done"):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE sources(
          id INTEGER PRIMARY KEY,source_key TEXT,name TEXT,source_type TEXT,uri TEXT,
          version TEXT,content TEXT,content_hash TEXT,language TEXT
        );
        CREATE TABLE source_passages(
          source_id INTEGER,passage_id TEXT,section_id INTEGER,content_hash TEXT,
          start_offset INTEGER,end_offset INTEGER,location TEXT
        );
        CREATE TABLE entities(
          id INTEGER PRIMARY KEY,canonical_name TEXT,normalized_name TEXT,definition TEXT
        );
        CREATE TABLE entity_aliases(id INTEGER PRIMARY KEY,entity_id INTEGER,name TEXT);
        CREATE TABLE entity_observations(
          id INTEGER PRIMARY KEY,source_id INTEGER,entity_id INTEGER,resolution_outcome TEXT,
          extraction_model TEXT,extraction_prompt_version TEXT,resolver_model TEXT,
          resolver_prompt_version TEXT
        );
        CREATE TABLE entity_type_vocab(id INTEGER PRIMARY KEY,canonical_name TEXT);
        CREATE TABLE entity_observation_types(
          id INTEGER PRIMARY KEY,observation_id INTEGER,type_id INTEGER
        );
        CREATE TABLE relation_types(
          id INTEGER PRIMARY KEY,canonical_name TEXT,relation_kind TEXT
        );
        CREATE TABLE claims(
          id INTEGER PRIMARY KEY,subject_id INTEGER,object_id INTEGER,relation TEXT,
          relation_type_id INTEGER
        );
        CREATE TABLE assertions(
          id INTEGER PRIMARY KEY,claim_id INTEGER,normalized_text TEXT,scope_text TEXT,
          scope_is_restrictive INTEGER,polarity TEXT
        );
        CREATE TABLE claim_observations(
          id INTEGER PRIMARY KEY,subject_entity_id INTEGER,object_entity_id INTEGER,
          claim_id INTEGER,assertion_id INTEGER,materialization_error TEXT
        );
        CREATE TABLE claim_observation_judgments(
          id INTEGER PRIMARY KEY,observation_id INTEGER,validator_model TEXT,
          validator_prompt_version TEXT,verdict TEXT
        );
        CREATE TABLE evidence(
          id INTEGER PRIMARY KEY,source_id INTEGER,entity_id INTEGER,claim_id INTEGER,
          assertion_id INTEGER,passage_ids TEXT,model_quote TEXT,location TEXT
        );
        CREATE TABLE source_progress(
          source_id INTEGER,chunk_index INTEGER,status TEXT,result TEXT,error TEXT,
          updated_at TEXT
        );
        """
    )
    content = "Alpha relates to Beta."
    conn.execute("INSERT INTO schema_meta VALUES ('schema_version',?)", (schema_version,))
    conn.execute(
        "INSERT INTO sources VALUES (1,'doc-1','Document','textbook','',"
        "'v1',?,'abc','en')",
        (content,),
    )
    conn.execute(
        "INSERT INTO source_passages VALUES "
        "(1,'u1',NULL,'unit-hash',0,?,'page 1')",
        (len(content),),
    )
    conn.executemany(
        "INSERT INTO entities VALUES (?,?,?,?)",
        [(1, "Alpha", "alpha", "First entity"), (2, "Beta", "beta", "Second entity")],
    )
    conn.execute("INSERT INTO entity_aliases VALUES (1,1,'A')")
    conn.executemany(
        "INSERT INTO entity_observations VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, 1, 1, "new", "extractor", "extract-v1", "resolver", "resolve-v1"),
            (2, 1, 2, "new", "extractor", "extract-v1", "resolver", "resolve-v1"),
        ],
    )
    conn.execute("INSERT INTO entity_type_vocab VALUES (1,'concept')")
    conn.executemany(
        "INSERT INTO entity_observation_types VALUES (?,?,?)",
        [(1, 1, 1), (2, 2, 1)],
    )
    conn.execute("INSERT INTO relation_types VALUES (1,'relates_to','other')")
    conn.execute("INSERT INTO claims VALUES (1,1,2,'relates_to',1)")
    conn.execute(
        "INSERT INTO assertions VALUES (1,1,'Alpha relates to Beta.','',0,'support')"
    )
    conn.execute("INSERT INTO claim_observations VALUES (1,1,2,1,1,'')")
    conn.execute(
        "INSERT INTO claim_observation_judgments VALUES (1,1,'judge','judge-v1','supports')"
    )
    conn.executemany(
        "INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, 1, 1, None, None, '[\"u1\"]', "Alpha", "page 1"),
            (2, 1, 2, None, None, '[\"u1\"]', "Beta", "page 1"),
            (3, 1, None, 1, 1, '[\"u1\"]', "Alpha relates to Beta", "page 1"),
        ],
    )
    conn.execute(
        "INSERT INTO source_progress VALUES (1,0,?,'{}','',"
        "'2026-01-01 00:00:00')",
        (progress_status,),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def adapter_inputs(tmp_path):
    database = tmp_path / "graph.db"
    _fixture_db(database)
    probes = tmp_path / "probes.jsonl"
    probes.write_text(
        json.dumps(
            {
                "probe_id": "p1",
                "document_id": "doc-1",
                "statement": "Alpha relates to Beta.",
                "evidence_unit_ids": ["u1"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return database, probes


def test_adapter_emits_valid_neutral_contract(adapter_inputs, tmp_path):
    database, probes = adapter_inputs
    output = tmp_path / "output"
    report = adapt_sqlite(
        database,
        output,
        benchmark_id="test-v1",
        system_id="system-a",
        system_name="System A",
        system_version="1",
        fact_probes_path=probes,
    )
    benchmark = BenchmarkBundle.load(output / "benchmark.json")
    submission = SubmissionBundle.load(output / "submission.json")
    assert validate_benchmark(benchmark).ok
    assert validate_submission(submission, benchmark).ok
    assert report["output_counts"]["entities"] == 2
    assert report["output_counts"]["assertions"] == 1
    assert report["output_counts"]["source_units"] == 1
    assert benchmark.manifest["metadata"]["evaluation_scope"][
        "processed_chunk_indices"
    ] == [0]
    assert submission.payload["documents"][0]["assertions"][0]["scope"] == ""


def test_adapter_rejects_unsupported_schema(adapter_inputs, tmp_path):
    _, probes = adapter_inputs
    database = tmp_path / "old.db"
    _fixture_db(database, schema_version="9")
    with pytest.raises(ValueError, match="unsupported"):
        adapt_sqlite(
            database,
            tmp_path / "output",
            benchmark_id="test-v1",
            system_id="system-a",
            system_name="System A",
            system_version="1",
            fact_probes_path=probes,
        )


def test_adapter_rejects_incomplete_progress(adapter_inputs, tmp_path):
    _, probes = adapter_inputs
    database = tmp_path / "failed.db"
    _fixture_db(database, progress_status="failed")
    with pytest.raises(ValueError, match="incomplete source_progress"):
        adapt_sqlite(
            database,
            tmp_path / "output",
            benchmark_id="test-v1",
            system_id="system-a",
            system_name="System A",
            system_version="1",
            fact_probes_path=probes,
        )
