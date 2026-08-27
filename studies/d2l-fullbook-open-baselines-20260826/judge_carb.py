"""Re-judge fact_recovery under CaRB's split matching rule.

The v2 pass emitted one label per probe, so a graph that recovered the fact
but also retrieved unsupported neighbours was scored the same as a graph that
never recovered it. CaRB (Bhardwaj et al., EMNLP 2019) separates the two:
recall is scored multi-match (any candidate may carry the gold fact) while
precision is scored separately over the predicted tuples. This pass therefore
emits ``covered`` (recall side) and ``unsupported`` (precision side) as
independent fields; neither may be lowered because of the other.
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

from review_tasks import read_jsonl, render_task

SYSTEM_PROMPT = """你是知识图谱质量评审员。你会看到一条来自原文的源事实、一组从某个知识图谱检索出来的候选断言，以及这些断言所依据的来源证据。

你要**互相独立**地回答两个问题，任何一个的答案都不允许影响另一个。

问题一 —— covered（召回侧，多匹配）：
候选中是否**存在一条或多条**断言，合起来忠实地表达了该源事实的核心内容？
- 只要有候选覆盖了核心内容就算 covered=yes，**即使其他候选包含无关或无据内容**。
- 允许多条候选共同拼出该事实。
- 只有当核心内容缺失、方向颠倒、或关键限定被改变时才算 covered=no。
- 若源事实是复合的（含对比条件、动机、代价、多步骤机制），当核心命题被覆盖但次要维度缺失时，仍算 covered=yes，并在 reason 中说明缺了哪一维。

问题二 —— unsupported（精度侧，逐条计数）：
在给出的候选中，有多少条包含来源证据不支持的实质内容（含方向错误、实体错配、凭空添加的细节）？
- 这是一个计数，范围 0 到候选总数。
- **不要因为候选里有噪声就把 covered 判成 no。**

只输出一个 JSON 对象，不要有任何其他文字、解释或代码块标记：
{"covered": "yes|no|uncertain", "unsupported": <整数>, "total_candidates": <整数>, "confidence": 0.0-1.0, "reason": "一句中文理由，不超过60字"}"""

API_URL = "https://api.minimaxi.com/v1/chat/completions"


def build_prompt(task: dict) -> str:
    return (
        "判定维度：fact_recovery（CaRB 拆分口径）\n"
        "请独立回答 covered 与 unsupported 两个问题。\n\n"
        f"待判定项：\n{render_task(task)}"
    )


def iter_json_objects(blob: str):
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(blob):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
                if depth == 0:
                    yield blob[start : index + 1]


def parse_verdict(text: str, n_candidates: int) -> dict:
    payload = None
    for span in iter_json_objects(text.strip()):
        try:
            candidate = json.loads(span)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "covered" in candidate:
            payload = candidate
    if payload is None:
        raise ValueError(f"no verdict object in response: {text[:200]!r}")
    covered = str(payload.get("covered", "")).strip().lower()
    if covered not in {"yes", "no", "uncertain"}:
        raise ValueError(f"unexpected covered: {covered!r}")
    try:
        unsupported = int(payload.get("unsupported", 0))
    except (TypeError, ValueError):
        unsupported = 0
    try:
        total = int(payload.get("total_candidates", n_candidates))
    except (TypeError, ValueError):
        total = n_candidates
    total = max(total, 0) or n_candidates
    unsupported = min(max(unsupported, 0), total)
    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "covered": covered,
        "unsupported": unsupported,
        "total_candidates": total,
        "confidence": round(min(max(confidence, 0.0), 1.0), 4),
        "reason": str(payload.get("reason", "")).strip()[:200],
    }


def call_model(prompt, model, api_key, max_tokens, timeout, n_candidates):
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    choice = payload["choices"][0]["message"]["content"]
    return parse_verdict(choice, n_candidates), payload.get("usage", {}) or {}


def judge_one(task, args, api_key):
    prompt = build_prompt(task)
    n_candidates = len(task["content"].get("candidate_graph_assertions", []))
    last_error = ""
    for attempt in range(1, args.retries + 1):
        try:
            verdict, usage = call_model(
                prompt, args.model, api_key, args.max_tokens,
                args.timeout, n_candidates,
            )
            verdict.update(
                {
                    "task_id": task["task_id"],
                    "judge_id": args.judge_id,
                    "attempts": attempt,
                }
            )
            return verdict, usage
        except (
            urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ValueError, KeyError, json.JSONDecodeError, OSError,
        ) as error:
            last_error = f"{type(error).__name__}: {error}"
            if attempt < args.retries:
                time.sleep(min(2**attempt, 30))
    return (
        {
            "task_id": task["task_id"],
            "judge_id": args.judge_id,
            "covered": "error",
            "unsupported": 0,
            "total_candidates": n_candidates,
            "confidence": 0.0,
            "reason": last_error[:200],
            "attempts": args.retries,
        },
        {},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="MiniMax-M3")
    parser.add_argument("--judge-id", default="minimax-m3-carb-fact-recovery-v1")
    parser.add_argument("--api-key-env", default="MINIMAX_API_KEY")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=6144)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is required")

    pool = []
    for entry in args.source:
        system_id, _, path = entry.partition("=")
        for task in read_jsonl(Path(path) / "all-tasks.jsonl"):
            if task["kind"] == "fact_recovery":
                task["_system_id"] = system_id
                pool.append(task)
    random.Random(args.seed).shuffle(pool)
    if args.limit:
        pool = pool[: args.limit]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    judgments_path = args.out_dir / "judgments.jsonl"
    done = set()
    if judgments_path.exists():
        for row in read_jsonl(judgments_path):
            if row.get("covered") != "error":
                done.add(row["task_id"])
    pending = [t for t in pool if t["task_id"] not in done]

    (args.out_dir / "pool-map.json").write_text(
        json.dumps(
            {
                "seed": args.seed,
                "judge_id": args.judge_id,
                "model": args.model,
                "protocol": "CaRB split matching: multi-match recall (covered), "
                            "separate precision count (unsupported)",
                "systems": {t["task_id"]: t["_system_id"] for t in pool},
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"pool={len(pool)} done={len(done)} pending={len(pending)} "
          f"workers={args.workers} model={args.model}", flush=True)

    lock = threading.Lock()
    counters = {"yes": 0, "no": 0, "uncertain": 0, "error": 0}
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
                    counters[verdict["covered"]] = counters.get(
                        verdict["covered"], 0) + 1
                    for key in usage_total:
                        usage_total[key] += int(usage.get(key, 0) or 0)
                    completed += 1
                    if completed % 10 == 0 or completed == len(pending):
                        print(f"[{completed}/{len(pending)}] "
                              f"covered={verdict['covered']} "
                              f"yes={counters['yes']} no={counters['no']} "
                              f"unc={counters['uncertain']} "
                              f"err={counters['error']} "
                              f"elapsed={time.time()-started:.0f}s", flush=True)

    report = {
        "judge_id": args.judge_id, "model": args.model, "seed": args.seed,
        "pool_size": len(pool), "judged_this_invocation": len(pending),
        "covered_counts": counters, "usage": usage_total,
        "wall_seconds_this_invocation": round(time.time() - started, 3),
        "protocol": "CaRB split matching (multi-match recall / separate precision)",
        "blinding": "system-anonymized; not strictly blind (graph shape leaks identity)",
    }
    (args.out_dir / "judge-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    raise SystemExit(1 if counters["error"] else 0)


if __name__ == "__main__":
    main()
