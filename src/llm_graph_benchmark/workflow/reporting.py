"""Aggregate only the selected metrics; unresolved technical work stays explicit."""
from collections import Counter
import csv
import io
from pathlib import Path
import time

from ..bundle import canonical_hash
from . import protocol, semantic_duplicate
from .preparation import read, sha
from .transport import write, usage_summary

PASS = {"assertion_correctness": "correct", "entity_correctness": "correct",
        "entity_evidence": "supported", "entity_description": "supported"}
SCOPE_ROWS = {"entity_description_only": ("整段描述", "抽样实体无描述字段数"),
              "semantic_duplicate_only": ("语义重复",)}


def result_for(run, task):
    path = Path(run) / "results" / (task["id"] + ".json")
    if not path.exists():
        return {"status": "pending"}
    result = read(path)
    if result.get("task_id") != task["id"] or result.get("task_hash") != canonical_hash(task):
        raise ValueError("Result does not match frozen task: " + task["id"])
    if result.get("status") == "done" and result.get("value_hash") != canonical_hash(result["value"]):
        raise ValueError("Result value changed: " + task["id"])
    return result


def _ratio(n, d):
    return n / d if d else None


def _stage_not_run():
    return {"status": "not_applicable", "na_reason": "Evaluated in the separate semantic-duplicate stage",
            "expected": 0, "done": 0, "unassessed": 0, "statuses": {}, "labels": {},
            "numerator": None, "denominator": 0, "rate": None, "partial_rate_judged_only": None,
            "aggregation": "entity_duplicate", "uncertain_rate": None, "pool_excluded": 0,
            "sampled_entities": None, "field_absent": 0, "atomic": {}, "finest_supported_type": {},
            "whole_support_rate": None}


