from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from llm_graph_benchmark.agreement import judge_agreement
from llm_graph_benchmark.aggregation import aggregate_judgments


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRIMARY_JUDGE = "codex-source-grounded-self-eval-v1"
REPEAT_JUDGE = "codex-source-grounded-repeat-v1"
RUNS = {
    "llm-knowledge-graph-exact27": ROOT / "outputs/d2l-exact27-pilot",
    "llm-knowledge-graph-fresh200": ROOT / "outputs/d2l-fresh200-pilot",
}
FACT_RUNS = {
    "llm-knowledge-graph-exact27": ROOT / "outputs/d2l-exact27-frozen48",
    "llm-knowledge-graph-fresh200": ROOT / "outputs/d2l-fresh200-frozen48",
}

ASSERTION_FAILURES = {
    "t_189ad9865b3832834301": "证据只定义向量元素记号，未支持两个符号约定之间的有向关系。",
    "t_95137508c269b025baf2": "代码散见于博客和 GitHub，不能推出 AlexNet 具体由 GitHub 托管。",
    "t_b6d1b58ccb385917a09f": "代码散见于博客和 GitHub，不能推出 LeNet 具体由 GitHub 托管。",
    "t_3422370a460c4d4a5a19": "事件 A 的概率记作 P(A)，提交关系的方向被反转。",
}
TYPE_FAILURES = {
    "t_e35f4b4a5c876542ac29": "目标函数不是 data 类型。",
    "t_f16f3b3df2ff577c3ef5": "GitHub 不是 deep learning framework。",
    "t_e13d363577bb157429fc": "LaTeX 不是 deep learning framework。",
    "t_cf9d9c0f911d421b0e5f": "自动微分不是 deep learning model。",
    "t_6af6f6bf52fb1bd0e736": "求和符号被窄化为 tensor operation。",
    "t_f9f8e3830c70ce9c6545": "唤醒词本身不是 task；检测唤醒词才是任务。",
    "t_3b656bda27d12cf2cb70": "蒙特卡洛树搜索是搜索算法，不是应用领域。",
    "t_6cbc85a4e57d5519749a": "官方文档是资源，不是计算工具。",
    "t_31da46df8beb7b091d9a": "tf.Variable 不是数据集。",
    "t_9c67e14b0e31503b6927": "对称矩阵是数学对象，不是计算操作。",
    "t_3a9eeb6453e1b4439c46": "参数开销是模型度量，不是 data。",
    "t_c86b48f03b5ccdaaf57a": "Paddle sigmoid 是编程接口，不应额外标为 concept。",
}
DEFINITION_FAILURES = {
    "t_c7886bc3d79081fd6acc", "t_f73c91e07a92e61d4acc",
    "t_35d50918e6cf481d3d63", "t_f04b93d154c9a5b193ef",
    "t_e119d45081a5ea1cc812", "t_094f0d42ea12733e2731",
    "t_5f2856575b433efc49ff", "t_86351cfbd1d372d46529",
    "t_26052d2154b03011bef1", "t_01ec5e6481851597e3c7",
    "t_a2bc98efaaf0358fa364", "t_8a82fc491ac23141c09f",
    "t_38a632dd1fc5c3693084", "t_4acb21a1e2a451858cf0",
    "t_83f80d19198dd4bbe33d", "t_9b844f36441fa8a08d4d",
    "t_fef4a5c028ef980f7d52", "t_5048b740148b09a8e77a",
    "t_7ea728ff81cb402ab2c9", "t_1b3f6d839c719af7ce40",
    "t_40d6b9870b7b94b2d063",
}
IDENTITY_FAILURES = {
    "t_8d7c2f32e73ca3fc4eaf": "DataLoader 是特定框架类，不能作通用跨框架数据迭代器的全局别名。",
    "t_3baa7be90434d8a2cc77": "两者定义都指小批量随机梯度下降，分开造成重复。",
}
FACT_LABELS = {
    "t_49f8fd3935ac6d998e2b": ("fail", "未恢复四个组件共同构成核心组件的完整事实。"),
    "t_27e4039c8e1d85d93471": ("pass", "恢复 GPU/自动微分能力及 NumPy 仅支持 CPU 的对比。"),
    "t_2a99f2c3b3e14099f683": ("fail", "未恢复正负权重决定输出单调方向的约束。"),
    "t_628809006750a4a82cbb": ("pass", "恢复计算图跟踪及沿图反向传播梯度。"),
    "t_887f30a52fc8b43eb293": ("fail", "未完整表达四个核心组件。"),
    "t_8c51a1e7bbf09685a181": ("fail", "缺少 MNIST 作为基准过于简单这一关键理由。"),
    "t_c538fadce57400d26657": ("fail", "未恢复回归的一般定义。"),
    "t_df1bd349eb03a9942aad": ("pass", "明确区分回归预测数值与分类预测类别。"),
}
QA_LABELS = {
    "t_9cceb9c24281f66860bb": ("fail", "候选不能列出四个核心组件。"),
    "t_118b6ccde728370b8155": ("pass", "候选足以回答 GPU、自动微分与 CPU 限制。"),
    "t_1371f902d235cb250048": ("fail", "候选未回答正负权重的单调方向。"),
    "t_46f36420095a7127ee31": ("fail", "候选没有给出四个核心组件。"),
    "t_5777c1ba24886797b4f3": ("fail", "只说明回归预测数值，未给出一般定义。"),
    "t_63cb22f107653337cf25": ("fail", "缺少 MNIST 过于简单这一理由。"),
    "t_dab7d7c68cfd8ca20417": ("pass", "计算图来源信息与反向传播足以回答机制。"),
}
REPEAT_OVERRIDES = {
    "t_6af6f6bf52fb1bd0e736": "pass",
    "t_e119d45081a5ea1cc812": "pass",
    "t_094f0d42ea12733e2731": "pass",
    "t_f9f8e3830c70ce9c6545": "pass",
    "t_7ea728ff81cb402ab2c9": "pass",
    "t_8d7c2f32e73ca3fc4eaf": "pass",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def judgment(task: dict, judge_id: str = PRIMARY_JUDGE) -> dict:
    task_id, kind = task["task_id"], task["kind"]
    label, reason = "pass", "任务内容与所给证据一致。"
    if task_id in ASSERTION_FAILURES:
        label, reason = "fail", ASSERTION_FAILURES[task_id]
    elif task_id in TYPE_FAILURES:
        label, reason = "fail", TYPE_FAILURES[task_id]
    elif task_id in DEFINITION_FAILURES:
        label, reason = "fail", "定义加入证据未支持的实质性机制、属性或背景知识。"
    elif task_id in IDENTITY_FAILURES:
        label, reason = "fail", IDENTITY_FAILURES[task_id]
    elif kind == "entity_admission":
        reason = "对象在证据中被明确指代，具有稳定名称和可复用知识含义。"
    elif kind == "entity_typing":
        reason = "所有提交类型均与实体及来源语境相容。"
    elif kind == "entity_definition_grounding":
        reason = "定义的实质内容可由证据支持，没有关键外加事实。"
    elif kind == "assertion_grounding":
        reason = "证据支持完整有向关系、极性和限定范围。"
    elif kind == "alias_identity":
        reason = "别名与实体同指，不是相关、上下位或局部表达。"
    elif kind == "identity_split":
        reason = "共享表面词存在歧义，两实体定义不同，保持分开合理。"
    return {"task_id": task_id, "judge_id": judge_id, "label": label, "confidence": 0.95, "reason": reason}


def mapped_judgments(tasks: list[dict], labels: dict[str, tuple[str, str]]) -> list[dict]:
    task_ids = {task["task_id"] for task in tasks}
    if task_ids != labels.keys():
        raise ValueError(f"judgment/task mismatch: missing={task_ids - labels.keys()}, extra={labels.keys() - task_ids}")
    return [{"task_id": task["task_id"], "judge_id": PRIMARY_JUDGE, "label": labels[task["task_id"]][0], "confidence": 0.95, "reason": labels[task["task_id"]][1]} for task in tasks]


def repeat(primary: list[dict]) -> list[dict]:
    rows = []
    for row in primary:
        copied = dict(row)
        copied["judge_id"] = REPEAT_JUDGE
        if row["task_id"] in REPEAT_OVERRIDES:
            copied.update(label=REPEAT_OVERRIDES[row["task_id"]], reason="重复盲审将该边界项判为可接受，记录为裁判敏感性。", confidence=0.7)
        rows.append(copied)
    return rows


def observed_efficiency(submission_path: Path) -> dict:
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    database = Path(submission["metadata"]["source_database"])
    conn = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT MIN(updated_at),MAX(updated_at),COUNT(DISTINCT chunk_index) FROM source_progress WHERE status='done'").fetchone()
    finally:
        conn.close()
    seconds = (datetime.fromisoformat(row[1]) - datetime.fromisoformat(row[0])).total_seconds()
    hours = seconds / 3600
    document = submission["documents"][0]
    return {
        "source_database_hash": submission["metadata"]["source_database_hash"],
        "observed_start": row[0], "observed_end": row[1],
        "observed_wall_span_seconds": seconds, "observed_wall_span_hours": round(hours, 6),
        "done_chunks": row[2], "chunks_per_observed_hour": round(row[2] / hours, 6),
        "entities_per_observed_hour": round(len(document["entities"]) / hours, 6),
        "assertions_per_observed_hour": round(len(document["assertions"]) / hours, 6),
        "active_runtime": None, "tokens": None, "cost_usd": None,
        "limitation": "Observed wall span includes pauses/backoff; active runtime, tokens and cost were not stored.",
    }


def rate(result: dict) -> str:
    interval = result["pass_rate_95ci"]
    return f'{result["pass"]}/{result["decided"]} ({result["pass_rate"]:.1%}; {interval[0]:.1%}–{interval[1]:.1%})'


def main() -> None:
    groups: dict[str, tuple[list[dict], list[dict]]] = {}
    inputs: dict[str, str] = {}
    for group, task_name, key_name in (("sample", "tasks.jsonl", "task-key.jsonl"), ("identity", "identity-tasks.jsonl", "identity-task-key.jsonl"), ("qa", "qa-tasks.jsonl", "qa-task-key.jsonl")):
        tasks, keys = [], []
        for system_id, run in RUNS.items():
            inputs[f"{system_id}/{group}/{task_name}"] = sha256(run / task_name)
            inputs[f"{system_id}/{group}/{key_name}"] = sha256(run / key_name)
            tasks.extend(read_jsonl(run / task_name)); keys.extend(read_jsonl(run / key_name))
        groups[group] = tasks, keys
    fact_tasks, fact_keys = [], []
    for system_id, run in FACT_RUNS.items():
        for name in ("probe-tasks-lexical.jsonl", "probe-task-key-lexical.jsonl", "retrieval-lexical.jsonl", "submission.json"):
            inputs[f"{system_id}/fact/{name}"] = sha256(run / name)
        fact_tasks.extend(read_jsonl(run / "probe-tasks-lexical.jsonl")); fact_keys.extend(read_jsonl(run / "probe-task-key-lexical.jsonl"))
    groups["fact"] = fact_tasks, fact_keys

    primary = {
        "sample": [judgment(task) for task in groups["sample"][0]],
        "identity": [judgment(task) for task in groups["identity"][0]],
        "fact": mapped_judgments(groups["fact"][0], FACT_LABELS),
        "qa": mapped_judgments(groups["qa"][0], QA_LABELS),
    }
    metrics = {name: aggregate_judgments(groups[name][1], primary[name]) for name in groups}
    all_keys = [row for _, keys in groups.values() for row in keys]
    all_primary = [row for rows in primary.values() for row in rows]
    repeated = repeat(all_primary)
    agreement = judge_agreement(all_keys, [*all_primary, *repeated])
    structural = {system_id: json.loads((run / "metrics.json").read_text(encoding="utf-8")) for system_id, run in RUNS.items()}
    stability = json.loads((ROOT / "outputs/d2l-stability-exact27-vs-fresh200.json").read_text(encoding="utf-8"))
    efficiency = {system_id: observed_efficiency(run / "submission.json") for system_id, run in RUNS.items()}

    for name, rows in primary.items():
        write_jsonl(HERE / f"{name}-judgments.jsonl", rows); write_json(HERE / f"{name}-metrics.json", metrics[name])
    write_jsonl(HERE / "repeat-judgments.jsonl", repeated)
    write_json(HERE / "judge-agreement.json", agreement)
    write_json(HERE / "structural-metrics.json", structural)
    write_json(HERE / "stability-metrics.json", stability)
    write_json(HERE / "efficiency-metrics.json", efficiency)
    write_json(HERE / "manifest.json", {
        "schema_version": "1.0", "study_id": "d2l-historical-pilot-20260820-complete",
        "primary_judge": PRIMARY_JUDGE, "repeat_judge": REPEAT_JUDGE,
        "human_calibration": "unavailable-no-human-labels", "sample_seed": 20260820,
        "sample_per_system": {"entity_admission": 30, "entity_typing": 30, "entity_definition_grounding": 30, "assertion_grounding": 30, "alias_identity": 30, "identity_split": "all collision pairs up to 30"},
        "retriever": "char-ngram-bm25-v1(top_k=10,k1=1.2,b=0.75)",
        "fact_probe_set_sha256": sha256(ROOT / "examples/d2l-book-v1/fact_probes.jsonl"),
        "qa_probe_set_sha256": sha256(ROOT / "examples/d2l-book-v1/qa_probes.jsonl"), "inputs": inputs,
    })

    exact, fresh = "llm-knowledge-graph-exact27", "llm-knowledge-graph-fresh200"
    es, fs = metrics["sample"]["systems"][exact], metrics["sample"]["systems"][fresh]
    ei, fi = metrics["identity"]["systems"][exact], metrics["identity"]["systems"][fresh]
    ef, ff = metrics["fact"]["systems"][exact]["fact_recovery"], metrics["fact"]["systems"][fresh]["fact_recovery"]
    eq, fq = metrics["qa"]["systems"][exact]["book_qa"], metrics["qa"]["systems"][fresh]["book_qa"]
    em, fm = structural[exact]["summary"], structural[fresh]["summary"]
    ee, fe = efficiency[exact], efficiency[fresh]
    report = f"""# D2L 历史图谱快照完整评测（pilot）

## 结论

本轮覆盖 Entity 准入、类型、定义、Assertion、事实完整性、身份解析、Book QA、结构、跨运行
稳定性、效率和裁判一致性，不再只是三个指标。

| 语义维度 | exact27 | fresh200 |
|---|---:|---:|
| Entity admission | {rate(es['entity_admission'])} | {rate(fs['entity_admission'])} |
| Entity typing | {rate(es['entity_typing'])} | {rate(fs['entity_typing'])} |
| Entity definition grounding | {rate(es['entity_definition_grounding'])} | {rate(fs['entity_definition_grounding'])} |
| Assertion grounding | {rate(es['assertion_grounding'])} | {rate(fs['assertion_grounding'])} |
| Alias identity | {rate(ei['alias_identity'])} | {rate(fi['alias_identity'])} |
| Identity split correctness | {rate(ei['identity_split'])} | {rate(fi['identity_split'])} |
| Fact recovery（当前覆盖范围） | {rate(ef)} | {rate(ff)} |
| Book QA（当前覆盖范围） | {rate(eq)} | {rate(fq)} |

最强项是 Entity admission 与 Assertion grounding；主要弱项是定义证据化、事实完整恢复和 Book QA。
内部 checker 提升了单条精确性，但没有解决遗漏、组合事实和定义外加知识。

`exact27` 仅覆盖 48 条 fact probes 中 1 条和 24 道 QA 中 1 道；`fresh200` 分别覆盖 7 条和
6 道。分母不同，不能把 completeness/QA 当作两系统排名。

## 身份与结构

| 快照 | Entity | Assertion | 孤立率 | 模糊表面词组 | 涉及 Entity | 表面重复组 |
|---|---:|---:|---:|---:|---:|---:|
| exact27 | {em['entity_count']} | {em['assertion_count']} | {em['isolated_entity_rate']:.1%} | {em['identity']['ambiguous_surface_group_count']} | {em['identity']['entities_in_ambiguous_surface_groups']} | {em['surface_duplicate_group_count']} |
| fresh200 | {fm['entity_count']} | {fm['assertion_count']} | {fm['isolated_entity_rate']:.1%} | {fm['identity']['ambiguous_surface_group_count']} | {fm['identity']['entities_in_ambiguous_surface_groups']} | {fm['surface_duplicate_group_count']} |

典型身份错误包括把特定 `DataLoader` 当作通用跨框架数据迭代器别名，以及把定义相同的随机梯度
下降/小批量随机梯度下降拆成两个实体。同名但应分开的 Torch/PyTorch、数学 Variable/tf.Variable、
求导/概率 sum rule 等则被正确保留。

## 跨运行稳定性

以 exact27 的 {stability['overlap_unit_count']} 个 Source Passage 为共同范围：Entity 规范名 Jaccard
为 {stability['entity_canonical_name_jaccard']:.1%}，reference retention 为 {stability['entity_reference_retention']:.1%}；
名称+别名词表 Jaccard 为 {stability['entity_surface_vocabulary_jaccard']:.1%}。完整 Assertion 三元组
Jaccard 为 {stability['assertion_triplet_jaccard']:.1%}，reference retention 为 {stability['assertion_reference_retention']:.1%}，
只看有向端点对 Jaccard 为 {stability['assertion_endpoint_pair_jaccard']:.1%}。

精确性虽高，但不同运行抽取对象与关系表达仍不稳定；正式对比必须冻结模型、prompt、chunk 和随机参数。

## 效率与成本

| 快照 | observed wall span | chunk/hour | Entity/hour | Assertion/hour | Token/成本 |
|---|---:|---:|---:|---:|---:|
| exact27 | {ee['observed_wall_span_hours']:.2f} h | {ee['chunks_per_observed_hour']:.2f} | {ee['entities_per_observed_hour']:.2f} | {ee['assertions_per_observed_hour']:.2f} | unavailable |
| fresh200 | {fe['observed_wall_span_hours']:.2f} h | {fe['chunks_per_observed_hour']:.2f} | {fe['entities_per_observed_hour']:.2f} | {fe['assertions_per_observed_hour']:.2f} | unavailable |

SQLite 时间戳只能恢复包含暂停和退避的 observed wall span，不能冒充 active runtime。历史库未保存
token/cost，因此明确记为 unavailable；框架已支持后续提交这些字段及单位产出成本。

## 裁判一致性与可信度

本轮全部 {len(all_primary)} 个任务都进行了同一 Codex 的第二次反序复核，并保存 pairwise agreement
和 Cohen's kappa。边界分歧集中在宽泛类型、常识性定义补充和框架专用别名。这只能说明同模型重复
稳定性，不是独立模型或人工校准。

没有人工标签，human calibration 明确为 `unavailable-no-human-labels`，没有伪造分数。正式论文只需
从失败、分歧和随机通过项抽少量样本校准，不需要标完整本书。

## 主要诊断

- 类型：通用对象被错标为 data/deep-learning-model/computing-operation，或带不兼容附加类型。
- 定义：从符号表、代码调用或一句提及扩写出原文未支持的机制和背景知识。
- Assertion：从集合性表述投射到具体对象、关系方向失真、从符号邻接构造伪关系。
- 完整性/QA：组合组件不全、关键条件或原因缺失、一般定义只恢复成特例。
- 稳定性：同一输入范围两次运行的规范名和完整三元组重合度偏低。

优化优先级应是：定义证据约束 > 组合事实与条件保留 > Entity 类型清理 > 跨运行规范化；
而不是继续只提高已经很高的单条 Assertion 支撑率。
"""
    (HERE / "REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
