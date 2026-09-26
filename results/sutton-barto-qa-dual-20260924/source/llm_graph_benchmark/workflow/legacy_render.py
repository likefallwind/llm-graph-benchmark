"""Frozen judging logic migrated from studies/d2l-fullbook-open-baselines-20260826/review_tasks.py."""
import json

def compact(value: object, limit: int = 900) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "..."

def evidence_text(task: dict, limit: int = 1200) -> str:
    rows = task.get("source_evidence") or task.get("evidence") or []
    texts: list[str] = []
    for row in rows:
        unit = row.get("unit", row)
        text = str(unit.get("text", "")).strip()
        if text and text not in texts:
            texts.append(text)
    return " | ".join(texts)[:limit]

def candidates_text(content: dict) -> str:
    lines = []
    for index, row in enumerate(content.get("candidate_graph_assertions", []), start=1):
        statement = (
            f"{row.get('subject')} --{row.get('predicate')}--> {row.get('object')}"
            f" | scope={row.get('scope', '')} | {row.get('text', '')}"
        )
        lines.append(f"{index}. {statement[:500]}")
    return "\n".join(lines)

def render_task(task: dict) -> str:
    content = task["content"]
    lines = [f"task_id={task['task_id']}", f"kind={task['kind']}"]
    if task["kind"].startswith("entity_"):
        lines.extend(
            [
                f"name={content.get('name')}",
                f"aliases={compact(content.get('aliases', []), 500)}",
                f"types={compact(content.get('types', []), 500)}",
                f"definition={content.get('definition', '')}",
            ]
        )
    elif task["kind"] == "assertion_grounding":
        lines.extend(
            [
                f"assertion={content.get('subject')} --{content.get('predicate')}--> {content.get('object')}",
                f"text={content.get('text')}",
                f"scope={content.get('scope', '')}; polarity={content.get('polarity')}",
            ]
        )
    elif task["kind"] == "alias_identity":
        lines.extend(
            [
                f"name={content.get('name')}; alias={content.get('alias')}",
                f"types={compact(content.get('types', []), 500)}",
                f"definition={content.get('definition', '')}",
            ]
        )
    elif task["kind"] == "identity_split":
        lines.append(f"content={compact(content, 2200)}")
    elif task["kind"] == "fact_recovery":
        lines.append(f"source_fact={content.get('source_fact')}")
        lines.append(f"candidates=\n{candidates_text(content)}")
    elif task["kind"] == "book_qa":
        lines.append(f"question={content.get('question')}")
        lines.append(f"reference_answer={content.get('reference_answer')}")
        lines.append(f"candidates=\n{candidates_text(content)}")
    else:
        lines.append(f"content={compact(content, 2200)}")
    if task["kind"] != "identity_split":
        lines.append(f"evidence={evidence_text(task)}")
    return "\n".join(lines)
