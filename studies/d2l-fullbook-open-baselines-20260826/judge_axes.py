"""Judge sampled assertions on three separate quality axes.

v2 bundled grounding, projection fidelity and scope into one question, so a
system whose triples were true-but-misprojected scored the same as one whose
triples were false. Text2KGBench (Mihindukulasooriya et al., ISWC 2023) splits
fact extraction from ontology conformance and hallucination for the same
reason; it also notes that its conformance and relation-hallucination metrics
are complements of each other, so each prompt below explicitly tells the judge
to ignore the other two axes and the pass writes the axes independently for a
later collinearity check.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from judge_tasks import iter_json_objects
from review_tasks import read_jsonl, render_task

AXIS_PROMPTS = {
    "assertion_grounding_v3": """你只判定一件事：**来源证据是否支持该断言所陈述的内容**。

- 只看内容层面的真假：证据里有没有说这件事。
- **不要**因为主谓宾的结构表达得不好、关系方向别扭而判 fail —— 那是另一个维度在管。
- **不要**因为限定条件缺失或多余而判 fail —— 那也是另一个维度在管。
- 若断言包含证据没有说到的实质内容（凭空添加的细节、数值、实体），判 fail。""",
    "assertion_projection": """你只判定一件事：**(主语, 谓词, 宾语) 这个三元组是否忠实地投影了原文所表达的关系**。

- 关系方向对不对？主语是不是该关系真正的承担者？宾语是不是真正的受体？
- 谓词的语义与原文一致吗？（把"相似"写成"包含"、把"辅助函数"写成"定义于"、把"参数传入"写成"包含"都算不忠实）
- 谓词的强度对不对？不能比原文更强或更弱。
- 主语或宾语的粒度对不对？（把"唤醒词识别任务"压缩成"唤醒词"算不忠实）
- **假设内容本身是原文支持的**；即使你觉得证据不支持这个说法，也只按"如果原文这么说了，这个三元组表达得对不对"来判。
- **不要**因为限定条件缺失而判 fail —— 那是另一个维度在管。""",
    "assertion_scope": """你只判定一件事：**该断言（含 scope 字段和 text）是否忠实保留了原文的限定条件**。

- 原文有的必要限定（条件、适用范围、时间、适用对象、否定）有没有被丢掉？
  例：原文说"学习率持续过高时"，断言写成无条件成立 → fail。
- 有没有加上原文没有的限定？例：原文只说"隐藏层"，断言写成"单隐藏层" → fail。
- 原文本来就是无条件陈述、断言也没加限定 → pass。
- **不要**因为内容本身是否被证据支持而判 fail —— 那是另一个维度在管。
- **不要**因为三元组结构或关系方向而判 fail —— 那也是另一个维度在管。""",
}

SYSTEM_PROMPT_TEMPLATE = """你是知识图谱质量评审员。你会看到一条从某个知识图谱抽取系统产出的断言，以及它所依据的来源证据。

{axis}

通用规则：
- 只依据给出的来源证据判定，不要用你自己的背景知识去补全证据没有说到的内容。
- pass = 在本维度上成立；fail = 在本维度上不成立；uncertain = 证据不足以就本维度作判断。
- 不要推测这条数据来自哪个系统，只判这一条本身。