def report(run):
    from .engine import slots_path
    run = Path(run).resolve()
    tasks, keys = read(run / "tasks.json"), read(run / "private-key.json")
    systems, structures = read(run / "systems.json"), read(run / "structure.json")
    sampling, manifest = read(run / "sampling.json"), read(run / "manifest.json")
    if any(t["metric"] not in protocol.METRICS for t in tasks):
        raise ValueError("Retired metrics require their archived workflow version")
    selected_metrics = manifest.get("selected_metrics", protocol.METRICS)
    results = {t["id"]: result_for(run, t) for t in tasks}
    details, grouped = [], {}
    for sid in systems:
        groups = grouped[sid] = {}
        for metric in protocol.METRICS:
            selected = [t for t in tasks if keys[t["id"]]["system"] == sid and t["metric"] == metric]
            if metric == "semantic_duplicate":
                for task in selected:
                    r = results[task["id"]]
                    details.append({"task_id": task["id"], **keys[task["id"]], **r})
                groups[metric] = (semantic_duplicate.aggregate(sampling[sid], selected, keys, results)
                                  if manifest.get("evaluation_scope") == "semantic_duplicate_only"
                                  else _stage_not_run())
                continue
            counts, labels, atoms, levels = Counter(), Counter(), Counter(), Counter()
            rates = []
            for task in selected:
                r = results[task["id"]]
                counts[r["status"]] += 1
                if r["status"] != "done":
                    details.append({"task_id": task["id"], **keys[task["id"]], **r})
                    continue
                value = r["value"]
                labels[value["label"]] += 1
                row = {"task_id": task["id"], **keys[task["id"]], "status": "done", "value": value}
                if metric == "entity_typing":
                    values = value["items"]
                    atomic = Counter(x["label"] for x in values)
                    atoms.update(atomic)
                    rates.append(atomic["pass"] / len(values))
                    row["score"] = rates[-1]
                    levels[max((x["level"] for x in values if x["label"] == "pass"), default="none")] += 1
                details.append(row)
            expected, done = len(selected), counts["done"]
            sampled = sum(len(d.get("entity_ids", [])) for d in sampling[sid])
            missing_fields = sum(x["metric"] == metric for d in sampling[sid] for x in d.get("excluded_fields", []))
            success = labels[PASS.get(metric, "pass")]
            partial = sum(rates) / len(rates) if rates else _ratio(success, done)
            status = "not_applicable" if not expected else "complete" if done == expected else "incomplete"
            na_reason = (
                "No native field in the frozen entity sample" if metric in {"entity_typing", "entity_description"}
                else "No eligible nontrivial aliases" if metric == "alias_identity"
                else "No source-side fact probes" if metric == "fact_recovery"
                else "No eligible objects"
            ) if not expected else None
            groups[metric] = {
                "status": status, "na_reason": na_reason, "expected": expected, "done": done,
                "unassessed": expected - done, "statuses": dict(counts), "labels": dict(labels),
                "numerator": None if metric == "entity_typing" else success, "denominator": expected,
                "rate": partial if status == "complete" and metric != "relation_granularity" else None,
                "partial_rate_judged_only": partial if metric != "relation_granularity" else None,
                "aggregation": "entity_macro" if metric == "entity_typing" else "sample_fraction",
                "sampled_entities": sampled if metric in {"entity_typing", "entity_description"} else None,
                "field_absent": missing_fields,
                "atomic": dict(atoms), "finest_supported_type": dict(levels),
                "whole_support_rate": _ratio(success, expected) if done == expected else None,
            }
        correct = {keys[t["id"]]["document_id"] + "\0" + keys[t["id"]]["item_id"]: results[t["id"]]
                   for t in tasks if keys[t["id"]]["system"] == sid and t["metric"] == "assertion_correctness"}
        pair_count = 0
        for t in tasks:
            if keys[t["id"]]["system"] != sid or t["metric"] != "relation_granularity":
                continue
            r = results[t["id"]]
            c = correct[keys[t["id"]]["document_id"] + "\0" + keys[t["id"]]["item_id"]]
            if r["status"] == c["status"] == "done" and r["value"]["label"] == "L3" and c["value"]["label"] == "correct":
                pair_count += 1
        g = groups["relation_granularity"]
        joint_complete = g["status"] == groups["assertion_correctness"]["status"] == "complete"
        g["correct_l3_count"] = pair_count
        g["correct_l3_coverage"] = _ratio(pair_count, g["expected"]) if joint_complete else None
        g["correct_within_l3"] = _ratio(pair_count, g["labels"].get("L3", 0)) if joint_complete else None
        g["joint_complete"] = joint_complete
    counts = Counter(r["status"] for r in results.values())
    out = {
        "protocol": manifest["protocol"], "metric_versions": manifest["metric_versions"],
        "model": manifest["model"], "complete": counts["done"] == len(tasks),
        "total": len(tasks), "done": counts["done"], "statuses": dict(counts),
        "evaluation_scope": manifest.get("evaluation_scope", "all_selected_metrics"),
        "groups": {sid: {m: g for m, g in groups.items() if m in selected_metrics}
                   for sid, groups in grouped.items()},
        "structure": structures, "updated_at": time.time(),
        "evaluation_usage": usage_summary(run / "api", slots_path()),
        "provenance": {"input_hashes": manifest["input_hashes"],
                       "benchmark_hash": manifest["benchmark_hash"],
                       "code_hashes": manifest["code_hashes"]},
    }
    write(run / "summary.json", out)
    write(run / "case-results.json", details)
    header = f"协议：{manifest['protocol']}；模型：{manifest['model']}；有效任务 {out['done']}/{out['total']}。"
    _render(run, header, systems, grouped, structures, manifest.get("evaluation_scope"), selected_metrics)
    return out


