from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from llm_graph_benchmark.aggregation import aggregate_judgments


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / "outputs/d2l-full1105-vnext-20260826"
EVALUATION = RUN / "evaluation"
JUDGE_ID = "codex-source-grounded-fullbook-v1"
SYSTEM_ID = "llm-knowledge-graph-full1105-vnext"

FAILURES = {
    # Sampled entity/assertion quality.
    "t_043b5d84bba74806d2b6": "关系端点不当：多层感知机用于计算注意力权重，不能据此把它作为权重的有向结果端点。",
    "t_1361cc30f579ab52d48c": "nn.CrossEntropyLoss 被额外标成平方误差损失，类型不相容。",
    "t_4b44dd149d6b47f49432": "BERT 表示是模型输出/数据表示，不是模型本身。",
    "t_5df8ac0bff8340b40ee9": "自定义初始化方法被额外标成正则化技术和训练现象。",
    "t_d5f3f673579ea40d5ab5": "优化算法被混入损失函数、正则化、注意力机制和训练现象等不相容类型。",
    "t_8859e4df60f1bc52a348": "隐藏单元是结构组件；隐藏单元数量可以是超参数，但单元本身不是超参数。",
    "t_7536efc924093c030345": "证据只把符号列为指示函数，没有给出真取 1、假取 0 的定义。",
    "t_2dc203d2b99890d327d0": "证据定义的是向量空间中的凸集，不能支持所提交的向量空间定义。",
    "t_642e01a04bddd43550b8": "证据只实例化 Seq2SeqDecoder，没有支持其拼接上下文、循环层和逐词元预测机制。",
    # Identity review.
    "t_d1ee54ec8a272016f7a7": "burst read 是特定长连续传输方式，不应作为一般 sequential access 的全局同义词。",
    "t_ff83d1b6635521587ddc": "kaggle_cifar10 是章节交叉引用标识，不是该比赛章节实体的自然语言别名。",
    "t_87f35bace96632898afe": "单样本随机梯度下降与此处的随机梯度下降指同一算法，拆分造成重复。",
    "t_d455496ab168f38e6395": "本书语境中的词向量与词嵌入都指词的向量表示，当前拆分造成近重复实体。",
    # Frozen fact recovery probes.
    "t_09737677559f0ea480c9": "只恢复了初始化或激活的零散事实，未恢复二者影响收敛及梯度爆炸/消失的完整机制。",
    "t_0c1108e31ba1adacaf79": "未恢复神经网络块可代表整模并可递归组合的完整层级事实。",
    "t_1712d888b8c4d2246008": "未恢复通过对目标取负把最大化转换成最小化的一般规则。",
    "t_36b327710d3b81dec561": "候选只给出一般形状影响因素，没有直接恢复无填充、步幅 1 的目标公式。",
    "t_51304dc8dd4e1b9558a4": "只恢复查询和键同源，遗漏值也来自同一组输入。",
    "t_8b9cb0148317accc1bae": "未恢复完整批量的数据效率与单样本向量化效率之间的明确权衡。",
    "t_a7e7d4fa09bbfb9af6e3": "候选无法列出数据、模型、目标函数和算法四个核心组件。",
    "t_e6a19dc2c78b8f0ae706": "恢复了展开与链式法则，但遗漏长序列的时间和内存代价。",
    "t_ea0bc235ac93d89d73af": "恢复了泄漏平均机制，但遗漏将速率调度与按坐标自适应分离这一目的。",
    "t_eb62b9aa68971140e131": "恢复了全量微调，但遗漏额外全连接层及其参数从零学习。",
    "t_eeddf05fa0834182a204": "只恢复 Adam 的个别成分，未恢复四类优化技术的组合。",
    "t_f8de37c35de937312555": "候选没有恢复回归的一般定义。",
    # Frozen book QA probes.
    "t_02fb702fed570c3ffb41": "候选提到自动微分和反向传播，但遗漏计算图如何跟踪数据与操作组合。",
    "t_2c41b338cb9e99ec7cb5": "只覆盖自动微分，遗漏 GPU 加速及 NumPy 仅支持 CPU 的对比。",
    "t_3e597a6733c67361f660": "只描述负采样本身，未回答完整 softmax 的大词表成本和分层 softmax。",
    "t_608149111b82dd101ee9": "候选未完整回答新增全连接层、从零学习新增参数、微调全部 BERT 参数三部分。",
    "t_6b89c3ad20a94549e1c2": "候选与 GRU/LSTM 的简化、效果和速度对比无关。",
    "t_747a6bdbcc2c7a854e30": "候选提到小批量算法，却没有恢复数据效率与向量化效率的权衡。",
    "t_8c7f7438b64b3ff63e68": "候选没有给出回归的一般定义。",
    "t_d2815f695b2da9149cd4": "候选没有给出目标卷积输出形状公式。",
    "t_d519dc90786e0bcd8816": "候选没有解释 MNIST 过于简单及 Fashion-MNIST 更复杂。",
    "t_dccdb52ca447363d23f6": "只恢复分词和建词表，遗漏加载、转索引及完整步骤顺序。",
    "t_ea9b0b39063abe7c5a84": "候选没有完整建立 word2vec 和 GloVe 均使用上下文无关表示的因果链。",
    "t_f2a94b97acec3baf445a": "候选无法列出机器学习问题的四个核心组件。",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def pass_reason(kind: str) -> str:
    return {
        "entity_admission": "证据明确指代该对象，名称稳定且具有可复用的知识含义。",
        "entity_typing": "提交的全部类型均与实体及来源语境相容。",
        "entity_definition_grounding": "定义的实质内容可由证据支持，没有关键外加事实。",
        "assertion_grounding": "证据支持完整有向关系、极性和限定范围。",
        "alias_identity": "别名与实体同指，不是相关项、上下位项或局部引用标识。",
        "identity_split": "共享表面词存在歧义，两实体定义不同，保持分开合理。",
        "fact_recovery": "候选图断言足以恢复冻结事实，且没有依赖证据外补充。",
        "book_qa": "候选图断言足以独立回答问题的全部关键部分。",
    }[kind]


def build_judgments(tasks: list[dict]) -> list[dict]:
    task_ids = {row["task_id"] for row in tasks}
    extra = set(FAILURES) - task_ids
    if extra:
        raise ValueError(f"failure mappings reference unknown tasks: {sorted(extra)}")
    rows = []
    for task in tasks:
        task_id = task["task_id"]
        failed = task_id in FAILURES
        rows.append(
            {
                "task_id": task_id,
                "judge_id": JUDGE_ID,
                "label": "fail" if failed else "pass",
                "confidence": 0.9 if failed else 0.95,
                "reason": FAILURES.get(task_id, pass_reason(task["kind"])),
            }
        )
    return rows


def rate(metrics: dict, kind: str) -> str:
    row = metrics["systems"][SYSTEM_ID][kind]
    low, high = row["pass_rate_95ci"]
    return f'{row["pass"]}/{row["decided"]} ({row["pass_rate"]:.1%}; 95% CI {low:.1%}–{high:.1%})'


def observed_span(database: Path) -> dict:
    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT MIN(updated_at), MAX(updated_at), COUNT(DISTINCT chunk_index) "
            "FROM source_progress WHERE status = 'done'"
        ).fetchone()
    finally:
        connection.close()
    seconds = (datetime.fromisoformat(row[1]) - datetime.fromisoformat(row[0])).total_seconds()
    return {
        "first_done_update": row[0],
        "last_done_update": row[1],
        "observed_wall_span_seconds": seconds,
        "observed_wall_span_hours": round(seconds / 3600, 6),
        "done_chunks": row[2],
        "active_runtime": None,
        "input_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
        "limitation": "The timestamp span includes retries, pauses and backoff; it is not active runtime.",
    }


