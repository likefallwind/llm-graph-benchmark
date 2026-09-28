"""Semantic duplicates: is one object split into several nodes, whatever their spelling?

A stage derived from a completed parent run. It reuses the parent's frozen entity
sample. Candidate generation happens before any model call and is frozen as input
files: evaluator-written equivalent names, a deterministic lexical search over
entity names and aliases only, and a lenient evaluator screening. Only the final
pairwise verdict goes to the MiniMax-M3 judge, which sees each entity's own
submitted citations unchanged.
"""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import time

from ..bundle import BenchmarkBundle, canonical_hash
from ..retrieval import _tokens
from . import identity_judge, protocol
from .preparation import FrozenSubmission, MAX_INPUT_BYTES, code_hashes, present, read, sha
from .transport import write

VERSION = "semantic-duplicate-v1"
# Per-entity cited source bytes. Two eligible entities always fit one request.
SOURCE_LIMIT = 170 * 1024
CANDIDATES = 30
K1, B = 1.2, 0.75



def _key(prefix, *parts):
    return prefix + hashlib.sha256("\0".join(parts).encode()).hexdigest()[:12]


def _source_rows(entity, units):
    return identity_judge.sources([{"unit_id": str(ref["unit_id"]), "text": units[str(ref["unit_id"])]["text"]}
                                   for ref in entity.get("evidence", [])])


def source_bytes(entity, units):
    return sum(len(row["text"].encode()) for row in _source_rows(entity, units))


def _parent_config(parent, manifest):
    for path in manifest["input_hashes"]:
        if not path.endswith(".json") or not Path(path).exists():
            continue
        value = read(path)
        if isinstance(value, dict) and "submissions" in value and "benchmark" in value:
            if sha(path) != manifest["input_hashes"][path]:
                raise ValueError("Parent workflow config changed: " + path)
            return Path(path)
    raise ValueError("Parent workflow config not found in manifest inputs")


def load_parent(parent):
    """Reload the parent's frozen benchmark, submissions and entity sample, verifying hashes."""
    parent = Path(parent).resolve()
    manifest = read(parent / "manifest.json")
    for name, digest in manifest["frozen_files"].items():
        if sha(parent / name) != digest:
            raise ValueError("Parent frozen input changed: " + name)
    config_path = _parent_config(parent, manifest)
    config = read(config_path)
    resolve = lambda value: (config_path.parent / value).resolve()
    benchmark = BenchmarkBundle.load(resolve(config["benchmark"]))
    digest = canonical_hash({"documents": benchmark.documents, "facts": benchmark.fact_probes,
                             "qa": benchmark.qa_probes, "rubric": benchmark.rubric,
                             "manifest": benchmark.manifest})
    if digest != manifest["benchmark_hash"]:
        raise ValueError("Parent benchmark changed")
    systems, sampling = read(parent / "systems.json"), read(parent / "sampling.json")
    submissions = {}
    for entry in config["submissions"]:
        path = resolve(entry if isinstance(entry, str) else entry["path"])
        sub = FrozenSubmission.load(path)
        if systems.get(sub.system_id, {}).get("submission_hash") != sub.submission_hash:
            raise ValueError("Parent submission changed: " + str(path))
        submissions[sub.system_id] = sub
    return {"parent": parent, "manifest": manifest, "benchmark": benchmark, "systems": systems,
            "sampling": sampling, "submissions": submissions}


def targets(state):
    """Eligible sampled entities and the eligible candidate pool, per system and document."""
    out = {}
    for sid, sub in state["submissions"].items():
        docs = {d["document_id"]: d for d in sub.payload["documents"]}
        out[sid] = {}
        for sample in state["sampling"][sid]:
            did = sample["document_id"]
            units = state["benchmark"].unit_by_document[did]
            entities = {str(e["id"]): e for e in docs[did]["entities"]}
            size = {eid: source_bytes(e, units) for eid, e in entities.items()}
            eligible = {eid for eid, n in size.items() if n <= SOURCE_LIMIT}
            out[sid][did] = {
                "entities": entities, "units": units,
                "targets": [eid for eid in sample["entity_ids"] if eid in eligible],
                "ineligible_targets": [eid for eid in sample["entity_ids"] if eid not in eligible],
                "pool": sorted(eligible),
                "pool_excluded": sorted(set(entities) - eligible),
            }
    return out


