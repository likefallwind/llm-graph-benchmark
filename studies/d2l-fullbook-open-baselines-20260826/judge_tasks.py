"""Pool the three full-book submissions into one judging pass.

Every generated task from every system is judged in a single shuffled,
system-anonymized pass so that pass rates share one calibration. The judge
model never sees which system produced a task, but graph shape still leaks
identity (only one system emits aliases, another emits a single predicate),
so this is recorded as system-anonymized rather than blind.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from review_tasks import read_jsonl, render_task

RUBRIC_QUESTIONS = {
    "entity_admission": (
        "Is this a stable, referable and substantive knowledge entity grounded "
        "in the supplied source evidence?"
    ),
    "entity_typing": (
        "Are all submitted entity types semantically compatible with the entity "
        "and its supplied source context?"
    ),
    "entity_definition_grounding": (
        "Is the submitted entity definition fully supported by the supplied "
        "source evidence without material unsupported additions?"
    ),
    "assertion_grounding": (
        "Does the source support the complete directed assertion, including "
        "polarity and restrictive scope?"
    ),
    "fact_recovery": (
        "Can the submitted graph recover this source-side fact without adding "
        "unsupported content?"
    ),
    "alias_identity": (
        "Is the submitted alias genuinely coreferential with this entity rather "
        "than a related, broader, narrower, or context-local expression?"
    ),
    "identity_split": (
        "Given their definitions and evidence, is it correct to keep these two "
        "entities separate despite a shared surface form?"
    ),
    "book_qa": (
        "Do the retrieved graph assertions contain enough correct information "
        "to answer the book question completely?"
    ),
}

SYSTEM_PROMPT = """你是知识图谱质量评审员。你会看到一条从某个知识图谱抽取系统产出的待判定项，以及它所依据的来源证据。

判定规则：
- 只依据给出的来源证据判定，不要用你自己的背景知识去补全证据没有说到的内容。
- pass = 该项在给出的证据下成立；fail = 不成立、错配、或包含证据不支持的实质内容；uncertain = 证据不足以判定。
- 不要因为表述简略就判 fail，也不要因为看起来合理就判 pass。
- 不要推测这条数据来自哪个系统，只判这一条本身。

只输出一个 JSON 对象，不要有任何其他文字、解释或代码块标记：
{"label": "pass|fail|uncertain", "confidence": 0.0-1.0, "reason": "一句中文理由，不超过60字"}"""

API_URL = "https://api.minimaxi.com/v1/chat/completions"


def build_prompt(task: dict) -> str:
    return (
        f"判定维度：{task['kind']}\n"
        f"判定问题：{RUBRIC_QUESTIONS[task['kind']]}\n\n"
        f"待判定项：\n{render_task(task)}"
    )


def iter_json_objects(blob: str):
    """Yield every balanced ``{...}`` span, so reasoning text around the
    verdict (which may itself contain braces) does not break parsing."""
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


def parse_verdict(text: str) -> dict:
    blob = text.strip()
    payload = None
    for span in iter_json_objects(blob):
        try:
            candidate = json.loads(span)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "label" in candidate:
            payload = candidate
    if payload is None:
        raise ValueError(f"no verdict object in response: {blob[:200]!r}")
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


def call_model(
    prompt: str, model: str, api_key: str, max_tokens: int, timeout: float
) -> tuple[dict, dict]:
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
    return parse_verdict(choice), payload.get("usage", {}) or {}


def judge_one(
    task: dict, args: argparse.Namespace, api_key: str
) -> tuple[dict, dict]:
    prompt = build_prompt(task)
    last_error = ""
    for attempt in range(1, args.retries + 1):
        try:
            verdict, usage = call_model(
                prompt, args.model, api_key, args.max_tokens, args.timeout
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
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ValueError,
            KeyError,
            json.JSONDecodeError,
            OSError,
        ) as error:
            last_error = f"{type(error).__name__}: {error}"
            if attempt < args.retries:
                time.sleep(min(2**attempt, 30))
    return (
        {
            "task_id": task["task_id"],
            "judge_id": args.judge_id,
            "label": "error",
            "confidence": 0.0,
            "reason": last_error[:200],
            "attempts": args.retries,
        },
        {},
    )


def load_pool(sources: list[tuple[str, Path]]) -> list[dict]:
    pool: list[dict] = []
    for system_id, evaluation in sources:
        for task in read_jsonl(evaluation / "all-tasks.jsonl"):
            task["_system_id"] = system_id
            pool.append(task)
    return pool


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True,
                        help="system_id=/path/to/evaluation")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="MiniMax-M3")
    parser.add_argument("--judge-id", default="minimax-m3-source-grounded-v2")
    parser.add_argument("--api-key-env", default="MINIMAX_API_KEY")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=6144)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is required")

    sources = []
    for entry in args.source:
        system_id, _, path = entry.partition("=")
        sources.append((system_id, Path(path)))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    judgments_path = args.out_dir / "judgments.jsonl"
    pool = load_pool(sources)
    random.Random(args.seed).shuffle(pool)
    if args.limit:
        pool = pool[: args.limit]

    done: set[str] = set()
    if judgments_path.exists():
        for row in read_jsonl(judgments_path):
            if row.get("label") != "error":
                done.add(row["task_id"])
    pending = [task for task in pool if task["task_id"] not in done]

    # The system map is written separately so the judged records themselves
    # carry no system identity.
    (args.out_dir / "pool-map.json").write_text(
        json.dumps(
            {
                "seed": args.seed,
                "judge_id": args.judge_id,
                "model": args.model,
                "systems": {
                    task["task_id"]: task["_system_id"] for task in pool
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"pool={len(pool)} done={len(done)} pending={len(pending)} "
        f"workers={args.workers} model={args.model}",
        flush=True,
    )

    lock = threading.Lock()
    counters = {"pass": 0, "fail": 0, "uncertain": 0, "error": 0}
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    completed = 0
    started = time.time()

    with judgments_path.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as pool_executor:
            futures = {
                pool_executor.submit(judge_one, task, args, api_key): task
                for task in pending
            }
            for future in as_completed(futures):
                verdict, usage = future.result()
                task = futures[future]
                with lock:
                    handle.write(
                        json.dumps(verdict, ensure_ascii=False, sort_keys=True)
                        + "\n"
                    )
                    handle.flush()
                    counters[verdict["label"]] = (
                        counters.get(verdict["label"], 0) + 1
                    )
                    for key in usage_total:
                        usage_total[key] += int(usage.get(key, 0) or 0)
                    completed += 1
                    if completed % 20 == 0 or completed == len(pending):
                        elapsed = time.time() - started
                        print(
                            f"[{completed}/{len(pending)}] "
                            f"kind={task['kind']} label={verdict['label']} "
                            f"pass={counters['pass']} fail={counters['fail']} "
                            f"uncertain={counters['uncertain']} "
                            f"error={counters['error']} "
                            f"elapsed={elapsed:.0f}s",
                            flush=True,
                        )

    report = {
        "judge_id": args.judge_id,
        "model": args.model,
        "seed": args.seed,
        "pool_size": len(pool),
        "judged_this_invocation": len(pending),
        "labels": counters,
        "usage": usage_total,
        "wall_seconds_this_invocation": round(time.time() - started, 3),
        "blinding": "system-anonymized; not strictly blind (graph shape leaks identity)",
    }
    (args.out_dir / "judge-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    raise SystemExit(1 if counters["error"] else 0)


if __name__ == "__main__":
    main()
