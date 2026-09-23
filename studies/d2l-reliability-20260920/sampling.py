"""Prepare frozen, blinded samples locally; this module never calls an API."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import unicodedata
from typing import Any


CORRECTED = "outputs/d2l-baseline-correction-m3-c6-20260909-172849"
OURS = "outputs/d2l-full1105-vnext-20260826"
SOURCE_CHARACTER_LIMIT = 120_000
FOCUS = {
    "entity": "只检查实体名称所指与边界是否合理、有原文依据。代码对象、事件、示例也可作为实体。此题不评价定义、类型、别名或全局身份归并。",
    "assertion": "检查完整断言的参与者、关系、方向及描述中的全部实质陈述，结合 scope 和 polarity 保留必要条件与否定。允许不同字段布局和宽泛关系；描述中的具体关系正常计入，但正确描述不能替换明确错误的谓词或端点。不要求抽全其他独立事实。",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _read(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def _normal(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def target_fingerprint(kind: str, target: dict[str, Any]) -> str:
    """Normalized exact content, not a claim of semantic-equivalence detection."""
    if kind == "entity":
        values = [target["name"]]
    else:
        values = [target.get(field, "") for field in ("subject", "predicate", "object")]
        values += [target.get("description", target.get("text", "")),
                   target.get("scope", ""), target.get("polarity", "positive")]
    return _digest([kind, *(_normal(value) for value in values)])


def _input_paths(repo: Path) -> dict[str, Path]:
    return {
        "ours": repo / OURS / "submission.json",
        "graphrag": repo / CORRECTED / "graphrag/submission.json",
        "autoschemakg": repo / CORRECTED / "autoschemakg/evaluation/semantic-submission.json",
        "kggen": repo / CORRECTED / "kggen/submission.json",
    }


def _history_paths(repo: Path) -> list[Path]:
    # Deliberately list the supported historical artifact families. Do not scan raw
    # API logs or claim to discover every record a human may ever have inspected.
    patterns = [
        "outputs/d2l-quality-*/*tasks.jsonl", "outputs/d2l-quality-*/*key.jsonl",
        f"{OURS}/evaluation/*tasks.jsonl", f"{OURS}/evaluation/*key.jsonl",
        "outputs/d2l-fullbook-axes-*/*tasks.jsonl",
        "outputs/d2l-fullbook-axes-*/*key.jsonl",
        "outputs/d2l-hybrid-retrieval-20260903/*/*tasks.jsonl",
        "outputs/d2l-hybrid-retrieval-20260903/*/*key.jsonl",
        "outputs/d2l-fullbook-open-baselines-20260826/runs/*/evaluation*/*tasks.jsonl",
        "outputs/d2l-fullbook-open-baselines-20260826/runs/*/evaluation*/*key.jsonl",
        f"{CORRECTED}/*/evaluation/inputs.json",
        f"{CORRECTED}/*/evaluation-smoke/inputs.json",
    ]
    paths = {path for pattern in patterns for path in repo.glob(pattern) if path.is_file()}
    sibling = repo.parent / "llm-knowledge-graph/tmp"
    for pattern in ("d2l-quality-simple-*/tasks.json", "d2l-quality-simple-*/private-key.json",
                    "d2l-quality-v3-*/tasks.json", "d2l-quality-v3-*/private-key.json"):
        paths.update(path for path in sibling.glob(pattern) if path.is_file())
    return sorted(paths)


def _kind(value: str) -> str | None:
    if value.startswith("entity") or value == "alias_identity":
        return "entity"
    if value.startswith("assertion") or value in {"relation", "edge"}:
        return "assertion"
    return None


def collect_exclusions(paths: list[Path], system_ids: dict[str, str]) -> dict[str, Any]:
    ids: set[tuple[str, str, str, str]] = set()
    fingerprints: set[str] = set()
    files = []
    aliases = {**{system: system for system in system_ids},
               **{native: system for system, native in system_ids.items()}}

    def visit(value: Any, inherited_kind: str | None = None) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item, inherited_kind)
            return
        if not isinstance(value, dict):
            return
        kind = _kind(str(value.get("kind", ""))) or inherited_kind
        system = aliases.get(value.get("system", value.get("system_id")))
        if system and kind and value.get("item_id"):
            doc_id = str(value.get("document_id", value.get("doc_id", "*")))
            ids.add((system, kind, doc_id, str(value["item_id"])))
        if all(field in value for field in ("subject", "predicate", "object")) and (
            "text" in value or "description" in value
        ):
            fingerprints.add(target_fingerprint("assertion", value))
        if "name" in value and (kind == "entity" or "definition" in value):
            fingerprints.add(target_fingerprint("entity", value))
        # Candidate assertions inside fact/QA tasks are intentionally included.
        # Source text and submitted evidence are not model outputs to exclude.
        ignored = {"evidence", "source_evidence", "unit", "units", "reference_context",
                   "submitted_sources", "supplied_sources", "metadata", "audit"}
        for key, child in value.items():
            if key not in ignored and isinstance(child, (dict, list)):
                visit(child, kind)

    for path in paths:
        before_ids, before_fingerprints = len(ids), len(fingerprints)
        visit(_read(path))
        files.append({"path": str(path), "sha256": _sha(path),
                      "new_id_keys": len(ids) - before_ids,
                      "new_content_fingerprints": len(fingerprints) - before_fingerprints})
    return {"ids": ids, "fingerprints": fingerprints, "files": files}


def _source_views(evidence: list[dict[str, Any]], units: list[dict[str, Any]]) -> tuple[list, list, dict]:
    positions = {str(unit["unit_id"]): i for i, unit in enumerate(units)}
    cited_ids = {str(ref["unit_id"]) for ref in evidence}
    unresolved = cited_ids - positions.keys()
    if unresolved:
        raise ValueError(f"Unknown native evidence unit IDs: {sorted(unresolved)}")
    cited_positions = sorted(positions[unit_id] for unit_id in cited_ids)
    context_positions = sorted({neighbor for pos in cited_positions
                                for neighbor in range(max(0, pos - 1), min(len(units), pos + 2))})
    def rows(indices: list[int]) -> list[dict[str, str]]:
        return [{"id": str(units[i]["unit_id"]), "text": units[i]["text"]} for i in indices]
    sources, context = rows(cited_positions), rows(context_positions)
    return sources, context, {
        "source_characters": sum(len(row["text"]) for row in sources),
        "reference_units": len(sources),
        "reference_context_characters": sum(len(row["text"]) for row in context),
        "reference_context_units": len(context),
        "native_reference_count": len(evidence),
        "provided_quote_count": sum(bool(ref.get("quote")) for ref in evidence),
        "citation_granularity": "complete deduplicated submitted parent units; quotes not substituted",
    }


def _legacy_coverage(repo: Path, sources: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "note": "Historical frozen 48-probe CaRB covered diagnostic, not new recall, not combined with quality as F1.",
        "systems": {},
    }
    for system in ("graphrag", "autoschemakg", "kggen"):
        path = repo / CORRECTED / system / "evaluation/summary.json"
        if path.exists():
            summary = _read(path)
            sources[str(path)] = _sha(path)
            result["systems"][system] = {"source": str(path), "counts": summary["recall"],
                                          "total": summary["recall_total"]}
    base = repo / "outputs/d2l-fullbook-carb-a-20260827"
    mapping, judgments = base / "pool-map.json", base / "judgments.jsonl"
    if mapping.exists() and judgments.exists():
        systems = _read(mapping)["systems"]
        counts = Counter(row["covered"] for row in _read(judgments)
                         if systems[row["task_id"]] == "llm-knowledge-graph-full1105-vnext")
        for path in (mapping, judgments):
            sources[str(path)] = _sha(path)
        result["systems"]["ours"] = {"source": str(judgments), "counts": dict(counts),
                                      "total": sum(counts.values())}
    return result


def prepare_samples(repo: Path, entities: int = 100, assertions: int = 200,
                    seed: int = 20260920) -> dict[str, Any]:
    if entities < 1 or assertions < 1:
        raise ValueError("Sample sizes must be positive")
    repo = repo.resolve()
    paths = _input_paths(repo)
    submissions = {system: _read(path) for system, path in paths.items()}
    sources = {str(path): _sha(path) for path in paths.values()}
    document_path = repo / OURS / "documents.jsonl"
    documents = _read(document_path)
    sources[str(document_path)] = _sha(document_path)
    units = {str(document["document_id"]): document["units"] for document in documents}
    if len(units) != len(documents):
        raise ValueError("Duplicate source document IDs")
    exclusion = collect_exclusions(_history_paths(repo), {
        system: submission["system"]["id"] for system, submission in submissions.items()})
    sources.update({row["path"]: row["sha256"] for row in exclusion["files"]})
    tasks, key, groups = [], {}, {}
    for system, submission in submissions.items():
        populations: dict[str, list] = {"entity": [], "assertion": []}
        for document in submission["documents"]:
            doc_id = str(document["document_id"])
            if doc_id not in units:
                raise ValueError(f"Missing source document: {doc_id}")
            entity_map = {str(entity["id"]): entity for entity in document["entities"]}
            if len(entity_map) != len(document["entities"]):
                raise ValueError("Duplicate entity IDs")
            for entity in document["entities"]:
                populations["entity"].append((doc_id, entity, {"name": entity["name"]}))
            for assertion in document["assertions"]:
                target = {field: assertion.get(field, "") for field in ("predicate", "scope")}
                target.update(subject=entity_map[str(assertion["subject_id"])]["name"],
                              object=entity_map[str(assertion["object_id"])]["name"],
                              description=assertion.get("text", ""),
                              polarity=assertion.get("polarity", "positive"))
                populations["assertion"].append((doc_id, assertion, target))
        groups[system] = {}
        for kind, sample_size in (("entity", entities), ("assertion", assertions)):
            population = sorted(populations[kind], key=lambda row: (row[0], str(row[1]["id"])))
            item_keys = [(doc_id, str(item["id"])) for doc_id, item, _ in population]
            if len(set(item_keys)) != len(item_keys):
                raise ValueError(f"Duplicate {kind} IDs")
            eligible, excluded_by_id, excluded_by_content, overlap = [], 0, 0, 0
            for doc_id, item, target in population:
                id_seen = any((system, kind, d, str(item["id"])) in exclusion["ids"]
                              for d in (doc_id, "*"))
                content_seen = target_fingerprint(kind, target) in exclusion["fingerprints"]
                excluded_by_id += id_seen
                excluded_by_content += content_seen
                overlap += id_seen and content_seen
                if not id_seen and not content_seen:
                    eligible.append((doc_id, item, target))
            if len(eligible) < sample_size:
                raise ValueError(f"{system}/{kind}: requested {sample_size}, only {len(eligible)} unseen eligible records")
            selected = random.Random(f"{seed}:{system}:{kind}").sample(eligible, sample_size)
            groups[system][kind] = {
                "population": len(population), "excluded": len(population) - len(eligible),
                "excluded_by_id": excluded_by_id, "excluded_by_content": excluded_by_content,
                "excluded_by_both": overlap, "eligible": len(eligible), "selected": len(selected),
                "selected_population_note": "uniform sample of the eligible remainder, not all original output",
            }
            for doc_id, item, target in selected:
                submitted, context, audit = _source_views(item.get("evidence", []), units[doc_id])
                available = kind == "entity" and bool(item.get("definition")) and bool(
                    item.get("metadata", {}).get("definition_available", True))
                audit.update(definition_available=available,
                             definition=item.get("definition") if available else None)
                payload = {"kind": kind, "focus": FOCUS[kind], "target": target,
                           "submitted_sources": submitted, "reference_context": context}
                uid = "q_" + _digest([seed, system, doc_id, str(item["id"]), payload])[:28]
                if uid in key:
                    raise ValueError("Duplicate blinded task ID")
                tasks.append({"id": uid, "payload": payload,
                              "oversized": audit["reference_context_characters"] > SOURCE_CHARACTER_LIMIT})
                key[uid] = {"system": system, "kind": kind, "item_id": str(item["id"]),
                            "doc_id": doc_id, "evidence": item.get("evidence", []), "audit": audit}
    random.Random(seed).shuffle(tasks)
    return {
        "tasks": tasks, "key": key, "sources": sources,
        "sampling": {
            "seed": seed, "groups": groups, "historical_files": exclusion["files"],
            "exclusion_note": "Exclude IDs and normalized exact target content found in the listed historical files, including fact/QA candidates. Does not establish a new book or eliminate all prior exposure.",
            "reference_context": "Submitted parent units plus one adjacent unit on each side; local reference context, not independent or exhaustive source retrieval.",
            "source_character_limit": SOURCE_CHARACTER_LIMIT,
            "oversized_selected": sum(task["oversized"] for task in tasks),
            "replacements": 0,
            "autoschemakg_scope": "Existing semantic-submission.json; excludes event participation/schema edges by the previously frozen track.",
        },
        "legacy_coverage": _legacy_coverage(repo, sources),
    }
