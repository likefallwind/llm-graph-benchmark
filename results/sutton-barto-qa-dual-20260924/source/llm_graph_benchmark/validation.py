from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .bundle import BenchmarkBundle, SCHEMA_VERSION, SubmissionBundle


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "issues": [item.as_dict() for item in self.issues]}


def _string(
    issues: list[ValidationIssue], value: Any, path: str, *, required: bool = True
) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if required:
        issues.append(ValidationIssue(path, "required_string", "must be a non-empty string"))
    return ""


def _list(
    issues: list[ValidationIssue], value: Any, path: str
) -> list[Any]:
    if isinstance(value, list):
        return value
    issues.append(ValidationIssue(path, "expected_list", "must be a list"))
    return []


def _unique_ids(
    issues: list[ValidationIssue], items: Iterable[Any], path: str, id_key: str
) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(
                ValidationIssue(f"{path}[{index}]", "expected_object", "must be an object")
            )
            continue
        item_id = _string(issues, item.get(id_key), f"{path}[{index}].{id_key}")
        if item_id in seen:
            issues.append(
                ValidationIssue(
                    f"{path}[{index}].{id_key}", "duplicate_id", f"duplicate ID: {item_id}"
                )
            )
        seen.add(item_id)
    return seen


def validate_benchmark(bundle: BenchmarkBundle) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if bundle.manifest.get("schema_version") != SCHEMA_VERSION:
        issues.append(
            ValidationIssue(
                "schema_version", "unsupported_version", f"must equal {SCHEMA_VERSION}"
            )
        )
    _string(issues, bundle.manifest.get("benchmark_id"), "benchmark_id")
    _string(issues, bundle.manifest.get("title"), "title")
    document_ids = _unique_ids(issues, bundle.documents, "documents", "document_id")
    units: dict[str, set[str]] = {}
    allowed_modalities = {"text", "image", "table", "mixed"}
    for doc_index, document in enumerate(bundle.documents):
        if not isinstance(document, dict):
            continue
        document_id = str(document.get("document_id", ""))
        _string(issues, document.get("content_hash"), f"documents[{doc_index}].content_hash")
        raw_units = _list(issues, document.get("units"), f"documents[{doc_index}].units")
        unit_ids = _unique_ids(
            issues, raw_units, f"documents[{doc_index}].units", "unit_id"
        )
        units[document_id] = unit_ids
        for unit_index, unit in enumerate(raw_units):
            if not isinstance(unit, dict):
                continue
            modality = _string(
                issues,
                unit.get("modality"),
                f"documents[{doc_index}].units[{unit_index}].modality",
            )
            if modality and modality not in allowed_modalities:
                issues.append(
                    ValidationIssue(
                        f"documents[{doc_index}].units[{unit_index}].modality",
                        "invalid_modality",
                        f"must be one of {sorted(allowed_modalities)}",
                    )
                )
            if not any(unit.get(key) for key in ("text", "asset_uri", "content_hash")):
                issues.append(
                    ValidationIssue(
                        f"documents[{doc_index}].units[{unit_index}]",
                        "missing_content",
                        "requires text, asset_uri, or content_hash",
                    )
                )
    probe_ids = _unique_ids(issues, bundle.fact_probes, "fact_probes", "probe_id")
    for index, probe in enumerate(bundle.fact_probes):
        if not isinstance(probe, dict):
            continue
        document_id = _string(
            issues, probe.get("document_id"), f"fact_probes[{index}].document_id"
        )
        _string(issues, probe.get("statement"), f"fact_probes[{index}].statement")
        if document_id and document_id not in document_ids:
            issues.append(
                ValidationIssue(
                    f"fact_probes[{index}].document_id",
                    "unknown_document",
                    document_id,
                )
            )
        refs = _list(
            issues, probe.get("evidence_unit_ids"), f"fact_probes[{index}].evidence_unit_ids"
        )
        for ref_index, unit_id in enumerate(refs):
            if unit_id not in units.get(document_id, set()):
                issues.append(
                    ValidationIssue(
                        f"fact_probes[{index}].evidence_unit_ids[{ref_index}]",
                        "unknown_unit",
                        str(unit_id),
                    )
                )
    if not probe_ids:
        issues.append(
            ValidationIssue("fact_probes", "empty_probes", "requires at least one fact probe")
        )
    _unique_ids(issues, bundle.qa_probes, "qa_probes", "qa_id")
    for index, probe in enumerate(bundle.qa_probes):
        if not isinstance(probe, dict):
            continue
        document_id = _string(
            issues, probe.get("document_id"), f"qa_probes[{index}].document_id"
        )
        _string(issues, probe.get("question"), f"qa_probes[{index}].question")
        _string(
            issues, probe.get("reference_answer"), f"qa_probes[{index}].reference_answer"
        )
        if document_id and document_id not in document_ids:
            issues.append(
                ValidationIssue(f"qa_probes[{index}].document_id", "unknown_document", document_id)
            )
        refs = _list(
            issues, probe.get("evidence_unit_ids"), f"qa_probes[{index}].evidence_unit_ids"
        )
        for ref_index, unit_id in enumerate(refs):
            if unit_id not in units.get(document_id, set()):
                issues.append(
                    ValidationIssue(
                        f"qa_probes[{index}].evidence_unit_ids[{ref_index}]",
                        "unknown_unit",
                        str(unit_id),
                    )
                )
    dimensions = bundle.rubric.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        issues.append(
            ValidationIssue("rubric.dimensions", "empty_dimensions", "requires dimensions")
        )
    else:
        _unique_ids(issues, dimensions, "rubric.dimensions", "id")
    return ValidationResult(tuple(issues))