def combine(parent, stage, out):
    """One table: the parent's other metrics plus its semantic-duplicate stage.

    Retired metrics in the parent (surface-collision splits) are dropped; no
    label is copied between metrics, and both sources stay hash-referenced.
    """
    parent, stage, out = Path(parent).resolve(), Path(stage).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError("Use a new combined output directory")
    pm, sm = read(parent / "manifest.json"), read(stage / "manifest.json")
    ps, ss = read(parent / "summary.json"), read(stage / "summary.json")
    if sm.get("evaluation_scope") != "semantic_duplicate_only":
        raise ValueError("Stage must be a semantic-duplicate run")
    if read(stage / "config.json")["parent"] != str(parent) or pm["benchmark_hash"] != sm["benchmark_hash"]:
        raise ValueError("Stage was not derived from this parent run")
    systems = read(parent / "systems.json")
    if set(systems) != set(ss["groups"]) or set(systems) != set(ps["groups"]):
        raise ValueError("Parent and stage systems differ")
    grouped = {}
    for sid in systems:
        grouped[sid] = {m: ps["groups"][sid][m] for m in protocol.METRICS if m in ps["groups"][sid]}
        grouped[sid]["semantic_duplicate"] = ss["groups"][sid]["semantic_duplicate"]
    done = sum(g["done"] for groups in grouped.values() for g in groups.values())
    total = sum(g["expected"] for groups in grouped.values() for g in groups.values())
    summary = {
        "protocol": protocol.VERSION, "model": pm["model"],
        "metric_versions": {**{m: v for m, v in pm["metric_versions"].items() if m in protocol.METRICS},
                            **sm["metric_versions"]},
        "complete": all(g["status"] != "incomplete" for groups in grouped.values() for g in groups.values()),
        "total": total, "done": done, "evaluation_scope": "combined_parent_and_semantic_stage",
        "groups": grouped, "structure": ps["structure"], "updated_at": time.time(),
        "composed_from": {
            "parent": {"run": str(parent), "protocol": pm["protocol"],
                       "summary_sha256": sha(parent / "summary.json"),
                       "dropped_retired_metrics": sorted(set(ps["groups"][next(iter(systems))]) - set(protocol.METRICS))},
            "stage": {"run": str(stage), "protocol": sm["protocol"], "summary_sha256": sha(stage / "summary.json")},
        },
    }
    out.mkdir(parents=True)
    write(out / "summary.json", summary)
    header = (f"协议：{protocol.VERSION}；模型：{pm['model']}；有效任务 {done}/{total}。"
              f"语义重复来自单独阶段（{sm['metric_versions']['semantic_duplicate']}），"
              f"其余指标来自父运行（{pm['protocol']}，已退役的实体拆分不列入）。")
    _render(out, header, systems, grouped, ps["structure"], None, protocol.METRICS)
    return summary