def main() -> None:
    tasks = read_jsonl(EVALUATION / "all-tasks.jsonl")
    keys = read_jsonl(EVALUATION / "all-task-key.jsonl")
    if len(tasks) != 252 or len(keys) != 252:
        raise ValueError(f"expected 252 tasks and keys, got {len(tasks)} and {len(keys)}")
    judgments = build_judgments(tasks)
    metrics = aggregate_judgments(keys, judgments)
    structural = read_json(EVALUATION / "structural-metrics.json")
    adapter = read_json(RUN / "adapter-report.json")
    database = Path(adapter["database"])

    write_jsonl(HERE / "judgments.jsonl", judgments)
    write_json(HERE / "judged-metrics.json", metrics)
    write_json(HERE / "structural-metrics.json", structural)
    write_json(HERE / "adapter-report.json", adapter)
    write_json(HERE / "efficiency-metrics.json", observed_span(database))
    write_json(
        HERE / "manifest.json",
        {
            "schema_version": "1.0",
            "study_id": "d2l-fullbook-vnext-20260826",
            "system_id": SYSTEM_ID,
            "primary_judge": JUDGE_ID,
            "judge_scope": "single source-grounded Codex pass over every generated task",
            "independent_judge_calibration": "unavailable",
            "human_calibration": "unavailable-no-human-labels",
            "sample_seed": 20260820,
            "sample": {
                "entity_admission": 30,
                "entity_typing": 30,
                "entity_definition_grounding": 30,
                "assertion_grounding": 30,
                "alias_identity": 30,
                "identity_split": 30,
                "fact_recovery": 48,
                "book_qa": 24,
            },
            "retriever": "char-ngram-bm25-v1(top_k=10,k1=1.2,b=0.75)",
            "source_database": str(database),
            "source_database_hash": adapter.get("source_database_hash")
            or read_json(RUN / "submission.json")["metadata"]["source_database_hash"],
            "source_revision": "1aed294b7b5dbb6c1e779d000d2fdb2b1ace21d4",
            "worktree_patch_sha256": "sha256:23ce929894845b64cbf32e7a84047ded51dacdffaab704cf0238f90f25326123",
            "input_hashes": {
                "submission": sha256(RUN / "submission.json"),
                "all_tasks": sha256(EVALUATION / "all-tasks.jsonl"),
                "all_task_key": sha256(EVALUATION / "all-task-key.jsonl"),
                "fact_probes": sha256(ROOT / "examples/d2l-book-v1/fact_probes.jsonl"),
                "qa_probes": sha256(ROOT / "examples/d2l-book-v1/qa_probes.jsonl"),
            },
        },
    )

    summary = structural["summary"]
    integrity = adapter["integrity"]
    report = f"""# D2L 全书 vNext 图谱评测

## 结论

这份全书图谱已完成 1105/1105 个 chunk，SQLite `quick_check` 通过，且 Benchmark 与 Submission
schema 均通过验证。它不是只看内部 checker 的自评：本轮使用冻结的 48 条事实和 24 道 Book QA，
并对 180 个抽样实体、关系和身份任务逐条做来源证据盲评，共 252 个任务。

| 维度 | 结果 |
|---|---:|
| Entity admission | {rate(metrics, 'entity_admission')} |
| Entity typing | {rate(metrics, 'entity_typing')} |
| Entity definition grounding | {rate(metrics, 'entity_definition_grounding')} |
| Assertion grounding | {rate(metrics, 'assertion_grounding')} |
| Alias identity | {rate(metrics, 'alias_identity')} |
| Identity split correctness | {rate(metrics, 'identity_split')} |
| Fact recovery | {rate(metrics, 'fact_recovery')} |
| Book QA | {rate(metrics, 'book_qa')} |

核心判断：单条 Assertion 的证据化很强，实体准入与身份解析也可靠；但复合事实的完整恢复仍是主要
瓶颈。失败多发生在遗漏对比条件、动机、代价或多步骤机制，而不是凭空制造完全错误的事实。

## 结构与身份

- Entity: {summary['entity_count']}；Assertion: {summary['assertion_count']}；Source Passage: {integrity['counts']['source_passages']}。
- Entity/Assertion 证据覆盖率均为 100%。
- 孤立 Entity: {structural['documents'][0]['isolated_entity_count']}（{summary['isolated_entity_rate']:.1%}）。
- 最大连通分量覆盖 {structural['documents'][0]['largest_component_ratio']:.1%} 的 Entity，共 {structural['documents'][0]['component_count']} 个分量。
- 谓词有 {summary['unique_predicate_count_sum']} 种，说明开放谓词仍高度碎片化。
- 75 个模糊表面词组涉及 137 个 Entity；规范名表面重复组为 0。

类型错误集中在“多标签越多越好”的过度标注，例如把交叉熵损失标成平方误差损失、把 BERT 表示
标成模型、把优化算法同时标成损失函数/正则化/注意力机制。定义错误则集中于把常识或实现细节补进
证据没有说到的定义。

## 运行完整性与血缘

- 数据库：`{database}`（只读评测，未修改来源仓库）。
- schema v{integrity['schema_version']}，模型 `{integrity['models'][0]}`，进度
  `{integrity['progress']['counts']['done']}/{integrity['progress']['total']}`，chunk 范围
  {integrity['progress']['min_chunk']}–{integrity['progress']['max_chunk']}。
- 来源提交：`1aed294b7b5dbb6c1e779d000d2fdb2b1ace21d4`；运行时 worktree patch SHA-256
  `23ce929894845b64cbf32e7a84047ded51dacdffaab704cf0238f90f25326123`。
- Claim observation: {integrity['claim_observations']['observations']}；支持 {integrity['claim_observations']['supports']}；
  insufficient {integrity['claim_observations']['insufficient']}；contradicts {integrity['claim_observations']['contradicts']}；
  materialized {integrity['claim_observations']['materialized']}。
- Entity observation: {integrity['entity_observations']['observations']}；unresolved 0。

active runtime、token 与成本没有被运行产物可靠记录，因此明确记为 unavailable。数据库更新时间跨度包含
失败重试、暂停和退避，不能冒充真实运行耗时。

## 可信度边界

本轮逐项判定由同一 Codex 做一次来源证据审查，没有调用外部模型，也没有使用图数据库内部 judge 的
标签作为最终答案。没有独立模型复审或人工校准，所以置信区间只表达抽样不确定性，不包含裁判偏差；
该结果适合作为工程诊断和后续回归基线，不应包装成已完成人类标注验证的论文结论。

## 复现

```bash
.venv/bin/python -m llm_graph_benchmark adapt-llmkg-sqlite \\
  --db ../llm-knowledge-graph/tmp/d2l-full1105-c6-20260817-193600.db \\
  --out-dir outputs/d2l-full1105-vnext-20260826 \\
  --benchmark-id d2l-fullbook-v1 \\
  --system-id llm-knowledge-graph-full1105-vnext \\
  --system-name "LLM Knowledge Graph" \\
  --system-version 1aed294+scopefix-23ce92989484 \\
  --fact-probes examples/d2l-book-v1/fact_probes.jsonl \\
  --qa-probes examples/d2l-book-v1/qa_probes.jsonl \\
  --chunk-chars 8000 --overlap-chars 500

.venv/bin/python studies/d2l-open-baselines-20260820/evaluate_submission.py \\
  --benchmark outputs/d2l-full1105-vnext-20260826/benchmark.json \\
  --submission outputs/d2l-full1105-vnext-20260826/submission.json \\
  --out-dir outputs/d2l-full1105-vnext-20260826/evaluation

.venv/bin/python studies/d2l-fullbook-vnext-20260826/build_results.py
```
"""
    (HERE / "REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
