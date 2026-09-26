"""Prepare a QA-only run from unchanged, previously frozen candidate lists."""
from pathlib import Path
import json
import time

from ..bundle import canonical_hash
from . import protocol
from .preparation import read, sha, code_hashes, MAX_INPUT_BYTES
from .reporting import result_for, report
from .transport import write


def prepare_qa_reassessment(parents, run, *, workers=4):
    run = Path(run).resolve()
    if run.exists():
        raise ValueError("Use a new QA run directory")
    if type(workers) is not int or not 1 <= workers <= 6:
        raise ValueError("workers must be in 1..6")
    tasks, keys, systems, structures, inputs, previous = [], {}, {}, {}, {}, []
    questions = {}
    for parent in parents:
        parent = Path(parent).resolve()
        manifest = read(parent / "manifest.json")
        # Historical code differs deliberately; verify historical data without
        # requiring its code to equal the new QA implementation.
        for name, digest in manifest["frozen_files"].items():
            if sha(parent / name) != digest:
                raise ValueError("Parent frozen input changed: " + str(parent / name))
        for name in ("manifest.json", "tasks.json", "private-key.json", "systems.json", "structure.json"):
            inputs[str(parent / name)] = sha(parent / name)
        parent_keys = read(parent / "private-key.json")
        parent_systems = read(parent / "systems.json")
        for sid in parent_systems:
            if sid in systems:
                raise ValueError("Duplicate parent system")
        systems.update(parent_systems)
        structures.update(read(parent / "structure.json"))
        for old in read(parent / "tasks.json"):
            if old["metric"] != "book_qa":
                continue
            k = parent_keys[old["id"]]
            messages = protocol.messages(old)
            question_key = (k["document_id"], k["item_id"])
            fingerprint = canonical_hash(messages)
            if question_key in questions and questions[question_key] != fingerprint:
                raise ValueError("Methods do not share the same source-side question")
            questions[question_key] = fingerprint
            tid = "t_" + canonical_hash([protocol.VERSION, protocol.VERSIONS["book_qa"],
                                         canonical_hash(old)]).split(":")[1][:24]
            size = len(json.dumps(messages, ensure_ascii=False).encode())
            task = {"id": tid, "metric": "book_qa", "payload": old["payload"],
                    "messages": messages, "max_tokens": 8192, "input_bytes": size,
                    "oversized": size > MAX_INPUT_BYTES}
            tasks.append(task)
            keys[tid] = {**k, "metric": "book_qa"}
            prior = result_for(parent, old)
            inputs[str(parent / "results" / (old["id"] + ".json"))] = sha(parent / "results" / (old["id"] + ".json"))
            previous.append({"task_id": tid, "parent": str(parent), "parent_task_id": old["id"],
                             **k, "previous_status": prior["status"],
                             "previous_value": prior.get("value"),
                             "candidate_payload_hash": canonical_hash(old["payload"])})
    if not tasks:
        raise ValueError("No parent QA tasks")
    # Same ordered questions for every method, not a varying benchmark subset.
    per_system = {sid: {(keys[t["id"]]["document_id"], keys[t["id"]]["item_id"])
                        for t in tasks if keys[t["id"]]["system"] == sid} for sid in systems}
    if any(q != set(questions) for q in per_system.values()):
        raise ValueError("Parent methods have different question sets")
    tasks.sort(key=lambda t: (keys[t["id"]]["item_id"], keys[t["id"]]["system"]))
    run.mkdir(parents=True)
    for name, value in (("tasks.json", tasks), ("private-key.json", keys),
                        ("systems.json", systems), ("structure.json", structures),
                        ("sampling.json", {sid: [] for sid in systems}),
                        ("prompts.json", protocol.prompt_snapshot()), ("previous-qa.json", previous),
                        ("config.json", {"workers": workers, "parents": [str(Path(p).resolve()) for p in parents]})):
        write(run / name, value)
    write(run / "manifest.json", {
        "protocol": protocol.VERSION, "metric_versions": protocol.VERSIONS,
        "model": "MiniMax-M3", "workers": workers, "temperature": 0,
        "evaluation_scope": "book_qa_only", "created_at": time.time(),
        "input_hashes": inputs, "code_hashes": code_hashes(),
        "benchmark_hash": canonical_hash(sorted((list(k), v) for k, v in questions.items())),
        "frozen_files": {p.name: sha(p) for p in run.iterdir() if p.is_file()},
        "counts": {"book_qa": len(tasks)}, "total_tasks": len(tasks),
        "planned_calls_without_retries": len(tasks) + len(questions),
        "source_only_qa_rubrics": len(questions),
        "oversized": sum(t["oversized"] for t in tasks), "max_input_bytes": MAX_INPUT_BYTES,
        "retriever": "unchanged parent frozen Top10 candidates",
    })
    report(run)
    return {"run": str(run), "tasks": len(tasks), "questions": len(questions)}