def _render(target, header, systems, grouped, structures, scope, selected):
    rows = []

    def pct(value):
        return (f"{value:.4%}" if 0 < value < 0.00005 else f"{value:.2%}") if value is not None else "N/A"

    def group_cell(sid, metric):
        g = grouped[sid][metric]
        if g["status"] == "not_applicable":
            return "N/A"
        if g["status"] != "complete":
            return f"未完成（{g['done']}/{g['expected']}）"
        if g["aggregation"] == "entity_macro":
            return f"{pct(g['rate'])}（{g['done']}实体宏平均）"
        return f"{pct(g['rate'])}（{g['numerator']}/{g['denominator']}）"

    def add(title, fn):
        rows.append([title] + [fn(sid) for sid in systems])

    def label_fraction(sid, metric, label):
        g = grouped[sid][metric]
        return pct(_ratio(g["labels"].get(label, 0), g["expected"])) if g["status"] == "complete" else group_cell(sid, metric)

    add(protocol.METRICS["assertion_correctness"], lambda s: group_cell(s, "assertion_correctness"))
    for label, name in (("incorrect", "完整断言错误率"), ("uncertain", "完整断言不确定率")):
        add(name, lambda s, label=label: label_fraction(s, "assertion_correctness", label))
    for level in ("L1", "L2", "L3", "uncertain"):
        add("关系粒度 " + level, lambda s, level=level: label_fraction(s, "relation_granularity", level))

    def joint_cell(sid, field):
        g = grouped[sid]["relation_granularity"]
        if not g["expected"]:
            return "N/A"
        return pct(g[field]) if g["joint_complete"] else "未完成"
    add("具体且正确覆盖（L3且正确/全部断言）", lambda s: joint_cell(s, "correct_l3_coverage"))
    add("L3 内完整断言正确率", lambda s: joint_cell(s, "correct_within_l3"))
    for metric in ("entity_correctness", "entity_evidence", "entity_typing"):
        add(protocol.METRICS[metric], lambda s, m=metric: group_cell(s, m))
    for level in ("L1", "L2", "L3", "none"):
        add("最具体正确类型 " + level, lambda s, level=level:
            str(grouped[s]["entity_typing"]["finest_supported_type"].get(level, 0))
            if grouped[s]["entity_typing"]["status"] == "complete" else group_cell(s, "entity_typing"))
    for levels, name in ((("L2", "L3"), "正确且 L2/L3 类型覆盖"), (("L3",), "正确且 L3 类型覆盖")):
        add(name, lambda s, levels=levels: pct(_ratio(
            sum(grouped[s]["entity_typing"]["finest_supported_type"].get(l, 0) for l in levels),
            grouped[s]["entity_typing"]["sampled_entities"]))
            if grouped[s]["entity_typing"]["status"] == "complete" else group_cell(s, "entity_typing"))
    add("抽样实体无类型字段数", lambda s: str(grouped[s]["entity_typing"]["field_absent"]))
    add("抽样实体无描述字段数", lambda s: str(grouped[s]["entity_description"]["field_absent"]))
    add(protocol.METRICS["entity_description"], lambda s: group_cell(s, "entity_description"))
    for label, title in (("not_supported", "整段描述不支持率"), ("uncertain", "整段描述不确定率")):
        add(title, lambda s, label=label: label_fraction(s, "entity_description", label))
    add(protocol.METRICS["alias_identity"], lambda s: group_cell(s, "alias_identity"))
    add("语义重复率（越低越好）", lambda s: group_cell(s, "semantic_duplicate"))
    add("语义重复不确定率", lambda s: pct(grouped[s]["semantic_duplicate"]["uncertain_rate"])
        if grouped[s]["semantic_duplicate"]["status"] == "complete" else group_cell(s, "semantic_duplicate"))
    add("语义重复排除的超大实体数", lambda s: str(grouped[s]["semantic_duplicate"]["pool_excluded"])
        if grouped[s]["semantic_duplicate"]["status"] != "not_applicable" else "N/A")
    add(protocol.METRICS["fact_recovery"], lambda s: group_cell(s, "fact_recovery"))
    for field, title in (("entity_count", "图实体数"), ("assertion_count", "图断言数"),
                         ("quality_assertion_count", "语义评测候选断言数"), ("alias_count", "别名条目数")):
        add(title, lambda s, f=field: str(structures[s][f]))
    for field, title in (("entity_citation_presence", "实体引用存在率"),
                         ("assertion_citation_presence", "断言引用存在率"),
                         ("isolated_entity_rate", "孤立实体率"), ("largest_component_ratio", "最大连通分量占比")):
        add(title, lambda s, f=field: pct(structures[s][f]))
    for field, title in (("types", "原生类型字段覆盖"), ("definition", "原生描述字段覆盖"),
                         ("aliases", "原生别名字段覆盖")):
        add(title, lambda s, f=field: f"{structures[s]['field_counts'][f]}/{structures[s]['entity_count']}")
    for field, title in (("input_tokens_million", "构图输入 Token（million）"),
                         ("output_tokens_million", "构图输出 Token（million）"),
                         ("total_tokens_million", "构图总 Token（million）")):
        add(title, lambda s, f=field: "N/A" if structures[s]["construction"][f] is None
            else f"{structures[s]['construction'][f]:.6f}")
    headers = ["指标"] + [systems[s]["name"] for s in systems]
    if scope in SCOPE_ROWS:
        rows = [r for r in rows if r[0].startswith(SCOPE_ROWS[scope])]
    escape = lambda x: str(x).replace("|", r"\|").replace("\n", " ")
    lines = [
        "# 图谱评测结果", "", header,
        "任务未完成时不发布最终得分。N/A 的具体原因、各项分母、语义不确定与技术状态见 summary.json。",
        "", "|" + "|".join(map(escape, headers)) + "|",
        "|" + "|".join(["---"] + ["---:"] * len(systems)) + "|",
    ]
    lines.extend("|" + "|".join(map(escape, row)) + "|" for row in rows)
    lines += [
        "", "## 判定覆盖与不确定", "",
        "|方法|指标|已判/可评|语义不确定|技术失败/未评|N/A 原因|",
        "|---|---|---:|---:|---:|---|",
    ]
    for sid, groups in grouped.items():
        for metric, g in groups.items():
            if metric not in selected:
                continue
            lines.append("|" + "|".join(map(escape, [systems[sid]["name"], protocol.METRICS[metric],
                f"{g['done']}/{g['expected']}", g["labels"].get("uncertain", 0),
                g["unassessed"], g["na_reason"] or ""])) + "|")
    lines += [
        "", "## 口径", "",
        "- 类型为实体内部通过标签比例的宏平均；描述对整段判支持/不支持/不确定，分别占全部可评描述样本的比例。不确定保留在分母。缺原生字段不补造，单列字段覆盖。",
        "- 类型粒度只统计正确标签，每实体取最具体正确类型；覆盖分母是全部抽样实体。无正确类型与无类型字段分开。",
        "- 关系粒度读取完整原生断言（含自然语言描述），与正确性独立。",
        "- 实体正确性使用提交引用及左右各一段；实体引用、类型与描述只使用完整提交来源；断言使用引用所在完整小节。",
        "- 完整事实覆盖为参考指标：只读 BM25 Top10 图候选，不能用目标事实或原文为图补信息；同时受图谱覆盖与检索召回影响，未通过不一定表示图谱缺少该知识，不是全书召回率，不单独用于判断方法优劣。",
        "- 别名展示实体提交的全部引用原文，不截断；原文是依据之一，可结合可靠通用知识，书中所指优先。",
        "- 语义重复沿用实体样本：评测方写等价叫法，在全图实体名与别名中检索前30个候选并宽松初筛，冻结后由裁判逐对从严判定（含义严格相同才算同指），裁判看双方原样引用原文。检索可能漏掉重复，结果是下限，越低越好；引用原文超过170KB的超大实体不进入样本和候选池，会低估这些实体涉及的重复。已判/可评按初筛留下的实体对计，语义不确定按实体计。",
        "- 构图 Token 与本次评测调用用量分开；无构图记录记 N/A。",
        "- 各图独立抽样，不是同实体配对实验；模型判断未经独立人工金标准校准，不据细小差距断言排名。",
        "- 类型标签绑定属于新接口版本，其他迁移规则见 metric_versions；不同版本的历史结果不自动混合。",
        "", "## 输入范围", "",
    ]
    for sid in systems:
        lines.append(f"- {escape(systems[sid]['name'])}：{escape(systems[sid]['scope_note'])}")
    if scope == "entity_description_only":
        lines.append("\n本轮只重评整段描述支持，其余指标不更新；未复用历史分段判定作为新标签。")
    if scope == "semantic_duplicate_only":
        lines.append("\n本轮只评语义重复，沿用父运行的实体样本，其余指标不更新。")
    target = Path(target)
    (target / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    (target / "comparison.csv").write_text(buffer.getvalue(), encoding="utf-8-sig")
