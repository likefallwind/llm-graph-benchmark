from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVALUATION = ROOT / "outputs/d2l-full1105-vnext-20260826/evaluation"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def compact(value: object, limit: int = 900) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "..."


def evidence_text(task: dict, limit: int = 900) -> str:
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
        lines.append(f"{index}. {statement[:420]}")
    return "\n".join(lines)


def entity_groups(tasks: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for task in tasks:
        if task["kind"] not in {
            "entity_admission",
            "entity_typing",
            "entity_definition_grounding",
        }:
            continue
        content = task["content"]
        key = json.dumps(content, ensure_ascii=False, sort_keys=True)
        row = grouped.setdefault(
            key,
            {"content": content, "evidence": evidence_text(task), "task_ids": {}},
        )
        row["task_ids"][task["kind"]] = task["task_id"]
    return list(grouped.values())


def render_entity(row: dict) -> str:
    content = row["content"]
    return "\n".join(
        [
            f"task_ids={compact(row['task_ids'], 500)}",
            f"name={content.get('name')}",
            f"aliases={compact(content.get('aliases', []), 500)}",
            f"types={compact(content.get('types', []), 500)}",
            f"definition={content.get('definition', '')}",
            f"evidence={row['evidence']}",
        ]
    )


def render_task(task: dict) -> str:
    content = task["content"]
    lines = [f"task_id={task['task_id']}", f"kind={task['kind']}"]
    if task["kind"] == "assertion_grounding":
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
        lines.append(f"content={compact(content, 1800)}")
    elif task["kind"] == "fact_recovery":
        lines.append(f"source_fact={content.get('source_fact')}")
        lines.append(f"candidates=\n{candidates_text(content)}")
    elif task["kind"] == "book_qa":
        lines.append(f"question={content.get('question')}")
        lines.append(f"reference_answer={content.get('reference_answer')}")
        lines.append(f"candidates=\n{candidates_text(content)}")
    else:
        lines.append(f"content={compact(content, 1800)}")
    if task["kind"] != "identity_split":
        lines.append(f"evidence={evidence_text(task)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "kind",
        choices=["entity", "assertion_grounding", "alias_identity", "identity_split", "fact_recovery", "book_qa"],
    )
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.kind == "entity":
        rows = entity_groups(read_jsonl(EVALUATION / "tasks.jsonl"))
        render = render_entity
    else:
        files = {
            "assertion_grounding": "tasks.jsonl",
            "alias_identity": "identity-tasks.jsonl",
            "identity_split": "identity-tasks.jsonl",
            "fact_recovery": "probe-tasks.jsonl",
            "book_qa": "qa-tasks.jsonl",
        }
        rows = [row for row in read_jsonl(EVALUATION / files[args.kind]) if row["kind"] == args.kind]
        render = render_task
    selected = rows[args.start : args.start + args.limit]
    print(f"kind={args.kind} total={len(rows)} start={args.start} count={len(selected)}")
    for index, row in enumerate(selected, start=args.start):
        print(f"\n### {index}\n{render(row)}")


if __name__ == "__main__":
    main()
