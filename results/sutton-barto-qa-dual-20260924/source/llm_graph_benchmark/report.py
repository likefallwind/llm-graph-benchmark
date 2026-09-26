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
        "优先报告盲评结果；Entity 与 Assertion 的裁判结果分别报告，结构规模不是质量分数。",
    ]
    if judged_systems:
        lines.extend(
            [
                "",
                "## Blind judgments",
                "",
                "Pass/all 以全部预定样本为分母，反映已确认通过的比例；缺失或调用错误不等于语义错误。",
                "Pass/decided 仅使用 pass+fail，排除 uncertain；需同时阅读判定覆盖率与任务完成状态。",
                "Wilson 区间仅描述已明确判定样本的抽样不确定性，不涵盖裁判偏差或跨材料泛化。",
                "",
                "| System | Dimension | Pass | Fail | Uncertain | Error | Unjudged | Pass/all | Pass/decided | Decided CI | Judgment coverage | Status |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
            ]
        )
        for system_id, dimensions in sorted(judged_systems.items()):
            for kind, result in sorted(dimensions.items()):
                interval = result["pass_rate_95ci"]
                interval_text = f"[{interval[0]:.3f}, {interval[1]:.3f}]" if interval else "—"
                lines.append(
                    f"| {system_id} | {kind} | {result['pass']} | {result['fail']} | "
                    f"{result['uncertain']} | {result.get('error', 0)} | {result['unjudged']} | "
                    f"{_display(result.get('pass_rate_all'))} | {_display(result['pass_rate'])} | "
                    f"{interval_text} | {_display(result.get('judgment_coverage'))} | {result.get('status', 'legacy')} |"
                )
    else:
        lines.extend(["", "未提供盲评结果；以下结构统计不能用于判断抽取正确性。"])
    lines.extend(
        [
            "",
            "## Structure, citation presence, and cost",
            "",
            "引用存在率仅表示 Entity 或 Assertion 是否附有 evidence，不代表引用内容正确或足以支持该条目。",
            "",
            "| System | Entities | Assertions | Entity citation presence | Assertion citation presence | Isolated rate | Cost (USD) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
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
    lines.append("")
    return "\n".join(lines)
