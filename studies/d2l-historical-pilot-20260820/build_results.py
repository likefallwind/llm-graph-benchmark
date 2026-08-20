from __future__ import annotations

import hashlib
import json
from pathlib import Path

from llm_graph_benchmark.aggregation import aggregate_judgments


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JUDGE_ID = "codex-source-grounded-self-eval-v1"

SAMPLE_RUNS = {
    "llm-knowledge-graph-exact27": ROOT / "outputs/d2l-exact27-pilot",
    "llm-knowledge-graph-fresh200": ROOT / "outputs/d2l-fresh200-pilot",
}
FACT_RUNS = {
    "llm-knowledge-graph-exact27": ROOT / "outputs/d2l-exact27-frozen48",
    "llm-knowledge-graph-fresh200": ROOT / "outputs/d2l-fresh200-frozen48",
}

ASSERTION_FAILURES = {
    "t_189ad9865b3832834301": (
        "证据只定义向量元素记号，未支持“向量符号约定采用标量符号约定”这一有向关系。"
    ),
    "t_95137508c269b025baf2": (
        "证据只说代码散见于博客和 GitHub，不能推出 AlexNet 的实现具体由 GitHub 托管。"
    ),
    "t_b6d1b58ccb385917a09f": (
        "证据只说代码散见于博客和 GitHub，不能推出 LeNet 的实现具体由 GitHub 托管。"
    ),
    "t_3422370a460c4d4a5a19": (
        "证据说明事件 A 的概率记作 P(A)，不支持“概率以随机事件为记号对象”的关系方向。"
    ),
}