def target_key(sid, did, eid):
    return _key("q", sid, did, eid)


def candidate_key(sid, did, eid, cid):
    return _key("c", sid, did, eid, cid)


def _entity_text(entity):
    return " ".join([str(entity["name"]), *map(str, entity.get("aliases", []))])


class _Index:
    """BM25 over entity names and aliases only; never descriptions or source text."""

    def __init__(self, entities, pool):
        self.ids = list(pool)
        self.postings = defaultdict(list)
        self.lengths = []
        for i, eid in enumerate(self.ids):
            counts = Counter(_tokens(_entity_text(entities[eid])))
            self.lengths.append(sum(counts.values()))
            for token, tf in counts.items():
                self.postings[token].append((i, tf))
        self.average = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0

    def rank(self, term, exclude):
        scores = defaultdict(float)
        total = len(self.ids)
        for token in set(_tokens(term)):
            rows = self.postings.get(token, ())
            idf = math.log(1 + (total - len(rows) + 0.5) / (len(rows) + 0.5))
            for i, tf in rows:
                scores[i] += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * self.lengths[i] / self.average))
        ranked = sorted(((-s, self.ids[i]) for i, s in scores.items() if s > 0 and self.ids[i] != exclude))
        return [eid for _, eid in ranked]


def query_terms(entity, expansions):
    terms, seen = [], set()
    for term in [entity["name"], *entity.get("aliases", []), *expansions]:
        term = str(term).strip()
        key = " ".join(_tokens(term))
        if term and key and key not in seen:
            seen.add(key)
            terms.append(term)
    return terms


def search(index, entity, eid, expansions, limit=CANDIDATES):
    """Round-robin over each term's ranking, so one spelling cannot fill every slot."""
    lists = [index.rank(term, eid) for term in query_terms(entity, expansions)]
    chosen, seen, depth = [], set(), 0
    while len(chosen) < limit and any(depth < len(x) for x in lists):
        for ranking in lists:
            if depth < len(ranking) and ranking[depth] not in seen:
                seen.add(ranking[depth])
                chosen.append(ranking[depth])
                if len(chosen) == limit:
                    break
        depth += 1
    return chosen


def _view(entity):
    return {"name": entity["name"], "aliases": list(entity.get("aliases", [])),
            "types": list(entity.get("types", [])) if present(entity, "types") else []}


def target_sheet(state, scope=None):
    """Blinded rows for writing equivalent names: no system, document or entity IDs."""
    scope = scope or targets(state)
    rows = []
    for sid, docs in scope.items():
        for did, doc in docs.items():
            for eid in doc["targets"]:
                entity = doc["entities"][eid]
                rows.append({"key": target_key(sid, did, eid), **_view(entity),
                             "definition": entity["definition"] if present(entity, "definition") else ""})
    return sorted(rows, key=lambda r: r["key"])


def candidates(state, expansions, scope=None):
    scope = scope or targets(state)
    expected = {r["key"] for r in target_sheet(state, scope)}
    if set(expansions) != expected:
        raise ValueError("Expansions must cover exactly the eligible targets")
    if any(not isinstance(v, list) or any(not isinstance(t, str) for t in v) for v in expansions.values()):
        raise ValueError("Each expansion must be a list of strings")
    out = {}
    for sid, docs in scope.items():
        for did, doc in docs.items():
            index = _Index(doc["entities"], doc["pool"])
            for eid in doc["targets"]:
                tkey = target_key(sid, did, eid)
                found = search(index, doc["entities"][eid], eid, expansions[tkey])
                out[tkey] = {"system": sid, "document_id": did, "entity_id": eid,
                             "candidates": [{"key": candidate_key(sid, did, eid, cid), "entity_id": cid}
                                            for cid in found]}
    return out


def screening_sheet(state, expansions, scope=None):
    scope = scope or targets(state)
    found = candidates(state, expansions, scope)
    rows = []
    for tkey, row in sorted(found.items()):
        entities = scope[row["system"]][row["document_id"]]["entities"]
        rows.append({"key": tkey, "target": _view(entities[row["entity_id"]]),
                     "candidates": [{"key": c["key"], **_view(entities[c["entity_id"]])}
                                    for c in row["candidates"]]})
    return rows


