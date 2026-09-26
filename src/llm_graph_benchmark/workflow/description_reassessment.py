"""Freeze a description-only re-evaluation with unchanged historical samples."""
import json
from pathlib import Path
import time

from ..bundle import canonical_hash
from . import protocol
from .preparation import read, sha, code_hashes, MAX_INPUT_BYTES
from .reporting import result_for, report
from .transport import write


def prepare_description_reassessment(parents, run, *, workers=6):
    run = Path(run).resolve()
    if run.exists():
        raise ValueError("Use a new description run directory")
    if type(workers) is not int or not 1 <= workers <= 6:
        raise ValueError("workers must be in 1..6")
    tasks, keys, systems, structures, sampling, inputs, previous = [], {}, {}, {}, {}, {}, []
    benchmark_hashes = set()
    for parent in parents:
        parent = Path(parent).resolve()
        manifest = read(parent / "manifest.json")
        benchmark_hashes.add(manifest["benchmark_hash"])
        for name, digest in manifest["frozen_files"].items():
            if sha(parent / name) != digest:
                raise ValueError("Parent frozen input changed: " + str(parent / name))
        for name in ("manifest.json", "tasks.json", "private-key.json", "systems.json", "structure.json", "sampling.json"):
            inputs[str(parent / name)] = sha(parent / name)
        parent_keys = read(parent / "private-key.json")
        parent_systems = read(parent / "systems.json")
        if set(parent_systems) & set(systems):
            raise ValueError("Duplicate parent system")
        systems.update(parent_systems)
        structures.update(read(parent / "structure.json"))
        sampling.update(read(parent / "sampling.json"))
        for old in read(parent / "tasks.json"):
            if old["metric"] != "entity_description":
                continue
            key = parent_keys[old["id"]]
            # Exact old target and complete source context; no resampling or truncation.
            tid = "t_" + canonical_hash([protocol.VERSION, protocol.VERSIONS["entity_description"],
                                         canonical_hash(old)]).split(":")[1][:24]
            messages = protocol.messages(old)
            size = len(json.dumps(messages, ensure_ascii=False).encode())
            tasks.append({"id": tid, "metric": "entity_description", "payload": old["payload"],
                          "messages": messages, "max_tokens": 8192, "input_bytes": size,
                          "oversized": size > MAX_INPUT_BYTES})
            keys[tid] = key
            prior = result_for(parent, old)
            if prior["status"] != "done":
                raise ValueError("Expected completed historical description result")
            inputs[str(parent / "results" / (old["id"] + ".json"))] = sha(parent / "results" / (old["id"] + ".json"))
            previous.append({"task_id": tid, "parent_task_id": old["id"], "parent": str(parent),
                             **key, "previous_value": prior["value"],
                             "payload_hash": canonical_hash(old["payload"])})
    if len(benchmark_hashes) != 1:
        raise ValueError("Parents must use the same frozen benchmark")
    if not tasks:
        raise ValueError("No native descriptions to evaluate")
    tasks.sort(key=lambda t: t["id"])
    run.mkdir(parents=True)
    for name, value in (("tasks.json", tasks), ("private-key.json", keys), ("systems.json", systems),
                        ("structure.json", structures), ("sampling.json", sampling),
                        ("prompts.json", protocol.prompt_snapshot()), ("previous-descriptions.json", previous),
                        ("config.json", {"workers": workers, "parents": [str(Path(p).resolve()) for p in parents]})):
        write(run / name, value)
    write(run / "manifest.json", {
        "protocol": protocol.VERSION, "metric_versions": {"entity_description": protocol.VERSIONS["entity_description"]},
        "model": "MiniMax-M3", "workers": workers, "temperature": 0,
        "evaluation_scope": "entity_description_only", "selected_metrics": ["entity_description"],
        "created_at": time.time(), "input_hashes": inputs, "code_hashes": code_hashes(),
        "benchmark_hash": next(iter(benchmark_hashes)),
        "frozen_files": {p.name: sha(p) for p in run.iterdir() if p.is_file()},
        "counts": {"entity_description": len(tasks)}, "total_tasks": len(tasks),
        "planned_calls_without_retries": len(tasks), "max_attempts_per_request": 3,
        "oversized": sum(t["oversized"] for t in tasks), "max_input_bytes": MAX_INPUT_BYTES,
        "retriever": "not used; unchanged historical entity descriptions and submitted sources",
    })
    report(run)
    return {"run": str(run), "tasks": len(tasks), "workers": workers}
