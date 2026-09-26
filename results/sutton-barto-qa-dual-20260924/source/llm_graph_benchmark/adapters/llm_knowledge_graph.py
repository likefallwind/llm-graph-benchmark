from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from ..bundle import BenchmarkBundle, SubmissionBundle
from ..io import read_jsonl, write_json, write_jsonl
from ..validation import validate_benchmark, validate_submission


SUPPORTED_SCHEMA_VERSION = "10"
ADAPTER_VERSION = "llm-knowledge-graph-sqlite-1"

DEFAULT_RUBRIC = {
    "labels": ["pass", "fail", "uncertain"],
    "dimensions": [
        {
            "id": "entity_admission",
            "question": (
                "Is this a stable, referable and substantive knowledge entity "
                "grounded in the supplied source evidence?"
            ),
        },
        {
            "id": "entity_typing",
            "question": (
                "Are all submitted entity types semantically compatible with the entity "
                "and its supplied source context?"
            ),
        },
        {
            "id": "entity_definition_grounding",
            "question": (
                "Is the submitted entity definition fully supported by the supplied source "
                "evidence without material unsupported additions?"
            ),
        },
        {
            "id": "assertion_grounding",
            "question": (
                "Does the source support the complete directed assertion, "
                "including polarity and restrictive scope?"
            ),
        },
        {
            "id": "fact_recovery",
            "question": (
                "Can the submitted graph recover this source-side fact without "
                "adding unsupported content?"
            ),
        },
        {
            "id": "alias_identity",
            "question": (
                "Is the submitted alias genuinely coreferential with this entity rather than "
                "a related, broader, narrower, or context-local expression?"
            ),
        },
        {
            "id": "identity_split",
            "question": (
                "Given their definitions and evidence, is it correct to keep these two entities "
                "separate despite a shared surface form?"
            ),
        },
        {
            "id": "book_qa",
            "question": (
                "Do the retrieved graph assertions contain enough correct information to answer "
                "the book question completely?"
            ),
        },
    ],
}


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _database_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _latest_progress(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT source_id,chunk_index,status,error,updated_at FROM (
          SELECT rowid AS progress_rowid,*,
                 ROW_NUMBER() OVER (
                   PARTITION BY source_id,chunk_index
                   ORDER BY updated_at DESC,rowid DESC
                 ) AS position
          FROM source_progress
        ) WHERE position=1 ORDER BY source_id,chunk_index
        """
    ).fetchall()


def _schema_version(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'"
    ).fetchone()
    return str(row[0]) if row else ""


def _integrity_metadata(conn: sqlite3.Connection) -> dict[str, Any]:
    progress = _latest_progress(conn)
    progress_counts: dict[str, int] = defaultdict(int)
    for row in progress:
        progress_counts[str(row["status"])] += 1
    observation = conn.execute(
        """
        WITH latest AS (
          SELECT observation_id,verdict FROM (
            SELECT observation_id,verdict,
                   ROW_NUMBER() OVER (
                     PARTITION BY observation_id ORDER BY id DESC
                   ) AS position
            FROM claim_observation_judgments
          ) WHERE position=1
        )
        SELECT COUNT(*) AS observations,
               SUM(o.subject_entity_id IS NULL OR o.object_entity_id IS NULL)
                 AS pending_endpoint,
               SUM(o.claim_id IS NOT NULL) AS materialized,
               SUM(o.materialization_error<>'') AS blocked,
               SUM(o.claim_id IS NULL AND latest.observation_id IS NULL)
                 AS pending_judgment,
               SUM(latest.verdict='supports') AS supports,
               SUM(latest.verdict='insufficient') AS insufficient,
               SUM(latest.verdict='contradicts') AS contradicts,
               SUM(latest.verdict='supports' AND o.claim_id IS NULL)
                 AS supported_unmaterialized
        FROM claim_observations o
        LEFT JOIN latest ON latest.observation_id=o.id
        """
    ).fetchone()
    entity = conn.execute(
        """
        SELECT COUNT(*) AS observations,
               SUM(entity_id IS NULL) AS unresolved,
               SUM(resolution_outcome='same') AS same_count,
               SUM(resolution_outcome='new') AS new_count,
               SUM(resolution_outcome='uncertain') AS uncertain_count
        FROM entity_observations
        """
    ).fetchone()
    counts = {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in (
            "sources",
            "source_passages",
            "entities",
            "entity_observations",
            "claims",
            "assertions",
            "claim_observations",
            "evidence",
        )
    }
    models = sorted(
        {
            str(row[0])
            for table, column in (
                ("entity_observations", "extraction_model"),
                ("entity_observations", "resolver_model"),
                ("claim_observation_judgments", "validator_model"),
            )
            for row in conn.execute(
                f"SELECT DISTINCT {column} FROM {table} WHERE {column}<>''"
            )
        }
    )
    prompt_versions = sorted(
        {
            str(row[0])
            for table, column in (
                ("entity_observations", "extraction_prompt_version"),
                ("entity_observations", "resolver_prompt_version"),
                ("claim_observation_judgments", "validator_prompt_version"),
            )
            for row in conn.execute(
                f"SELECT DISTINCT {column} FROM {table} WHERE {column}<>''"
            )
        }
    )
    return {
        "quick_check": str(conn.execute("PRAGMA quick_check").fetchone()[0]),
        "schema_version": _schema_version(conn),
        "progress": {
            "total": len(progress),
            "counts": dict(sorted(progress_counts.items())),
            "min_chunk": min((int(row["chunk_index"]) for row in progress), default=None),
            "max_chunk": max((int(row["chunk_index"]) for row in progress), default=None),
        },
        "counts": counts,
        "entity_observations": {
            key: int(entity[key] or 0) for key in entity.keys()
        },
        "claim_observations": {
            key: int(observation[key] or 0) for key in observation.keys()
        },
        "models": models,
        "prompt_versions": prompt_versions,
    }


def _refs(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        quote = str(row["model_quote"] or "")
        location = str(row["location"] or "")
        for raw_unit_id in json.loads(str(row["passage_ids"] or "[]")):
            unit_id = str(raw_unit_id)
            fingerprint = (unit_id, quote, location)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            ref: dict[str, Any] = {"unit_id": unit_id}
            if quote:
                ref["quote"] = quote
            if location:
                ref["location"] = location
            refs.append(ref)
    return refs


def _scoped_passage_ids(
    conn: sqlite3.Connection,
    source: sqlite3.Row,
    progress: Iterable[sqlite3.Row],
    *,
    chunk_chars: int,
    overlap_chars: int,
) -> tuple[set[str], int]:
    if chunk_chars < 200:
        raise ValueError("chunk_chars must be at least 200")
    if overlap_chars < 0 or overlap_chars >= chunk_chars:
        raise ValueError("overlap_chars must satisfy 0 <= overlap < chunk_chars")
    content = str(source["content"])
    rows = conn.execute(
        """
        SELECT passage_id,section_id,start_offset,end_offset
        FROM source_passages WHERE source_id=? ORDER BY passage_id
        """,
        (source["id"],),
    ).fetchall()
    groups: list[list[tuple[str, int]]] = []
    last_section: int | None = None
    for row in rows:
        section_id = int(row["section_id"]) if row["section_id"] is not None else -1
        if not groups or section_id != last_section:
            groups.append([])
        text = content[int(row["start_offset"]):int(row["end_offset"])]
        groups[-1].append((str(row["passage_id"]), len(text)))
        last_section = section_id
    chunks: list[list[str]] = []
    for group in groups:
        start_index = 0
        while start_index < len(group):
            selected: list[str] = []
            rendered_size = 0
            end_index = start_index
            while end_index < len(group):
                passage_id, text_length = group[end_index]
                addition = len(passage_id) + text_length + 4
                if selected and rendered_size + addition > chunk_chars:
                    break
                selected.append(passage_id)
                rendered_size += addition
                end_index += 1
            chunks.append(selected)
            if end_index >= len(group):
                break
            overlap_size = 0
            next_index = end_index
            while next_index > start_index + 1:
                passage_id, text_length = group[next_index - 1]
                addition = len(passage_id) + text_length + 4
                if overlap_size + addition > overlap_chars:
                    break
                overlap_size += addition
                next_index -= 1
            start_index = next_index if next_index < end_index else end_index
    done_indices = {
        int(row["chunk_index"])
        for row in progress
        if int(row["source_id"]) == int(source["id"]) and str(row["status"]) == "done"
    }
    unknown = sorted(index for index in done_indices if index >= len(chunks))
    if unknown:
        raise ValueError(
            f"source_progress contains chunk indices outside reconstructed scope: {unknown[:5]}"
        )
    return {
        passage_id for index in done_indices for passage_id in chunks[index]
    }, len(chunks)


def _document_row(
    conn: sqlite3.Connection,
    source: sqlite3.Row,
    scoped_passage_ids: set[str],
) -> dict[str, Any]:
    content = str(source["content"])
    units = []
    for row in conn.execute(
        """
        SELECT passage_id,content_hash,start_offset,end_offset,location
        FROM source_passages WHERE source_id=? ORDER BY passage_id
        """,
        (source["id"],),
    ):
        if str(row["passage_id"]) not in scoped_passage_ids:
            continue
        start, end = int(row["start_offset"]), int(row["end_offset"])
        units.append(
            {
                "unit_id": str(row["passage_id"]),
                "modality": "text",
                "text": content[start:end],
                "content_hash": str(row["content_hash"]),
                "location": {
                    "description": str(row["location"]),
                    "start_offset": start,
                    "end_offset": end,
                },
            }
        )
    return {
        "document_id": str(source["source_key"]),
        "title": str(source["name"]),
        "language": str(source["language"]),
        "version": str(source["version"]),
        "content_hash": "sha256:" + str(source["content_hash"]),
        "uri": str(source["uri"]),
        "units": units,
    }


def _submission_document(
    conn: sqlite3.Connection, source: sqlite3.Row
) -> dict[str, Any]:
    source_id = int(source["id"])
    entity_rows = conn.execute(
        """
        SELECT DISTINCT e.* FROM entities e
        JOIN evidence v ON v.entity_id=e.id
        WHERE v.source_id=? ORDER BY e.id
        """,
        (source_id,),
    ).fetchall()
    entity_ids = {int(row["id"]) for row in entity_rows}
    aliases: dict[int, list[str]] = defaultdict(list)
    for row in conn.execute(
        "SELECT entity_id,name FROM entity_aliases ORDER BY entity_id,id"
    ):
        if int(row["entity_id"]) in entity_ids:
            aliases[int(row["entity_id"])].append(str(row["name"]))
    types: dict[int, set[str]] = defaultdict(set)
    for row in conn.execute(
        """
        SELECT o.entity_id,t.canonical_name
        FROM entity_observation_types ot
        JOIN entity_observations o ON o.id=ot.observation_id
        JOIN entity_type_vocab t ON t.id=ot.type_id
        WHERE o.source_id=? AND o.entity_id IS NOT NULL
        ORDER BY o.entity_id,t.canonical_name
        """,
        (source_id,),
    ):
        types[int(row["entity_id"])].add(str(row["canonical_name"]))
    entities = []
    for row in entity_rows:
        entity_id = int(row["id"])
        evidence = conn.execute(
            """
            SELECT passage_ids,model_quote,location FROM evidence
            WHERE source_id=? AND entity_id=? ORDER BY id
            """,
            (source_id, entity_id),
        ).fetchall()
        entities.append(
            {
                "id": f"e{entity_id}",
                "name": str(row["canonical_name"]),
                "definition": str(row["definition"]),
                "aliases": aliases[entity_id],
                "types": sorted(types[entity_id]),
                "evidence": _refs(evidence),
                "metadata": {"native_entity_id": entity_id},
            }
        )
    assertion_rows = conn.execute(
        """
        SELECT DISTINCT a.*,c.subject_id,c.object_id,c.relation,
               r.relation_kind
        FROM assertions a
        JOIN claims c ON c.id=a.claim_id
        JOIN relation_types r ON r.id=c.relation_type_id
        JOIN evidence v ON v.assertion_id=a.id
        WHERE v.source_id=? ORDER BY a.id
        """,
        (source_id,),
    ).fetchall()
    assertions = []
    for row in assertion_rows:
        subject_id, object_id = int(row["subject_id"]), int(row["object_id"])
        if subject_id not in entity_ids or object_id not in entity_ids:
            raise ValueError(
                f"assertion {row['id']} references an entity without source evidence"
            )
        evidence = conn.execute(
            """
            SELECT passage_ids,model_quote,location FROM evidence
            WHERE source_id=? AND assertion_id=? ORDER BY id
            """,
            (source_id, row["id"]),
        ).fetchall()
        polarity = str(row["polarity"])
        assertions.append(
            {
                "id": f"a{int(row['id'])}",
                "subject_id": f"e{subject_id}",
                "predicate": str(row["relation"]),
                "object_id": f"e{object_id}",
                "text": str(row["normalized_text"]),
                "scope": str(row["scope_text"]),
                "polarity": "positive" if polarity == "support" else "negative",
                "evidence": _refs(evidence),
                "metadata": {
                    "native_assertion_id": int(row["id"]),
                    "native_claim_id": int(row["claim_id"]),
                    "relation_kind": str(row["relation_kind"]),
                    "scope_is_restrictive": bool(row["scope_is_restrictive"]),
                },
            }
        )
    return {
        "document_id": str(source["source_key"]),
        "entities": entities,
        "assertions": assertions,
    }


def adapt_sqlite(
    db_path: str | Path,
    output_dir: str | Path,
    *,
    benchmark_id: str,
    system_id: str,
    system_name: str,
    system_version: str,
    fact_probes_path: str | Path,
    qa_probes_path: str | Path | None = None,
    source_id: int | None = None,
    allow_incomplete: bool = False,
    filter_probes_to_scope: bool = False,
    chunk_chars: int = 8000,
    overlap_chars: int = 500,
) -> dict[str, Any]:
    database = Path(db_path).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    conn = _connect_read_only(database)
    try:
        schema_version = _schema_version(conn)
        if schema_version != SUPPORTED_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported llm-knowledge-graph schema {schema_version}; "
                f"expected {SUPPORTED_SCHEMA_VERSION}"
            )
        integrity = _integrity_metadata(conn)
        if integrity["quick_check"] != "ok":
            raise ValueError(f"database quick_check failed: {integrity['quick_check']}")
        incomplete = {
            status: count
            for status, count in integrity["progress"]["counts"].items()
            if status != "done" and count
        }
        if incomplete and not allow_incomplete:
            raise ValueError(f"database has incomplete source_progress: {incomplete}")
        if source_id is None:
            sources = conn.execute("SELECT * FROM sources ORDER BY id").fetchall()
            if len(sources) != 1:
                raise ValueError("source_id is required when the database has multiple sources")
            source = sources[0]
        else:
            source = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
            if source is None:
                raise ValueError(f"unknown source_id {source_id}")
        progress = _latest_progress(conn)
        scoped_passage_ids, reconstructed_chunk_count = _scoped_passage_ids(
            conn,
            source,
            progress,
            chunk_chars=chunk_chars,
            overlap_chars=overlap_chars,
        )
        document = _document_row(conn, source, scoped_passage_ids)
        submission_document = _submission_document(conn, source)
    finally:
        conn.close()

    all_probes = read_jsonl(fact_probes_path)
    out_of_scope_probes = [
        probe
        for probe in all_probes
        if any(
            str(unit_id) not in scoped_passage_ids
            for unit_id in probe.get("evidence_unit_ids", [])
        )
    ]
    if out_of_scope_probes and not filter_probes_to_scope:
        probe_ids = [str(probe.get("probe_id", "")) for probe in out_of_scope_probes]
        raise ValueError(
            "fact probes reference passages outside processed scope: "
            f"{probe_ids[:5]}"
        )
    excluded_probe_ids = {
        str(probe.get("probe_id", "")) for probe in out_of_scope_probes
    }
    probes = [
        probe
        for probe in all_probes
        if str(probe.get("probe_id", "")) not in excluded_probe_ids
    ]
    if not probes:
        raise ValueError("no fact probes remain inside processed scope")
    all_qa_probes = read_jsonl(qa_probes_path) if qa_probes_path else []
    out_of_scope_qa_probes = [
        probe
        for probe in all_qa_probes
        if any(
            str(unit_id) not in scoped_passage_ids
            for unit_id in probe.get("evidence_unit_ids", [])
        )
    ]
    if out_of_scope_qa_probes and not filter_probes_to_scope:
        qa_ids = [str(probe.get("qa_id", "")) for probe in out_of_scope_qa_probes]
        raise ValueError(
            "QA probes reference passages outside processed scope: "
            f"{qa_ids[:5]}"
        )
    excluded_qa_ids = {
        str(probe.get("qa_id", "")) for probe in out_of_scope_qa_probes
    }
    qa_probes = [
        probe
        for probe in all_qa_probes
        if str(probe.get("qa_id", "")) not in excluded_qa_ids
    ]
    manifest = {
        "schema_version": "1.0",
        "benchmark_id": benchmark_id,
        "title": f"{document['title']} pilot benchmark",
        "documents_file": "documents.jsonl",
        "fact_probes_file": "fact_probes.jsonl",
        "rubric_file": "rubric.json",
        "metadata": {
            "adapter": ADAPTER_VERSION,
            "source_database_hash": _database_hash(database),
            "source_schema_version": SUPPORTED_SCHEMA_VERSION,
            "evaluation_scope": {
                "processed_chunk_indices": sorted(
                    int(row["chunk_index"])
                    for row in progress
                    if int(row["source_id"]) == int(source["id"])
                    and str(row["status"]) == "done"
                ),
                "chunk_chars": chunk_chars,
                "overlap_chars": overlap_chars,
                "scoped_passage_count": len(scoped_passage_ids),
                "reconstructed_book_chunk_count": reconstructed_chunk_count,
            },
            "fact_probe_scope": {
                "input_count": len(all_probes),
                "included_count": len(probes),
                "excluded_count": len(out_of_scope_probes),
                "excluded_probe_ids": sorted(excluded_probe_ids),
                "filter_enabled": filter_probes_to_scope,
            },
        },
    }
    if qa_probes_path:
        manifest["qa_probes_file"] = "qa_probes.jsonl"
        manifest["metadata"]["qa_probe_scope"] = {
            "input_count": len(all_qa_probes),
            "included_count": len(qa_probes),
            "excluded_count": len(out_of_scope_qa_probes),
            "excluded_qa_ids": sorted(excluded_qa_ids),
            "filter_enabled": filter_probes_to_scope,
        }
    submission = {
        "schema_version": "1.0",
        "benchmark_id": benchmark_id,
        "system": {
            "id": system_id,
            "name": system_name,
            "version": system_version,
            "metadata": {"adapter": ADAPTER_VERSION},
        },
        "documents": [submission_document],
        "runtime": {},
        "metadata": {
            "source_database": str(database),
            "source_database_hash": manifest["metadata"]["source_database_hash"],
            "integrity": integrity,
            "evaluation_scope": manifest["metadata"]["evaluation_scope"],
        },
    }
    write_json(output / "benchmark.json", manifest)
    write_jsonl(output / "documents.jsonl", [document])
    write_jsonl(output / "fact_probes.jsonl", probes)
    if qa_probes_path:
        write_jsonl(output / "qa_probes.jsonl", qa_probes)
    write_json(output / "rubric.json", DEFAULT_RUBRIC)
    write_json(output / "submission.json", submission)

    benchmark_bundle = BenchmarkBundle.load(output / "benchmark.json")
    benchmark_result = validate_benchmark(benchmark_bundle)
    submission_bundle = SubmissionBundle.load(output / "submission.json")
    submission_result = validate_submission(submission_bundle, benchmark_bundle)
    report = {
        "adapter": ADAPTER_VERSION,
        "database": str(database),
        "benchmark_id": benchmark_id,
        "system_id": system_id,
        "benchmark_validation": benchmark_result.as_dict(),
        "submission_validation": submission_result.as_dict(),
        "output_counts": {
            "documents": 1,
            "source_units": len(document["units"]),
            "fact_probes": len(probes),
            "qa_probes": len(qa_probes),
            "entities": len(submission_document["entities"]),
            "assertions": len(submission_document["assertions"]),
        },
        "fact_probe_scope": manifest["metadata"]["fact_probe_scope"],
        "integrity": integrity,
    }
    write_json(output / "adapter-report.json", report)
    if not benchmark_result.ok or not submission_result.ok:
        raise ValueError(f"adapter produced invalid output: {report}")
    return report
