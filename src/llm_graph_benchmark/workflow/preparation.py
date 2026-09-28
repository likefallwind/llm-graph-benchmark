"""Prepare a frozen, source-grounded evaluation without any API calls."""
from collections import Counter
from functools import cached_property
import hashlib
import json
from pathlib import Path
import random
import time

from ..bundle import BenchmarkBundle, SubmissionBundle, canonical_hash
from ..identity import create_identity_tasks
from ..metrics import submission_metrics
from ..retrieval import retrieve_fact_probes
from ..validation import validate_benchmark, validate_submission
from . import ledger, protocol
from .transport import write

DEFAULT_SAMPLES = {"entities": 100, "assertions": 200, "aliases": 30}
MAX_INPUT_BYTES = 350_000


class FrozenSubmission(SubmissionBundle):
    # A loaded workflow submission is never mutated. Avoid hashing an entire
    # large graph once per sampled entity in the legacy task builders.
    @cached_property
    def submission_hash(self):
        return canonical_hash(self.payload)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes():
    root = Path(__file__).resolve().parent.parent
    names = ["bundle.py", "io.py", "identity.py", "metrics.py", "qa.py",
             "retrieval.py", "validation.py"]
    files = [root / name for name in names] + sorted((root / "workflow").glob("*.py"))
    return {str(p.relative_to(root)): sha(p) for p in files}


def present(entity, field):
    if entity.get("metadata", {}).get(field + "_available") is False:
        return False
    value = entity.get(field)
    return bool(value.strip()) if isinstance(value, str) else bool(value)


def select(items, limit, seed):
    ordered = sorted(items, key=lambda x: str(x["id"]))
    return sorted(random.Random(seed).sample(ordered, min(limit, len(ordered))),
                  key=lambda x: str(x["id"]))


def _sources(item, units):
    return [{"id": uid, "text": units[uid]["text"]}
            for uid in dict.fromkeys(str(ref["unit_id"]) for ref in item.get("evidence", []))]


def _neighbors(item, ordered):
    positions = {u["unit_id"]: i for i, u in enumerate(ordered)}
    chosen = set()
    for ref in item.get("evidence", []):
        pos = positions[str(ref["unit_id"])]
        chosen.update(range(max(0, pos - 1), min(len(ordered), pos + 2)))
    return [{"id": ordered[i]["unit_id"], "text": ordered[i]["text"]} for i in sorted(chosen)]


def _target(assertion, entities):
    return {
        "subject": entities[str(assertion["subject_id"])]["name"],
        "predicate": assertion["predicate"],
        "object": entities[str(assertion["object_id"])]["name"],
        "description": assertion["text"], "scope": assertion.get("scope", ""),
        "polarity": assertion.get("polarity", "positive"),
    }


def _candidate(assertion, entities):
    target = _target(assertion, entities)
    target["text"] = target.pop("description")
    return target


def _validate_config(config):
    allowed = {"benchmark", "submissions", "seed", "samples", "workers"}
    if set(config) - allowed:
        raise ValueError("Unknown workflow config keys: " + str(sorted(set(config) - allowed)))
    if not isinstance(config.get("benchmark"), str) or not config["benchmark"]:
        raise ValueError("benchmark path is required")
    if not isinstance(config.get("submissions"), list) or not config["submissions"]:
        raise ValueError("submissions must be a nonempty list")
    workers = config.get("workers", 6)
    if type(workers) is not int or not 1 <= workers <= 6:
        raise ValueError("workers must be an integer in 1..6")
    if type(config.get("seed", 0)) is not int:
        raise ValueError("seed must be an integer")
    sampling = config.get("samples", {})
    if isinstance(sampling, dict) and "splits" in sampling:
        raise ValueError("samples.splits was retired with identity_split; "
                         "semantic duplicates reuse the entity sample in a separate stage")
    if not isinstance(sampling, dict) or set(sampling) - set(DEFAULT_SAMPLES):
        raise ValueError("Unknown sampling settings")
    samples = {**DEFAULT_SAMPLES, **sampling}
    if any(type(v) is not int or v < 1 for v in samples.values()):
        raise ValueError("All sample sizes must be positive integers")
    return samples