def _validate_evidence(
    issues: list[ValidationIssue],
    evidence: Any,
    path: str,
    valid_units: set[str],
) -> None:
    refs = _list(issues, evidence, path)
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            issues.append(
                ValidationIssue(f"{path}[{index}]", "expected_object", "must be an object")
            )
            continue
        unit_id = _string(issues, ref.get("unit_id"), f"{path}[{index}].unit_id")
        if unit_id and unit_id not in valid_units:
            issues.append(
                ValidationIssue(f"{path}[{index}].unit_id", "unknown_unit", unit_id)
            )
        bbox = ref.get("bbox")
        if bbox is not None and (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(not isinstance(value, (int, float)) for value in bbox)
        ):
            issues.append(
                ValidationIssue(f"{path}[{index}].bbox", "invalid_bbox", "must be four numbers")
            )


def validate_submission(
    submission: SubmissionBundle, benchmark: BenchmarkBundle
) -> ValidationResult:
    issues: list[ValidationIssue] = []
    payload = submission.payload
    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append(
            ValidationIssue(
                "schema_version", "unsupported_version", f"must equal {SCHEMA_VERSION}"
            )
        )
    if payload.get("benchmark_id") != benchmark.benchmark_id:
        issues.append(
            ValidationIssue(
                "benchmark_id", "benchmark_mismatch", f"must equal {benchmark.benchmark_id}"
            )
        )
    system = payload.get("system")
    if not isinstance(system, dict):
        issues.append(ValidationIssue("system", "expected_object", "must be an object"))
        system = {}
    _string(issues, system.get("id"), "system.id")
    _string(issues, system.get("name"), "system.name")
    _string(issues, system.get("version"), "system.version")
    documents = _list(issues, payload.get("documents"), "documents")
    submission_doc_ids = _unique_ids(issues, documents, "documents", "document_id")
    benchmark_doc_ids = set(benchmark.document_by_id)
    for unknown in sorted(submission_doc_ids - benchmark_doc_ids):
        issues.append(ValidationIssue("documents", "unknown_document", unknown))
    for missing in sorted(benchmark_doc_ids - submission_doc_ids):
        issues.append(ValidationIssue("documents", "missing_document", missing))

    for doc_index, document in enumerate(documents):
        if not isinstance(document, dict):
            continue
        document_id = str(document.get("document_id", ""))
        valid_units = set(benchmark.unit_by_document.get(document_id, {}))
        entities = _list(issues, document.get("entities"), f"documents[{doc_index}].entities")
        assertions = _list(
            issues, document.get("assertions"), f"documents[{doc_index}].assertions"
        )
        entity_ids = _unique_ids(
            issues, entities, f"documents[{doc_index}].entities", "id"
        )
        _unique_ids(issues, assertions, f"documents[{doc_index}].assertions", "id")
        for entity_index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                continue
            base = f"documents[{doc_index}].entities[{entity_index}]"
            _string(issues, entity.get("name"), f"{base}.name")
            metadata = entity.get("metadata", {})
            absent = isinstance(metadata, dict) and metadata.get("definition_available") is False
            if absent and isinstance(entity.get("definition"), str):
                pass  # Explicit native absence permits an empty definition.
            else:
                _string(issues, entity.get("definition"), f"{base}.definition")
            types = entity.get("types", [])
            if not isinstance(types, list) or any(not isinstance(x, str) for x in types):
                issues.append(ValidationIssue(f"{base}.types", "invalid_types", "must be strings"))
            _validate_evidence(issues, entity.get("evidence"), f"{base}.evidence", valid_units)
        for assertion_index, assertion in enumerate(assertions):
            if not isinstance(assertion, dict):
                continue
            base = f"documents[{doc_index}].assertions[{assertion_index}]"
            subject_id = _string(issues, assertion.get("subject_id"), f"{base}.subject_id")
            object_id = _string(issues, assertion.get("object_id"), f"{base}.object_id")
            _string(issues, assertion.get("predicate"), f"{base}.predicate")
            _string(issues, assertion.get("text"), f"{base}.text")
            if subject_id and subject_id not in entity_ids:
                issues.append(
                    ValidationIssue(f"{base}.subject_id", "unknown_entity", subject_id)
                )
            if object_id and object_id not in entity_ids:
                issues.append(ValidationIssue(f"{base}.object_id", "unknown_entity", object_id))
            polarity = assertion.get("polarity", "positive")
            if polarity not in {"positive", "negative"}:
                issues.append(
                    ValidationIssue(
                        f"{base}.polarity", "invalid_polarity", "must be positive or negative"
                    )
                )
            _validate_evidence(
                issues, assertion.get("evidence"), f"{base}.evidence", valid_units
            )
    runtime = payload.get("runtime", {})
    if not isinstance(runtime, dict):
        issues.append(ValidationIssue("runtime", "expected_object", "must be an object"))
    else:
        for key in ("elapsed_seconds", "cost_usd", "input_tokens", "output_tokens"):
            value = runtime.get(key)
            if value is not None and (
                not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0
            ):
                issues.append(
                    ValidationIssue(f"runtime.{key}", "invalid_number", "must be non-negative")
                )
    return ValidationResult(tuple(issues))
