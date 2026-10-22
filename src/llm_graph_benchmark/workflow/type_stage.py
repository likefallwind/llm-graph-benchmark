"""Re-judge entity types under the current type version, as a stage of a completed run.

The parent's frozen entity sample, native type labels and cited sources are reused
unchanged; only the type prompt (and therefore the version) differs. Payloads are
rebuilt from the frozen submissions and must equal the parent's type tasks, so the
stage cannot silently judge a different sample or different evidence.
"""
import json
from pathlib import Path
import time

from ..bundle import canonical_hash
from . import protocol
from .preparation import MAX_INPUT_BYTES, _sources, code_hashes, present, read, sha
from .semantic_duplicate import load_parent
from .transport import write

METRIC = "entity_typing"


def _payload(entity, units):
    target = {"name": entity["name"],
              "types": [{"type_id": f"type-{i}", "type_text": text} for i, text in enumerate(entity["types"])]}
    return {"target": target, "evidence": _sources(entity, units)}


def prepare(parent, run, *, workers=6):
    run = Path(run).resolve()
    if run.exists():
        raise ValueError("Use a new type stage run directory")
    if type(workers) is not int or not 1 <= workers <= 6:
        raise ValueError("workers must be in 1..6")
    state = load_parent(parent)
    parent_dir = state["parent"]
    seed = read(parent_dir / "config.json").get("seed", 0)
    keys_parent = read(parent_dir / "private-key.json")
    previous = {(k["system"], k["document_id"], k["item_id"]): t["payload"]
                for t in read(parent_dir / "tasks.json") if t["metric"] == METRIC
                for k in [keys_parent[t["id"]]]}
    tasks, keys = [], {}
    for sid, sub in state["submissions"].items():
        docs = {d["document_id"]: d for d in sub.payload["documents"]}
        sub_hash = state["systems"][sid]["submission_hash"]
        for sample in state["sampling"][sid]:
            did = sample["document_id"]
            units = state["benchmark"].unit_by_document[did]
            entities = {str(e["id"]): e for e in docs[did]["entities"]}
            for eid in sample["entity_ids"]:
                entity = entities[eid]
                if not present(entity, "types"):
                    continue
                payload = _payload(entity, units)
                if previous.get((sid, did, eid)) != payload:
                    raise ValueError(f"Rebuilt type task differs from the parent's: {sid} {eid}")
                identity = [protocol.VERSION, protocol.VERSIONS[METRIC], sub_hash, seed, did, eid, METRIC]
                tid = "t_" + canonical_hash(identity).split(":")[1][:24]
                task = {"id": tid, "metric": METRIC, "payload": payload, "max_tokens": 8192}
                task["messages"] = protocol.messages(task)
                task["input_bytes"] = len(json.dumps(task["messages"], ensure_ascii=False).encode())
                task["oversized"] = task["input_bytes"] > MAX_INPUT_BYTES
                tasks.append(task)
                keys[tid] = {"system": sid, "document_id": did, "item_id": eid,
                             "metric": METRIC, "submission_hash": sub_hash}
    if len(tasks) != len(previous):
        raise ValueError("Type stage must cover exactly the parent's type tasks")
    tasks.sort(key=lambda t: t["id"])
    run.mkdir(parents=True)
    for name, value in (
        ("tasks.json", tasks), ("private-key.json", keys), ("sampling.json", state["sampling"]),
        ("systems.json", state["systems"]), ("structure.json", read(parent_dir / "structure.json")),
        ("prompts.json", {"version": protocol.VERSION, "metric_versions": {METRIC: protocol.VERSIONS[METRIC]},
                          "types": protocol.SHARED + protocol.TYPES}),
        ("config.json", {"parent": str(parent_dir), "workers": workers, "seed": seed}),
    ):
        write(run / name, value)
    inputs = {str(parent_dir / name): sha(parent_dir / name)
              for name in ("manifest.json", "tasks.json", "private-key.json", "sampling.json",
                           "systems.json", "structure.json", "config.json")}
    write(run / "manifest.json", {
        "protocol": protocol.VERSION, "metric_versions": {METRIC: protocol.VERSIONS[METRIC]},
        "model": "MiniMax-M3", "workers": workers, "temperature": 0,
        "evaluation_scope": "entity_typing_only", "selected_metrics": [METRIC],
        "created_at": time.time(), "input_hashes": inputs, "code_hashes": code_hashes(),
        "benchmark_hash": state["manifest"]["benchmark_hash"], "parent_protocol": state["manifest"]["protocol"],
        "frozen_files": {p.name: sha(p) for p in run.iterdir() if p.is_file()},
        "counts": {METRIC: len(tasks)}, "total_tasks": len(tasks),
        "planned_calls_without_retries": len(tasks), "max_attempts_per_request": 3,
        "oversized": sum(t["oversized"] for t in tasks), "max_input_bytes": MAX_INPUT_BYTES,
    })
    from .reporting import report
    report(run)
    return {"run": str(run), "tasks": len(tasks), "workers": workers,
            "systems": {sid: sum(k["system"] == sid for k in keys.values()) for sid in state["systems"]}}