def _judge_view(entity, units):
    return {**_view(entity), "definition": entity["definition"] if present(entity, "definition") else "",
            "evidence": _source_rows(entity, units)}


def payload(entities, units, eid, cid):
    return {"entity_a": _judge_view(entities[eid], units), "entity_b": _judge_view(entities[cid], units)}


def messages(task):
    return identity_judge.duplicate_messages(task["payload"])


def prepare(parent, expansions_path, screening_path, run, *, workers=6):
    run = Path(run).resolve()
    if run.exists():
        raise ValueError("Use a new semantic-duplicate run directory")
    if type(workers) is not int or not 1 <= workers <= 6:
        raise ValueError("workers must be in 1..6")
    state = load_parent(parent)
    scope = targets(state)
    expansions, screening = read(expansions_path), read(screening_path)
    found = candidates(state, expansions, scope)
    if set(screening) != set(found):
        raise ValueError("Screening must cover exactly the eligible targets")
    tasks, keys, sampling = [], {}, {}
    seed = read(state["parent"] / "config.json").get("seed", 0)
    for tkey, row in sorted(found.items()):
        sid, did, eid = row["system"], row["document_id"], row["entity_id"]
        by_key = {c["key"]: c["entity_id"] for c in row["candidates"]}
        flagged = screening[tkey]
        if not isinstance(flagged, list) or len(set(flagged)) != len(flagged) or set(flagged) - set(by_key):
            raise ValueError("Screened pairs must be distinct candidates of their target: " + tkey)
        doc = scope[sid][did]
        for ckey in sorted(flagged):
            cid = by_key[ckey]
            sub_hash = state["systems"][sid]["submission_hash"]
            tid = "t_" + canonical_hash([protocol.VERSION, VERSION, sub_hash, seed, did, eid, cid]).split(":")[1][:24]
            task = {"id": tid, "metric": "semantic_duplicate",
                    "payload": payload(doc["entities"], doc["units"], eid, cid), "max_tokens": 8192}
            task["messages"] = messages(task)
            task["input_bytes"] = len(json.dumps(task["messages"], ensure_ascii=False).encode())
            task["oversized"] = task["input_bytes"] > MAX_INPUT_BYTES
            tasks.append(task)
            keys[tid] = {"system": sid, "document_id": did, "item_id": f"{eid}:duplicate:{cid}",
                         "target_id": eid, "candidate_id": cid, "metric": "semantic_duplicate",
                         "submission_hash": sub_hash}
    for sid, docs in scope.items():
        sampling[sid] = [{
            "document_id": did, "target_ids": doc["targets"],
            "ineligible_target_ids": doc["ineligible_targets"],
            "pool_excluded_count": len(doc["pool_excluded"]),
            "pool_excluded_ids": doc["pool_excluded"],
            "candidates": {eid: [c["entity_id"] for c in found[target_key(sid, did, eid)]["candidates"]]
                           for eid in doc["targets"]},
            "flagged": {eid: sorted(next(c["entity_id"] for c in found[target_key(sid, did, eid)]["candidates"]
                                         if c["key"] == k) for k in screening[target_key(sid, did, eid)])
                        for eid in doc["targets"]},
        } for did, doc in docs.items()]
    tasks.sort(key=lambda t: t["id"])
    run.mkdir(parents=True)
    parent_dir = state["parent"]
    for name, value in (
        ("tasks.json", tasks), ("private-key.json", keys), ("sampling.json", sampling),
        ("systems.json", state["systems"]), ("structure.json", read(parent_dir / "structure.json")),
        ("prompts.json", {"version": protocol.VERSION, "metric_versions": {"semantic_duplicate": VERSION},
                          "semantic_duplicate": identity_judge.DUPLICATE_PROMPT}),
        ("expansions.json", expansions), ("screening.json", screening),
        ("config.json", {"parent": str(parent_dir), "workers": workers, "seed": seed,
                         "source_limit_bytes": SOURCE_LIMIT, "candidates_per_target": CANDIDATES}),
    ):
        write(run / name, value)
    inputs = {str(Path(expansions_path).resolve()): sha(expansions_path),
              str(Path(screening_path).resolve()): sha(screening_path)}
    for name in ("manifest.json", "sampling.json", "systems.json", "structure.json", "config.json"):
        inputs[str(parent_dir / name)] = sha(parent_dir / name)
    write(run / "manifest.json", {
        "protocol": protocol.VERSION, "metric_versions": {"semantic_duplicate": VERSION},
        "model": "MiniMax-M3", "workers": workers, "temperature": 0,
        "evaluation_scope": "semantic_duplicate_only", "selected_metrics": ["semantic_duplicate"],
        "created_at": time.time(), "input_hashes": inputs, "code_hashes": code_hashes(),
        "benchmark_hash": state["manifest"]["benchmark_hash"], "parent_protocol": state["manifest"]["protocol"],
        "frozen_files": {p.name: sha(p) for p in run.iterdir() if p.is_file()},
        "counts": {"semantic_duplicate": len(tasks)}, "total_tasks": len(tasks),
        "planned_calls_without_retries": len(tasks), "max_attempts_per_request": 3,
        "oversized": sum(t["oversized"] for t in tasks), "max_input_bytes": MAX_INPUT_BYTES,
        "retriever": {"id": "entity-name-bm25-round-robin-v1", "fields": "name+aliases",
                      "top_k": CANDIDATES, "k1": K1, "b": B},
    })
    from .reporting import report
    report(run)
    return {"run": str(run), "tasks": len(tasks), "workers": workers,
            "targets": {sid: sum(len(d["targets"]) for d in docs.values()) for sid, docs in scope.items()}}


