# 第二本书：语义重复率（取代实体拆分）

协议 selected-metrics-v6-semantic-duplicates。语义重复为单独阶段（semantic-duplicate-v1），其余指标原样取自 [RL 统一重评](../sutton-barto-rerun-20260926/README.md)，已退役的实体拆分不列入。
REPORT.md / comparison.csv / summary.json 为合成总表；stage/ 为语义重复阶段的报告、逐对判定、抽样与冻结的叫法和初筛；raw/ 为阶段运行目录全部记录（含发给裁判的完整消息与原始返回，入库前用实际 API 密钥扫描，未命中）。
过程与复现见 [studies/rl-semantic-duplicate-20260928](../../studies/rl-semantic-duplicate-20260928/README.md)。

|方法|语义重复率|初筛留下 / 判同指的实体对|排除的超大实体（候选池）|
|---|---:|---:|---:|
|我们的方法|5.0%（5/100）|16 / 5|0|
|GraphRAG|37.0%（37/100）|91 / 74|20|
|AutoSchemaKG|42.0%（42/100）|108 / 85|30|
|KGGen|54.5%（54/99）|127 / 103|21|

语义重复率 = 抽样实体中至少有一个严格同指节点的比例，越低越好；不确定按实体计均为 0。KGGen 有 1 个抽样实体引用原文超过170KB，按规则排除，分母为 99。
判同指的 267 对里，226 对名称统一写法后并不相同（我们 2、GraphRAG 69、AutoSchemaKG 77、KGGen 78），旧的实体拆分根本不会把它们当作候选，例如 DLS / DORSOLATERAL STRIATUM、POLE-BALANCING / CART-POLE TASK、McClure / S. M. McClure、BE objective / BE (Bellman error)。

读法与限制：
- 结果是下限：检索只看名称与别名，初筛只看名称、别名、类型，都可能漏掉重复；各方法同一流程。
- 基线的超大核心概念（reinforcement learning、policy、state/states 等）不在候选池内，它们之间的明显重复（如 AutoSchemaKG 的 state/states、action/actions）没有计入，基线重复率偏低估。
- 叫法与初筛由评测方（Claude）离线完成并冻结；最终同指由 MiniMax-M3 逐对盲评。
- 抽查到少量偏宽的同指判定，如我们的"强化学习 / 强化学习理论"、"智能体-环境边界 / 智能体–环境接口"，GraphRAG 的 POLE-BALANCING / POLE-BALANCING EXAMPLE；逐条判定与理由见 stage/case-results.json，建议人工复核。