def _subset(quality, full):
    if quality.system_id != full.system_id:
        raise ValueError("Quality and structure system IDs must match")
    docs = {d["document_id"]: d for d in full.payload["documents"]}
    for doc in quality.payload["documents"]:
        other = docs[doc["document_id"]]
        for kind in ("entities", "assertions"):
            by_id = {x["id"]: x for x in other[kind]}
            for item in doc[kind]:
                if item["id"] not in by_id or item != by_id[item["id"]]:
                    raise ValueError("Quality input must be an unchanged subset of the structure input")


def structure_metrics(submission, quality, usage):
    raw = submission_metrics(submission)
    summary = raw["summary"]
    entities = [e for d in submission.payload["documents"] for e in d["entities"]]
    n = len(entities)
    field_counts = {field: sum(present(e, field) for e in entities)
                    for field in ("types", "definition", "aliases")}
    largest = max((d["largest_component_count"]
                   for d in raw["documents"]), default=0)
    tokens = {}
    for field in ("input_tokens", "output_tokens"):
        value = usage.get(field)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Construction token counts must be nonnegative integers or null")
        tokens[field + "_million"] = value / 1_000_000 if value is not None else None
    total = sum(usage[f] for f in ("input_tokens", "output_tokens")) if all(
        usage.get(f) is not None for f in ("input_tokens", "output_tokens")) else None
    tokens["total_tokens_million"] = total / 1_000_000 if total is not None else None
    return {
        "entity_count": n, "assertion_count": summary["assertion_count"],
        "quality_assertion_count": sum(len(d["assertions"]) for d in quality.payload["documents"]),
        "entity_citation_presence": summary["entity_evidence_coverage"] if n else None,
        "assertion_citation_presence": summary["assertion_evidence_coverage"] if summary["assertion_count"] else None,
        "isolated_entity_rate": summary["isolated_entity_rate"] if n else None,
        "largest_component_ratio": largest / n if n else None,
        "alias_count": summary["identity"]["alias_count"],
        "field_counts": field_counts, "construction": tokens,
        "construction_source": usage.get("source", "submission.runtime (construction only)"),
        "documents": [{k: d[k] for k in ("document_id", "entity_count", "assertion_count",
                                       "largest_component_ratio", "isolated_entity_count")}
                      for d in raw["documents"]],
    }