def aggregate(sampling, tasks, keys, results):
    """Entity-level outcome: any strict same-referent pair makes the target a duplicate."""
    pairs = defaultdict(list)
    for task in tasks:
        k = keys[task["id"]]
        pairs[(k["document_id"], k["target_id"])].append((k, results[task["id"]]))
    outcomes, statuses, pair_labels, duplicates = Counter(), Counter(), Counter(), []
    n = ineligible = excluded = 0
    for doc in sampling:
        n += len(doc["target_ids"])
        ineligible += len(doc["ineligible_target_ids"])
        excluded += doc["pool_excluded_count"]
        for eid in doc["target_ids"]:
            rows = pairs.get((doc["document_id"], eid), [])
            labels = []
            for k, r in rows:
                statuses[r["status"]] += 1
                if r["status"] == "done":
                    labels.append(r["value"]["label"])
                    pair_labels[r["value"]["label"]] += 1
                    if r["value"]["label"] == "pass":
                        duplicates.append({"document_id": doc["document_id"], "target_id": eid,
                                           "candidate_id": k["candidate_id"], "reason": r["value"]["reason"]})
            if "pass" in labels:
                outcomes["duplicate"] += 1
            elif len(labels) < len(rows):
                outcomes["unresolved"] += 1
            elif "uncertain" in labels:
                outcomes["uncertain"] += 1
            else:
                outcomes["none"] += 1
    expected, done = len(tasks), statuses["done"]
    status = "not_applicable" if not n else "complete" if done == expected else "incomplete"
    rate = outcomes["duplicate"] / n if n else None
    return {
        "status": status, "na_reason": None if n else "No eligible sampled entities",
        "expected": expected, "done": done, "unassessed": expected - done, "statuses": dict(statuses),
        "labels": {k: v for k, v in outcomes.items() if k != "unresolved"},
        "unresolved_targets": outcomes["unresolved"], "pair_labels": dict(pair_labels),
        "numerator": outcomes["duplicate"], "denominator": n,
        "rate": rate if status == "complete" else None,
        "partial_rate_judged_only": rate, "aggregation": "entity_duplicate",
        "uncertain_rate": outcomes["uncertain"] / n if n and status == "complete" else None,
        "ineligible_targets": ineligible, "pool_excluded": excluded, "flagged_pairs": expected,
        "duplicates": duplicates, "lower_is_better": True,
        "sampled_entities": None, "field_absent": 0, "atomic": {}, "finest_supported_type": {},
        "whole_support_rate": None,
    }
