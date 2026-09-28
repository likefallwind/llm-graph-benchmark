# 强化学习书：语义重复率（semantic-duplicate-v1）

取代实体拆分正确率。父运行为 RL 统一重评 `outputs/rl-rerun-fontfix-20260926-r3`（其余指标不变），沿用其实体样本。
阶段运行目录 `outputs/rl-semantic-duplicate-20260928`（不入库），MiniMax-M3、temperature=0、6 并发。

## 流程与冻结文件

|步|做法|文件|
|---|---|---|
|1 目标|父运行每图 100 个抽样实体；引用原文超过170KB的实体排除出样本和候选池|targets-sheet.json（盲化：只有名称、别名、类型、描述）|
|2 叫法|评测方（Claude，本会话）为每个目标写等价叫法：缩写、全称、中英翻译、写法与单复数变体|expansions.json|
|3 候选|同图实体名称+别名 BM25，每个叫法各自排序、轮流取，前30个|screening-sheet.json|
|4 初筛|评测方只看名称、别名、类型，宽松保留可能同指的候选|screening.json（screening-indices.json 为按候选序号记录的同一决定）|
|5 终判|MiniMax-M3 逐对从严判同指，看双方描述和原样的全部引用原文|阶段运行 results/|

目标 399 个（KGGen 1 个抽样实体超过170KB，排除）。173 个目标初筛留下候选，共 342 对：我们 16、GraphRAG 91、AutoSchemaKG 108、KGGen 127。
候选池排除的超大实体：我们 0、GraphRAG 20、AutoSchemaKG 30、KGGen 21，均为 reinforcement learning、policy、state/states 等核心概念，结果会低估这些实体涉及的重复。

结果：语义重复率 我们 5.0%、GraphRAG 37.0%、AutoSchemaKG 42.0%、KGGen 54.5%，342 对全部判完、无技术失败；总表与说明见 [results/sutton-barto-semantic-duplicate-20260928](../../results/sutton-barto-semantic-duplicate-20260928/README.md)。

## 注意

- 叫法和初筛由同一个评测方完成。目标表已去掉方法和实体 ID，但我们的方法实体多为中文名，评测方能认出来源；初筛按宽松标准执行，最终同指由盲评的 MiniMax 裁判判定。
- 检索只看实体名与别名，初筛只看名称、别名、类型，都可能漏掉重复；结果是下限，对各方法一致。
- 句子型实体（AutoSchemaKG 事件节点）只有在另一节点表达同一陈述时才可能同指；与概念节点不同指。

## 复现

```bash
llm-graph-benchmark workflow semantic-candidates --parent outputs/rl-rerun-fontfix-20260926-r3 --expansions studies/rl-semantic-duplicate-20260928/expansions.json --out /tmp/screening-sheet.json
llm-graph-benchmark workflow semantic-prepare --parent outputs/rl-rerun-fontfix-20260926-r3 --expansions studies/rl-semantic-duplicate-20260928/expansions.json --screening studies/rl-semantic-duplicate-20260928/screening.json --run outputs/rl-semantic-duplicate-20260928
llm-graph-benchmark workflow launch --run outputs/rl-semantic-duplicate-20260928
llm-graph-benchmark workflow combine --parent outputs/rl-rerun-fontfix-20260926-r3 --stage outputs/rl-semantic-duplicate-20260928 --out outputs/rl-combined-20260928
```