def prepare(config_path, run):
    config_path, run = Path(config_path).resolve(), Path(run).resolve()
    if run.exists():
        raise ValueError("Use a new run directory; use run/status/report to resume an existing run")
    config = read(config_path)
    samples = _validate_config(config)
    base, seed = config_path.parent, config.get("seed", 0)
    resolve = lambda value: (base / value).resolve()
    benchmark = BenchmarkBundle.load(resolve(config["benchmark"]))
    validation = validate_benchmark(benchmark)
    if not validation.ok:
        raise ValueError(f"Invalid benchmark: {validation.as_dict()}")
    for document in benchmark.documents:
        if any(not isinstance(unit.get("text"), str) for unit in document["units"]):
            raise ValueError("This workflow requires source text for every unit; provide OCR/transcription for non-text units")
    inputs = {str(config_path): sha(config_path), str(benchmark.path): sha(benchmark.path)}
    for key in ("documents_file", "fact_probes_file", "qa_probes_file", "rubric_file"):
        if key in benchmark.manifest:
            path = benchmark.path.parent / benchmark.manifest[key]
            inputs[str(path.resolve())] = sha(path)
    tasks, key, sampling, structures, systems = [], {}, {}, {}, {}
    unit_maps, source_docs = benchmark.unit_by_document, benchmark.document_by_id

    def add(sub, did, item_id, metric, payload):
        identity = [protocol.VERSION, protocol.VERSIONS[metric], sub.submission_hash,
                    seed, did, item_id, metric]
        tid = "t_" + canonical_hash(identity).split(":")[1][:24]
        if tid in key:
            raise ValueError("Duplicate task identity")
        task = {"id": tid, "metric": metric, "payload": payload, "max_tokens": 8192}
        task["messages"] = protocol.messages(task)
        task["input_bytes"] = len(json.dumps(task["messages"], ensure_ascii=False).encode())
        task["oversized"] = task["input_bytes"] > MAX_INPUT_BYTES
        tasks.append(task)
        key[tid] = {"system": sub.system_id, "document_id": did, "item_id": item_id,
                    "metric": metric, "submission_hash": sub.submission_hash}

    for entry in config["submissions"]:
        if isinstance(entry, str):
            entry = {"path": entry}
        if not isinstance(entry, dict) or set(entry) - {"path", "structure_path", "name", "scope_note", "construction_usage"}:
            raise ValueError("Invalid submission entry")
        sub = FrozenSubmission.load(resolve(entry["path"]))
        result = validate_submission(sub, benchmark)
        if not result.ok:
            raise ValueError(f"Invalid submission: {result.as_dict()}")
        if sub.system_id in systems:
            raise ValueError("Duplicate system_id: " + sub.system_id)
        systems[sub.system_id] = {"name": entry.get("name", sub.system_id),
                                  "scope_note": entry.get("scope_note", "complete submission"),
                                  "submission_hash": sub.submission_hash}
        inputs[str(sub.path)] = sha(sub.path)
        full = sub
        if entry.get("structure_path"):
            if not entry.get("scope_note"):
                raise ValueError("A separate structure_path requires a scope_note")
            full = FrozenSubmission.load(resolve(entry["structure_path"]))
            result = validate_submission(full, benchmark)
            if not result.ok:
                raise ValueError(f"Invalid structure submission: {result.as_dict()}")
            _subset(sub, full)
            inputs[str(full.path)] = sha(full.path)
        usage = full.payload.get("runtime", {})
        if entry.get("construction_usage"):
            upath = resolve(entry["construction_usage"])
            usage = read(upath)
            if not usage.get("source"):
                raise ValueError("construction_usage requires an auditable source")
            inputs[str(upath)] = sha(upath)
        structures[sub.system_id] = structure_metrics(full, sub, usage)
        docs = {d["document_id"]: d for d in sub.payload["documents"]}
        sampling[sub.system_id] = []
        for did, doc in sorted(docs.items()):
            entities = {str(e["id"]): e for e in doc["entities"]}
            selected = select(doc["entities"], samples["entities"], f"{seed}:{sub.submission_hash}:{did}:entities")
            assertions = select(doc["assertions"], samples["assertions"], f"{seed}:{sub.submission_hash}:{did}:assertions")
            excluded = []
            for entity in selected:
                eid = str(entity["id"])
                sources = _sources(entity, unit_maps[did])
                referent = {"kind": "entity", "target": {"name": entity["name"]},
                            "submitted_sources": sources,
                            "reference_context": _neighbors(entity, source_docs[did]["units"])}
                for metric in ("entity_correctness", "entity_evidence"):
                    add(sub, did, eid, metric, referent)
                for field, metric in (("types", "entity_typing"), ("definition", "entity_description")):
                    if not present(entity, field):
                        excluded.append({"entity_id": eid, "metric": metric, "reason": "native field absent"})
                        continue
                    target = {"name": entity["name"]}
                    if field == "types":
                        target["types"] = [{"type_id": f"type-{i}", "type_text": text}
                                           for i, text in enumerate(entity["types"])]
                    else:
                        target["description"] = entity["definition"]
                    add(sub, did, eid, metric, {"target": target, "evidence": sources})
            for assertion in assertions:
                target = _target(assertion, entities)
                context = ledger.section_context(source_docs[did]["units"],
                    [str(r["unit_id"]) for r in assertion.get("evidence", [])])
                ec = {role: {k: entities[str(assertion[role + "_id"])].get(k, [] if k == "aliases" else "")
                             for k in ("name", "aliases", "definition")} for role in ("subject", "object")}
                add(sub, did, str(assertion["id"]), "assertion_correctness",
                    {"target": target, "segments": ledger.segments(target),
                     "entity_context": ec, "reference_context": context})
                add(sub, did, str(assertion["id"]), "relation_granularity", {"target": target})
            sampling[sub.system_id].append({
                "document_id": did, "population_entities": len(entities),
                "population_assertions": len(doc["assertions"]),
                "entity_ids": [str(e["id"]) for e in selected],
                "assertion_ids": [str(a["id"]) for a in assertions], "excluded_fields": excluded,
            })
        # The historical identity task ID omits document_id. Build one document
        # at a time, then assign the workflow ID with explicit document scope.
        # Surface-collision split pairs are retired; only aliases are built here.
        for doc in docs.values():
            scoped = FrozenSubmission(sub.path, {**sub.payload, "documents": [doc]})
            identity = create_identity_tasks(benchmark, [scoped], aliases_per_document=samples["aliases"],
                                             collision_pairs_per_document=0, seed=seed)
            ikeys = {k["task_id"]: k for k in identity.key}
            for task in identity.tasks:
                k = ikeys[task["task_id"]]
                add(sub, k["document_id"], k["item_id"], task["kind"], task)
        fact_rows = retrieve_fact_probes(benchmark, [sub])
        for row, probe in zip(fact_rows, sorted(benchmark.fact_probes, key=lambda x: str(x["probe_id"]))):
            did = probe["document_id"]
            doc = docs[did]
            entities = {str(e["id"]): e for e in doc["entities"]}
            assertions = {str(a["id"]): a for a in doc["assertions"]}
            evidence = [{"id": f"C{i + 1}", "assertion": _candidate(assertions[aid], entities)}
                        for i, aid in enumerate(row["assertion_ids"])]
            add(sub, did, str(probe["probe_id"]), "fact_recovery",
                {"target": {"source_fact": probe["statement"]}, "evidence": evidence})
        # Retrieval IDs are frozen separately for traceability, never sent as source evidence.
        systems[sub.system_id]["retrieval"] = {"facts": fact_rows}
    tasks.sort(key=lambda x: x["id"])
    random.Random(seed).shuffle(tasks)
    run.mkdir(parents=True)
    snapshot = {**config, "samples": samples, "workers": config.get("workers", 6), "seed": seed}
    for name, value in (
        ("config.json", snapshot), ("tasks.json", tasks), ("private-key.json", key),
        ("sampling.json", sampling), ("structure.json", structures),
        ("systems.json", systems), ("prompts.json", protocol.prompt_snapshot()),
    ):
        write(run / name, value)
    manifest = {
        "protocol": protocol.VERSION, "metric_versions": protocol.VERSIONS,
        "model": "MiniMax-M3", "workers": snapshot["workers"], "temperature": 0,
        "created_at": time.time(), "input_hashes": inputs, "code_hashes": code_hashes(),
        "benchmark_hash": canonical_hash({"documents": benchmark.documents,
                                         "facts": benchmark.fact_probes, "qa": benchmark.qa_probes,
                                         "rubric": benchmark.rubric, "manifest": benchmark.manifest}),
        "frozen_files": {p.name: sha(p) for p in run.iterdir() if p.is_file()},
        "counts": dict(Counter(t["metric"] for t in tasks)), "total_tasks": len(tasks),
        "planned_calls_without_retries": len(tasks) + sum(t["metric"] == "assertion_correctness" for t in tasks),
        "oversized": sum(t["oversized"] for t in tasks),
        "max_attempts_per_request": 3, "max_input_bytes": MAX_INPUT_BYTES,
        "retriever": {"id": "char-ngram-bm25-v1", "top_k": 10, "k1": 1.2, "b": 0.75},
    }
    write(run / "manifest.json", manifest)
    from .reporting import report
    report(run)
    return {"run": str(run), "status": "prepared", "tasks": len(tasks),
            "planned_calls_without_retries": manifest["planned_calls_without_retries"],
            "oversized": manifest["oversized"]}


def verify(run):
    run = Path(run)
    manifest = read(run / "manifest.json")
    if manifest["protocol"] != protocol.VERSION or manifest["code_hashes"] != code_hashes():
        raise ValueError("Workflow code/protocol changed; restore the frozen version or prepare a new run")
    for name, digest in manifest["frozen_files"].items():
        if sha(run / name) != digest:
            raise ValueError("Frozen input changed: " + name)
    return manifest
