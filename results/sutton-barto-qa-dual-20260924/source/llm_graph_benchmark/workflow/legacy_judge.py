"""Frozen judging logic migrated from studies/d2l-fullbook-open-baselines-20260826/judge_tasks.py."""
import json
from .legacy_render import render_task

RUBRIC_QUESTIONS = {'alias_identity': 'Is the submitted alias genuinely coreferential with this entity rather than a related, broader, narrower, or context-local expression?', 'identity_split': 'Given their definitions and evidence, is it correct to keep these two entities separate despite a shared surface form?', 'book_qa': 'Do the retrieved graph assertions contain enough correct information to answer the book question completely?'}

SYSTEM_PROMPT = """你是知识图谱质量评审员。你会看到一条从某个知识图谱抽取系统产出的待判定项，以及它所依据的来源证据。

判定规则：
- 只依据给出的来源证据判定，不要用你自己的背景知识去补全证据没有说到的内容。
- pass = 该项在给出的证据下成立；fail = 不成立、错配、或包含证据不支持的实质内容；uncertain = 证据不足以判定。
- 不要因为表述简略就判 fail，也不要因为看起来合理就判 pass。
- 不要推测这条数据来自哪个系统，只判这一条本身。

只输出一个 JSON 对象，不要有任何其他文字、解释或代码块标记：
{"label": "pass|fail|uncertain", "confidence": 0.0-1.0, "reason": "一句中文理由，不超过60字"}"""


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