只输出一个 JSON 对象，不要有任何其他文字、解释或代码块标记：
{{"label": "pass|fail|uncertain", "confidence": 0.0-1.0, "reason": "一句中文理由，不超过60字"}}"""

API_URL = "https://api.minimaxi.com/v1/chat/completions"


def build_prompt(task: dict) -> str:
    rendered = dict(task)
    rendered["kind"] = "assertion_grounding"  # reuse the assertion renderer
    return f"判定维度：{task['kind']}\n\n待判定项：\n{render_task(rendered)}"


def parse_verdict(text: str) -> dict:
    payload = None
    for span in iter_json_objects(text.strip()):
        try:
            candidate = json.loads(span)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "label" in candidate:
            payload = candidate
    if payload is None:
        raise ValueError(f"no verdict object in response: {text[:200]!r}")
    label = str(payload.get("label", "")).strip().lower()
    if label not in {"pass", "fail", "uncertain"}:
        raise ValueError(f"unexpected label: {label!r}")
    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "label": label,
        "confidence": round(min(max(confidence, 0.0), 1.0), 4),
        "reason": str(payload.get("reason", "")).strip()[:200],
    }


def call_model(task, prompt, model, api_key, max_tokens, timeout):
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(axis=AXIS_PROMPTS[task["kind"]])
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    choice = payload["choices"][0]["message"]["content"]
    return parse_verdict(choice), payload.get("usage", {}) or {}


def judge_one(task, args, api_key):
    prompt = build_prompt(task)
    last_error = ""
    for attempt in range(1, args.retries + 1):
        try:
            verdict, usage = call_model(task, prompt, args.model, api_key,
                                        args.max_tokens, args.timeout)
            verdict.update({"task_id": task["task_id"], "kind": task["kind"],
                            "judge_id": args.judge_id, "attempts": attempt})
            return verdict, usage
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                ValueError, KeyError, json.JSONDecodeError, OSError) as error:
            last_error = f"{type(error).__name__}: {error}"
            if attempt < args.retries:
                time.sleep(min(2**attempt, 30))
    return ({"task_id": task["task_id"], "kind": task["kind"],
             "judge_id": args.judge_id, "label": "error", "confidence": 0.0,
             "reason": last_error[:200], "attempts": args.retries}, {})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="MiniMax-M3")
    parser.add_argument("--judge-id", default="minimax-m3-assertion-axes-v1")
    parser.add_argument("--api-key-env", default="MINIMAX_API_KEY")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is required")

    pool = read_jsonl(args.tasks)
    random.Random(args.seed).shuffle(pool)
    if args.limit:
        pool = pool[: args.limit]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    judgments_path = args.out_dir / "judgments.jsonl"
    done = set()
    if judgments_path.exists():
        for row in read_jsonl(judgments_path):
            if row.get("label") != "error":
                done.add(row["task_id"])
    pending = [t for t in pool if t["task_id"] not in done]
    print(f"pool={len(pool)} done={len(done)} pending={len(pending)} "
          f"workers={args.workers} model={args.model}", flush=True)

    lock = threading.Lock()
    counters = {"pass": 0, "fail": 0, "uncertain": 0, "error": 0}
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    completed = 0
    started = time.time()
    with judgments_path.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(judge_one, t, args, api_key): t
                       for t in pending}
            for future in as_completed(futures):
                verdict, usage = future.result()
                with lock:
                    handle.write(json.dumps(verdict, ensure_ascii=False,
                                            sort_keys=True) + "\n")
                    handle.flush()
                    counters[verdict["label"]] = counters.get(
                        verdict["label"], 0) + 1
                    for key in usage_total:
                        usage_total[key] += int(usage.get(key, 0) or 0)
                    completed += 1
                    if completed % 50 == 0 or completed == len(pending):
                        print(f"[{completed}/{len(pending)}] "
                              f"kind={verdict['kind']} "
                              f"pass={counters['pass']} fail={counters['fail']} "
                              f"unc={counters['uncertain']} "
                              f"err={counters['error']} "
                              f"elapsed={time.time()-started:.0f}s", flush=True)

    report = {
        "judge_id": args.judge_id, "model": args.model, "seed": args.seed,
        "pool_size": len(pool), "judged_this_invocation": len(pending),
        "labels": counters, "usage": usage_total,
        "wall_seconds_this_invocation": round(time.time() - started, 3),
        "axes": list(AXIS_PROMPTS),
        "blinding": "system-anonymized; not strictly blind (graph shape leaks identity)",
    }
    (args.out_dir / "judge-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    raise SystemExit(1 if counters["error"] else 0)


if __name__ == "__main__":
    main()
