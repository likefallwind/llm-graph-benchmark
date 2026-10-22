# 强化学习书：从零构图（pipeline-v3）评测

图谱：`../llm-knowledge-graph/outputs/rl-from-zero-m3-c6-20261004-pipeline-v3`（2026-10-04 至 10-07，MiniMax-M3，6 并发，324/324 块，完整性检查通过）。
只读强化学习书构图，1,268 实体、2,707 完整断言；构图 Token 未记录，报告为 N/A。

## 与基线的可比性

|项|做法|
|---|---|
|原文|沿用 [rl-source-fontfix-20260926](../rl-source-fontfix-20260926/README.md) 冻结 benchmark；图谱 2,920 段与冻结 S2 段逐段相同（文本、偏移、原文哈希），段 P 引用为 S2:P|
|抽样|种子 20260923，实体 100、断言 200、别名 30，事实探针 48|
|协议|主运行与语义重复为 selected-metrics-v6-semantic-duplicates，代码固定为提交 b33a8c5，冻结提示与基线运行（rl-rerun-fontfix-20260926-r3）逐字一致，仅少已退役的拆分；类型另按 v7 两级粒度对五列统一重判|
|基线|GraphRAG、AutoSchemaKG、KGGen 不重跑，沿用 [sutton-barto-semantic-duplicate-20260928](../../results/sutton-barto-semantic-duplicate-20260928/README.md)|
|语义重复|叫法与初筛由评测方（Claude）离线冻结：100 个目标，20 个留下候选，共 24 对；终判 MiniMax-M3|

主运行时工作区 protocol.py 的两级类型粒度改动尚未定稿，主运行没有使用；10-08 定稿为 type-boundary-v3-two-level 后，五列类型统一重判。

## 文件

prepare_submission.py 只读导出提交；workflow.json 为主运行配置；targets-sheet / expansions / screening-sheet / screening(-indices) 为语义重复阶段冻结文件；merge_table.py 把新列并入基线总表。

## 复现

```bash
git worktree add --detach outputs/code-b33a8c5 b33a8c5
python studies/rl-fromzero-v3-20261008/prepare_submission.py
cd outputs/code-b33a8c5 && export PYTHONPATH=$PWD/src
python -m llm_graph_benchmark workflow prepare --config ../../studies/rl-fromzero-v3-20261008/workflow.json --run ../rl-fromzero-v3-20261008-eval
python -m llm_graph_benchmark workflow launch --run ../rl-fromzero-v3-20261008-eval
python -m llm_graph_benchmark workflow semantic-prepare --parent ../rl-fromzero-v3-20261008-eval --expansions ../../studies/rl-fromzero-v3-20261008/expansions.json --screening ../../studies/rl-fromzero-v3-20261008/screening.json --run ../rl-fromzero-v3-20261008-semantic
python -m llm_graph_benchmark workflow launch --run ../rl-fromzero-v3-20261008-semantic
python -m llm_graph_benchmark workflow combine --parent ../rl-fromzero-v3-20261008-eval --stage ../rl-fromzero-v3-20261008-semantic --out ../rl-fromzero-v3-20261008-combined
```

2026-10-08 类型改为两级粒度（type-boundary-v3-two-level）后，用当前代码对两个父运行补判类型并合并：

```bash
llm-graph-benchmark workflow type-prepare --parent outputs/rl-fromzero-v3-20261008-eval --run outputs/rl-fromzero-v3-20261008-types
llm-graph-benchmark workflow type-prepare --parent outputs/rl-rerun-fontfix-20260926-r3 --run outputs/rl-rerun-r3-types-20261008
llm-graph-benchmark workflow launch --run outputs/rl-fromzero-v3-20261008-types
llm-graph-benchmark workflow launch --run outputs/rl-rerun-r3-types-20261008
llm-graph-benchmark workflow combine --parent outputs/rl-fromzero-v3-20261008-eval --stage outputs/rl-fromzero-v3-20261008-semantic --stage outputs/rl-fromzero-v3-20261008-types --out outputs/rl-fromzero-v3-20261008-combined-v7
llm-graph-benchmark workflow combine --parent outputs/rl-rerun-fontfix-20260926-r3 --stage outputs/rl-semantic-duplicate-20260928 --stage outputs/rl-rerun-r3-types-20261008 --out outputs/rl-rerun-r3-combined-v7
python studies/rl-fromzero-v3-20261008/merge_table.py
```

主运行 878 个任务（计划调用 1,078 次），0 个超长；876 完成，2 条完整断言因 Ē 的 Unicode 写法不一致而技术失败未评。结果见 [results/sutton-barto-fromzero-v3-20261008](../../results/sutton-barto-fromzero-v3-20261008/README.md)。
