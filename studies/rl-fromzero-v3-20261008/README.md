# 强化学习书：从零构图（pipeline-v3）评测

图谱：`../llm-knowledge-graph/outputs/rl-from-zero-m3-c6-20261004-pipeline-v3`（2026-10-04 至 10-07，MiniMax-M3，6 并发，324/324 块，完整性检查通过）。
只读强化学习书构图，1,268 实体、2,707 完整断言；构图 Token 未记录，报告为 N/A。

## 与基线的可比性

|项|做法|
|---|---|
|原文|沿用 [rl-source-fontfix-20260926](../rl-source-fontfix-20260926/README.md) 冻结 benchmark；图谱 2,920 段与冻结 S2 段逐段相同（文本、偏移、原文哈希），段 P 引用为 S2:P|
|抽样|种子 20260923，实体 100、断言 200、别名 30，事实探针 48|
|协议|selected-metrics-v6-semantic-duplicates，代码固定为提交 b33a8c5；冻结提示与基线运行（rl-rerun-fontfix-20260926-r3）逐字一致，仅少已退役的拆分|
|基线|GraphRAG、AutoSchemaKG、KGGen 不重跑，沿用 [sutton-barto-semantic-duplicate-20260928](../../results/sutton-barto-semantic-duplicate-20260928/README.md)|
|语义重复|叫法与初筛由评测方（Claude）离线冻结：100 个目标，20 个留下候选，共 24 对；终判 MiniMax-M3|

工作区 protocol.py 有一处未提交的类型粒度提示改动，基线类型分数不是用它评的，本评测不使用。

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
python ../../studies/rl-fromzero-v3-20261008/merge_table.py
```

主运行 878 个任务（计划调用 1,078 次），0 个超长。结果待运行完成后归档。
