"""Independent local checks of the completed trial; never rewrites labels."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow import qa_support
from llm_graph_benchmark.workflow.preparation import read, verify, sha
from llm_graph_benchmark.workflow.reporting import result_for
from llm_graph_benchmark.workflow.transport import write

RUN = ROOT / "outputs/rl-qa-dual-20260924"
manifest = verify(RUN)
tasks, keys = read(RUN / "tasks.json"), read(RUN / "private-key.json")
old = {r["task_id"]: r for r in read(RUN / "previous-qa.json")}
rubrics = read(RUN / "qa-requirements.json")
summary = read(RUN / "summary.json")
per_system = defaultdict(Counter)
per_question = defaultdict(set)
past_truncation = []
issues, reviewed_cases = [], []
for path, digest in manifest["input_hashes"].items():
    if sha(path) != digest:
        issues.append("Changed parent input: " + path)
for task in tasks:
    tid, key = task["id"], keys[task["id"]]
    if canonical_hash(task["payload"]) != old[tid]["candidate_payload_hash"]:
        issues.append("Changed candidates: " + tid)
    record = result_for(RUN, task)
    if record["status"] != "done":
        issues.append("Unassessed: " + tid)
        continue
    v = record["value"]
    rubric = rubrics[canonical_hash(task["messages"])]["rubric"]
    if v["rubric"] != rubric:
        issues.append("Shared rubric mismatch: " + tid)
    parsed = qa_support.parse_support({"choices": [{"message": {"content": json.dumps({"judgments": v["judgments"]})}}]}, task, rubric)
    if parsed != v:
        issues.append("Aggregation mismatch: " + tid)
    if v["complete_label"] == "pass" and v["core_label"] != "pass":
        issues.append("Non-nested labels: " + tid)
    per_system[key["system"]]["done"] += 1
    per_system[key["system"]]["core_" + v["core_label"]] += 1
    per_system[key["system"]]["complete_" + v["complete_label"]] += 1
    per_question[(key["document_id"], key["item_id"])].add(v["rubric_hash"])
    assertions = task["payload"]["content"]["candidate_graph_assertions"]
    for judgment in v["judgments"]:
        if judgment["label"] != "pass":
            continue
        for ref in judgment["assertion_evidence"]:
            a = assertions[int(ref["assertion_id"][1:]) - 1]
            previous_display = f"{a['subject']} --{a['predicate']}--> {a['object']} | scope={a.get('scope', '')} | {a['text']}"
            if ref["quote"] in previous_display and previous_display.index(ref["quote"]) + len(ref["quote"]) > 500:
                past_truncation.append({"task_id": tid, **key, "requirement_id": judgment["requirement_id"], **ref})
    if old[tid]["parent_task_id"] in ("t_7c64795a4b28ec6c6dee53c9", "t_97483ddf203e32b69a7a0334"):
        reviewed_cases.append({"task_id": tid, **key, "old_label": old[tid]["previous_value"]["label"],
                               "core_label": v["core_label"], "complete_label": v["complete_label"],
                               "unmet": [j for j in v["judgments"] if j["label"] != "pass"]})
for question, hashes in per_question.items():
    if len(hashes) != 1:
        issues.append("Different method rubrics: " + str(question))
for sid, counts in per_system.items():
    group = summary["groups"][sid]["book_qa"]
    if group["done"] != counts["done"] or group["numerator"] != counts["complete_pass"] or group["core"]["numerator"] != counts["core_pass"]:
        issues.append("Summary mismatch: " + sid)
report = {"complete": summary["complete"], "issues": issues, "counts": dict(per_system),
          "questions": len(per_question), "same_rubric_for_all_methods": all(len(x) == 1 for x in per_question.values()),
          "candidate_quotes_beyond_old_limit": past_truncation, "previous_problem_cases": reviewed_cases,
          "semantic_validation": "Source rubric overreach confirmed; see SOURCE_RUBRIC_REVIEW.md. Not independent human gold."}
write(RUN / "AUDIT.json", report)
print(json.dumps({"complete": report["complete"], "issues": issues, "counts": dict(per_system),
                  "quotes_beyond_old_limit": len(past_truncation), "previous_problem_cases": reviewed_cases}, ensure_ascii=False))
