from __future__ import annotations

from typing import Any, Iterable


def _display(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def markdown_report(
    metric_payloads: Iterable[dict[str, Any]], judged: dict[str, Any] | None = None
) -> str:
    metrics = list(metric_payloads)
    judged_systems = (judged or {}).get("systems", {})
    lines = [
        "# LLM Graph Benchmark Report",
        "",
        "结构规模不是质量分数；Entity 与 Assertion 的裁判结果分别报告。",
        "",
        "| System | Entities | Assertions | Entity evidence | Assertion evidence | Isolated rate | Cost (USD) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for payload in sorted(metrics, key=lambda item: str(item.get("system_id", ""))):
        summary = payload["summary"]
        lines.append(
            "| {system} | {entities} | {assertions} | {entity_ev} | {assertion_ev} | {isolated} | {cost} |".format(
                system=payload["system_id"],
                entities=summary["entity_count"],
                assertions=summary["assertion_count"],
                entity_ev=_display(summary["entity_evidence_coverage"]),
                assertion_ev=_display(summary["assertion_evidence_coverage"]),
                isolated=_display(summary["isolated_entity_rate"]),
                cost=_display(summary.get("cost_usd")),
            )
        )
    if judged_systems:
        lines.extend(
            [
                "",
                "## Blind judgments",
                "",
                "`uncertain` 和投票平局不进入 pass rate 分母。",
                "",
                "| System | Dimension | Pass | Fail | Uncertain | Unjudged | Pass rate | 95% CI |",
                "|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for system_id, dimensions in sorted(judged_systems.items()):
            for kind, result in sorted(dimensions.items()):
                interval = result["pass_rate_95ci"]
                lines.append(
                    f"| {system_id} | {kind} | {result['pass']} | {result['fail']} | "
                    f"{result['uncertain']} | {result['unjudged']} | {_display(result['pass_rate'])} | "
                    f"[{interval[0]:.3f}, {interval[1]:.3f}] |"
                )
    lines.append("")
    return "\n".join(lines)
