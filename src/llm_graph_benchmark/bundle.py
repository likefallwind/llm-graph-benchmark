from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import read_json, read_jsonl


SCHEMA_VERSION = "1.0"


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class BenchmarkBundle:
    path: Path
    manifest: dict[str, Any]
    documents: tuple[dict[str, Any], ...]
    fact_probes: tuple[dict[str, Any], ...]
    rubric: dict[str, Any]

    @property
    def benchmark_id(self) -> str:
        return str(self.manifest.get("benchmark_id", ""))

    @property
    def document_by_id(self) -> dict[str, dict[str, Any]]:
        return {str(item.get("document_id", "")): item for item in self.documents}

    @property
    def unit_by_document(self) -> dict[str, dict[str, dict[str, Any]]]:
        return {
            document_id: {
                str(unit.get("unit_id", "")): unit
                for unit in document.get("units", [])
                if isinstance(unit, dict)
            }
            for document_id, document in self.document_by_id.items()
        }

    @classmethod
    def load(cls, path: str | Path) -> "BenchmarkBundle":
        manifest_path = Path(path).resolve()
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError("benchmark manifest must be a JSON object")
        base = manifest_path.parent

        def relative_file(key: str) -> Path:
            value = manifest.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"benchmark manifest requires {key}")
            candidate = (base / value).resolve()
            if base != candidate and base not in candidate.parents:
                raise ValueError(f"{key} must stay inside the benchmark directory")
            return candidate

        documents = tuple(read_jsonl(relative_file("documents_file")))
        probes_path = relative_file("fact_probes_file")
        fact_probes = tuple(read_jsonl(probes_path))
        rubric = read_json(relative_file("rubric_file"))
        if not isinstance(rubric, dict):
            raise ValueError("rubric must be a JSON object")
        return cls(manifest_path, manifest, documents, fact_probes, rubric)


@dataclass(frozen=True)
class SubmissionBundle:
    path: Path
    payload: dict[str, Any]

    @property
    def system_id(self) -> str:
        system = self.payload.get("system", {})
        return str(system.get("id", "")) if isinstance(system, dict) else ""

    @property
    def submission_hash(self) -> str:
        return canonical_hash(self.payload)

    @classmethod
    def load(cls, path: str | Path) -> "SubmissionBundle":
        submission_path = Path(path).resolve()
        payload = read_json(submission_path)
        if not isinstance(payload, dict):
            raise ValueError("submission must be a JSON object")
        return cls(submission_path, payload)
