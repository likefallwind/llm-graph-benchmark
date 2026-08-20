from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def benchmark_dir(tmp_path: Path) -> Path:
    manifest = {
        "schema_version": "1.0",
        "benchmark_id": "test-v1",
        "title": "Test benchmark",
        "documents_file": "documents.jsonl",
        "fact_probes_file": "fact_probes.jsonl",
        "qa_probes_file": "qa_probes.jsonl",
        "rubric_file": "rubric.json",
    }
    document = {
        "document_id": "doc-1",
        "title": "Document",
        "content_hash": "sha256:test",
        "units": [
            {"unit_id": "u1", "modality": "text", "text": "Alpha relates to beta."}
        ],
    }
    probe = {
        "probe_id": "p1",
        "document_id": "doc-1",
        "statement": "Alpha relates to beta.",
        "evidence_unit_ids": ["u1"],
    }
    qa_probe = {
        "qa_id": "q1",
        "document_id": "doc-1",
        "question": "What relates to beta?",
        "reference_answer": "Alpha relates to beta.",
        "evidence_unit_ids": ["u1"],
    }
    rubric = {"dimensions": [{"id": "entity_admission", "question": "Valid?"}]}
    (tmp_path / "benchmark.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "documents.jsonl").write_text(json.dumps(document) + "\n", encoding="utf-8")
    (tmp_path / "fact_probes.jsonl").write_text(json.dumps(probe) + "\n", encoding="utf-8")
    (tmp_path / "qa_probes.jsonl").write_text(
        json.dumps(qa_probe) + "\n", encoding="utf-8"
    )
    (tmp_path / "rubric.json").write_text(json.dumps(rubric), encoding="utf-8")
    return tmp_path


@pytest.fixture
def submission_payload() -> dict:
    return {
        "schema_version": "1.0",
        "benchmark_id": "test-v1",
        "system": {"id": "system-a", "name": "System A", "version": "1"},
        "documents": [
            {
                "document_id": "doc-1",
                "entities": [
                    {
                        "id": "e1",
                        "name": "Alpha",
                        "definition": "The first entity.",
                        "types": ["concept"],
                        "evidence": [{"unit_id": "u1"}],
                    },
                    {
                        "id": "e2",
                        "name": "Beta",
                        "definition": "The second entity.",
                        "types": ["concept"],
                        "evidence": [{"unit_id": "u1"}],
                    },
                ],
                "assertions": [
                    {
                        "id": "a1",
                        "subject_id": "e1",
                        "predicate": "relates_to",
                        "object_id": "e2",
                        "text": "Alpha relates to beta.",
                        "polarity": "positive",
                        "evidence": [{"unit_id": "u1"}],
                    }
                ],
            }
        ],
        "runtime": {"elapsed_seconds": 1, "cost_usd": 0.1},
    }


@pytest.fixture
def submission_path(tmp_path: Path, submission_payload: dict) -> Path:
    path = tmp_path / "submission.json"
    path.write_text(json.dumps(submission_payload), encoding="utf-8")
    return path