FACT_LABELS = {
    "t_49f8fd3935ac6d998e2b": (
        "fail",
        "候选只零散涉及数据、模型、目标函数和优化器，未恢复四者共同构成核心组件的完整事实。",
    ),
    "t_27e4039c8e1d85d93471": (
        "pass",
        "候选明确恢复框架张量的 GPU/自动微分能力及 NumPy 仅支持 CPU 的对比。",
    ),
    "t_2a99f2c3b3e14099f683": (
        "fail",
        "候选只有一般线性模型关系，未恢复正负权重决定输出单调方向的约束。",
    ),
    "t_628809006750a4a82cbb": (
        "pass",
        "候选完整恢复计算图跟踪操作组合并沿图反向传播梯度。",
    ),
    "t_887f30a52fc8b43eb293": (
        "fail",
        "候选提到若干角色，但未完整表达数据、模型、目标函数和算法这四个核心组件。",
    ),
    "t_8c51a1e7bbf09685a181": (
        "fail",
        "候选表达 MNIST 被使用且 Fashion-MNIST 更复杂，但缺少 MNIST 作为基准过于简单这一关键原因。",
    ),
    "t_c538fadce57400d26657": (
        "fail",
        "候选只恢复线性回归的线性假设，未恢复回归作为自变量与因变量关系建模方法的一般定义。",
    ),
    "t_df1bd349eb03a9942aad": (
        "pass",
        "候选明确区分回归预测数值与分类预测所属类别。",
    ),
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def sample_judgments(tasks: list[dict]) -> list[dict]:
    rows = []
    for task in tasks:
        task_id = task["task_id"]
        kind = task["kind"]
        if task_id in ASSERTION_FAILURES:
            label = "fail"
            reason = ASSERTION_FAILURES[task_id]
        elif kind == "entity_admission":
            label = "pass"
            reason = "该对象在证据中被明确指代或定义，具有稳定名称和可复用的知识含义。"
        else:
            label = "pass"
            reason = "证据直接支持完整有向关系，任务中的极性与限定范围未超出证据。"
        rows.append(
            {
                "task_id": task_id,
                "judge_id": JUDGE_ID,
                "label": label,
                "confidence": 0.95,
                "reason": reason,
            }
        )
    return rows


def fact_judgments(tasks: list[dict]) -> list[dict]:
    task_ids = {task["task_id"] for task in tasks}
    missing = task_ids - FACT_LABELS.keys()
    extra = FACT_LABELS.keys() - task_ids
    if missing or extra:
        raise ValueError(f"fact judgment/task mismatch: missing={missing}, extra={extra}")
    return [
        {
            "task_id": task["task_id"],
            "judge_id": JUDGE_ID,
            "label": FACT_LABELS[task["task_id"]][0],
            "confidence": 0.95,
            "reason": FACT_LABELS[task["task_id"]][1],
        }
        for task in tasks
    ]


def rate(result: dict) -> str:
    interval = result["pass_rate_95ci"]
    return f'{result["pass"]}/{result["decided"]} ({result["pass_rate"]:.1%}; 95% CI {interval[0]:.1%}–{interval[1]:.1%})'


def main() -> None:
    sample_tasks: list[dict] = []
    sample_keys: list[dict] = []
    fact_tasks: list[dict] = []
    fact_keys: list[dict] = []
    inputs: dict[str, str] = {}

    for system_id, run in SAMPLE_RUNS.items():
        for name in ("tasks.jsonl", "task-key.jsonl", "submission.json", "metrics.json"):
            inputs[f"{system_id}/sample/{name}"] = sha256(run / name)
        sample_tasks.extend(read_jsonl(run / "tasks.jsonl"))
        sample_keys.extend(read_jsonl(run / "task-key.jsonl"))

    for system_id, run in FACT_RUNS.items():
        for name in (
            "probe-tasks-lexical.jsonl",
            "probe-task-key-lexical.jsonl",
            "retrieval-lexical.jsonl",
            "submission.json",
        ):
            inputs[f"{system_id}/fact/{name}"] = sha256(run / name)
        fact_tasks.extend(read_jsonl(run / "probe-tasks-lexical.jsonl"))
        fact_keys.extend(read_jsonl(run / "probe-task-key-lexical.jsonl"))

    sampled_judgments = sample_judgments(sample_tasks)
    facts_judgments = fact_judgments(fact_tasks)
    sampled_metrics = aggregate_judgments(sample_keys, sampled_judgments)
    fact_metrics = aggregate_judgments(fact_keys, facts_judgments)
    structural = {
        system_id: json.loads((run / "metrics.json").read_text(encoding="utf-8"))
        for system_id, run in SAMPLE_RUNS.items()
    }

    write_jsonl(HERE / "sample-judgments.jsonl", sampled_judgments)
    write_jsonl(HERE / "fact-judgments.jsonl", facts_judgments)
    write_json(HERE / "sample-metrics.json", sampled_metrics)
    write_json(HERE / "fact-metrics.json", fact_metrics)
    write_json(HERE / "structural-metrics.json", structural)
    write_json(
        HERE / "manifest.json",
        {
            "schema_version": "1.0",
            "study_id": "d2l-historical-pilot-20260820",
            "judge_id": JUDGE_ID,
            "sample_seed": 20260820,
            "sample_per_system": {"entity_admission": 30, "assertion_grounding": 30},
            "retriever": "char-ngram-bm25-v1(top_k=10,k1=1.2,b=0.75)",
            "fact_probe_set": "d2l-zh-facts-v1",
            "fact_probe_set_sha256": sha256(ROOT / "examples/d2l-book-v1/fact_probes.jsonl"),
            "inputs": inputs,
        },
    )

    exact_s = sampled_metrics["systems"]["llm-knowledge-graph-exact27"]
    fresh_s = sampled_metrics["systems"]["llm-knowledge-graph-fresh200"]
    exact_f = fact_metrics["systems"]["llm-knowledge-graph-exact27"]["fact_recovery"]
    fresh_f = fact_metrics["systems"]["llm-knowledge-graph-fresh200"]["fact_recovery"]
    exact_m = structural["llm-knowledge-graph-exact27"]["summary"]
    fresh_m = structural["llm-knowledge-graph-fresh200"]["summary"]

    report = f"""# D2L 历史图谱快照评测（pilot）

## 结论

两份历史快照表现出相似的模式：抽出的 Entity 基本都值得进入图谱，Assertion 的原文
支撑率也很高；当前最明显的短板是**事实完整恢复**，而不是“图里多数内容是错的”。

| 快照 | 已处理 chunk | Entity admission | Assertion grounding | Fact recovery（当前覆盖范围） |
|---|---:|---:|---:|---:|
| exact27 | 27 | {rate(exact_s['entity_admission'])} | {rate(exact_s['assertion_grounding'])} | {rate(exact_f)} |
| fresh200 | 200 | {rate(fresh_s['entity_admission'])} | {rate(fresh_s['assertion_grounding'])} | {rate(fresh_f)} |

`exact27` 只覆盖 48 条冻结探针中的 1 条，`fresh200` 只覆盖 7 条，因此两者的 fact recovery
分母不同，**不能把 0/1 与 3/7 当作严格的系统间排名**。它们只能评价各快照已处理范围。

## 结构与规模

| 快照 | Entity | Assertion | Entity evidence | Assertion evidence | 孤立 Entity 比例 | 表面重复组 |
|---|---:|---:|---:|---:|---:|---:|
| exact27 | {exact_m['entity_count']} | {exact_m['assertion_count']} | {exact_m['entity_evidence_coverage']:.0%} | {exact_m['assertion_evidence_coverage']:.0%} | {exact_m['isolated_entity_rate']:.1%} | {exact_m['surface_duplicate_group_count']} |
| fresh200 | {fresh_m['entity_count']} | {fresh_m['assertion_count']} | {fresh_m['entity_evidence_coverage']:.0%} | {fresh_m['assertion_evidence_coverage']:.0%} | {fresh_m['isolated_entity_rate']:.1%} | {fresh_m['surface_duplicate_group_count']} |

规模不是质量分数。fresh200 从 27 增长到 200 个 chunk 后，Entity/Assertion 数量显著增长，
证据覆盖仍为 100%，盲样本 Assertion grounding 没有随规模下降。

## 主要错误

- exact27 的 Assertion 错误包括：从符号表构造出不存在的“记法采用”关系，以及把“代码散见于博客
  和 GitHub”过度投射成 GitHub 分别托管 LeNet、AlexNet。
- fresh200 的 Assertion 错误是关系方向失真：原文的 `P(A)` 表示事件 A 的概率，不等于“概率以
  随机事件为记号”。
- fresh200 的 4 个 fact recovery 失败分别是：四个机器学习核心组件只恢复了一部分、线性模型的
  正负权重单调方向缺失、MNIST“过于简单”的选择理由缺失、回归的一般定义缺失。
- Entity admission 并不等于类型准确率。盲样本中可见 LaTeX/GitHub、TensorFlow Variable、
  对称矩阵等对象带有可疑的额外类型；这应在下一版增加独立 `entity_typing` 指标，不能事后混入
  已冻结的 admission 尺度。

## 协议

- 输入：同一本 D2L 中文版，源文本 SHA-256
  `9b57a1cead18be493ddbf26a62d09031a85c3a7261306648c1a5c2fc93a68e76`。
- 精确性侧：每个快照以 seed `20260820` 固定抽取 30 个 Entity 和 30 个 Assertion，系统身份
  不出现在公开任务中；本次 120/120 均已裁判。
- 完整性侧：使用独立从原文冻结的 48 条分层 fact probes；只在快照已处理 passage 范围内出题。
- 检索：统一使用 `char-ngram-bm25-v1(top_k=10,k1=1.2,b=0.75)`，只索引图谱 Assertion 的
  subject、predicate、object、text、scope，不读取原文 passage 或 evidence。
- 内部 LLM checker 是被评系统的一部分；上述盲评是统一的外部结果裁判，没有重复调用抽取 API。

## 可信度边界

这是**同一强模型完成策展与裁判的自评 pilot**，没有独立人类校准，不能宣称人工金标准。
Wilson 区间已报告，但小样本 fact recovery 区间很宽。两份数据库也只是书籍前 27/200 个 chunk 的
历史快照，不是全书最终分数。事实恢复分数同时受图谱和统一检索器影响；后续应在人类校准小样本上
验证检索器，并加入其他提取系统后再做正式横向比较。

本轮结果足以验证 benchmark 可以端到端评价真实历史图谱，也给出明确诊断：优先提升跨 Assertion
组合、条件/理由保留和一般定义覆盖；不应只继续优化单条 Assertion 的证据支撑率。
"""
    (HERE / "REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
