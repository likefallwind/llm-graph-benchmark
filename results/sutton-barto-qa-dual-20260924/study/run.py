"""Bounded 24-question, four-method QA reassessment; no graph reconstruction."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow import engine, qa_support
from llm_graph_benchmark.workflow.preparation import read, verify, sha
from llm_graph_benchmark.workflow.qa_reassessment import prepare_qa_reassessment
from llm_graph_benchmark.workflow.transport import Client, write

RUN = ROOT / "outputs/rl-qa-dual-20260924"


def prepare():
    archives = [ROOT / "results/sutton-barto-20260923/archive.json"] + [
        ROOT / "results/sutton-barto-baselines-20260923" / name / "archive.json"
        for name in ("graphrag", "autoschemakg", "kggen")]
    result = prepare_qa_reassessment([read(p)["run"] for p in archives], RUN, workers=4)
    manifest = read(RUN / "manifest.json")
    manifest["input_hashes"][str(Path(__file__).resolve())] = sha(Path(__file__))
    write(RUN / "manifest.json", manifest)
    print(result, flush=True)


def rubrics():
    manifest = verify(RUN)
    unique = {canonical_hash(t["messages"]): t for t in read(RUN / "tasks.json")}
    client = Client(RUN / "api", engine.slots_path(), concurrency=manifest["workers"])
    results = {}
    def one(pair):
        fingerprint, task = pair
        raw = client.complete(task["messages"], max_tokens=8192,
            validator=lambda r: qa_support.parse_rubric(r, task["payload"]))
        return fingerprint, {"question": task["payload"]["content"]["question"],
                             "rubric": qa_support.parse_rubric(raw, task["payload"])}
    with ThreadPoolExecutor(max_workers=manifest["workers"]) as pool:
        futures = [pool.submit(one, pair) for pair in unique.items()]
        for future in as_completed(futures):
            fingerprint, result = future.result()
            results[fingerprint] = result
            write(RUN / "qa-requirements-progress.json", {"done": len(results), "total": len(unique)})
            print("source requirements", len(results), "/", len(unique), flush=True)
    path = RUN / "qa-requirements.json"
    if path.exists() and read(path) != results:
        raise ValueError("Previously frozen QA requirements changed")
    write(path, results)
    manifest["frozen_files"][path.name] = sha(path)
    write(RUN / "manifest.json", manifest)


def comparison():
    summary = read(RUN / "summary.json")
    previous = {r["task_id"]: r for r in read(RUN / "previous-qa.json")}
    cases = read(RUN / "case-results.json")
    tasks = {t["id"]: t for t in read(RUN / "tasks.json")}
    systems = read(RUN / "systems.json")
    lines = ["# 强化学习 QA 双指标试评", "",
             "固定原24题和原Top10候选，仅更新QA口径；完整断言不截断。原历史结果保留。", "",
             "|方法|旧QA通过|核心信息支持|完整答案支持|有效任务|",
             "|---|---:|---:|---:|---:|"]
    for sid, system in systems.items():
        group = summary["groups"][sid]["book_qa"]
        old = [r for r in previous.values() if r["system"] == sid]
        count = sum(r["previous_value"]["label"] == "pass" for r in old)
        cell = lambda n: f"{n}/{len(old)}（{n/len(old):.2%}）"
        complete = group["status"] == "complete"
        lines.append(f"|{system['name']}|{cell(count)}|{cell(group['core']['numerator']) if complete else '未完成'}|"
                     f"{cell(group['numerator']) if complete else '未完成'}|{group['done']}/{group['expected']}|")
    lines += ["", "技术完成不等于语义验证。两个新分数使用同一来源侧要点；引文匹配不证明语义蕴含。",
              "BM25跨语言检索、原题集和构图条件沿用旧设置；本轮不能评估其影响。", ""]
    (RUN / "COMPARISON.md").write_text("\n".join(lines), encoding="utf-8")
    review = ["# QA逐题核查", ""]
    pairs = Counter()
    for c in sorted(cases, key=lambda c: (c['item_id'], c['system'])):
        task, old = tasks[c["task_id"]], previous[c["task_id"]]
        review += [f"## {systems[c['system']]['name']} / {c['item_id']}", "",
                   "任务：" + c["task_id"], "", task["payload"]["content"]["question"], ""]
        if c["status"] != "done":
            review += ["未完成：" + c["status"], ""]
            continue
        v = c["value"]
        pairs[(v["core_label"], v["complete_label"])] += 1
        review += [f"旧：{old['previous_value']['label']}；核心：{v['core_label']}；完整：{v['complete_label']}", ""]
        for req, judge in zip(v["rubric"]["requirements"], v["judgments"]):
            review += [f"- {req['id']} {'核心' if req['core'] else '完整答案补充'}：{req['text']}",
                       f"  判定：{judge['label']}；{judge['reason']}"]
            for ref in judge["assertion_evidence"]:
                review.append(f"  {ref['assertion_id']}.{ref['field']}：{ref['quote']}")
        review.append("")
    (RUN / "CASE_REVIEW.md").write_text("\n".join(review), encoding="utf-8")
    print({"complete": summary["complete"], "done": summary["done"], "total": summary["total"],
           "joint_labels": {str(k): n for k, n in pairs.items()}}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "rubrics", "run", "report"))
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "rubrics":
        rubrics()
    elif args.action == "run":
        verify(RUN)
        if not (RUN / "qa-requirements.json").exists():
            raise ValueError("Freeze source-only requirements first")
        write(RUN / "trial-started.json", {"at": time.time()})
        code = engine.execute(RUN, retry_failed=args.retry_failed)
        comparison()
        write(RUN / "trial-exit.json", {"exit_code": code, "at": time.time()})
        raise SystemExit(code)
    else:
        comparison()
