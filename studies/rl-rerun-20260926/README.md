# 强化学习书统一重评（selected-metrics-v5-identity-sources）

四个方法在同一次运行里评测，使用按字形名重抽的原文（[rl-source-fontfix-20260926](../rl-source-fontfix-20260926/README.md)）和当前协议。
随机种子沿用 20260923；样本由种子和提交哈希决定，和上一轮逐条相同（已核对：我们 908、GraphRAG 878、AutoSchemaKG 778、KGGen 708 项），可以逐条对比新旧判定。

|相对上一轮的变化|影响的指标|
|---|---|
|原文修复：负号、希腊字母、∑∇∈′⊤ 等 4,327 个错误字形，剩 36 个|读原文的指标：断言正确性、实体所指、实体引用、类型、描述、别名、拆分|
|别名：全部引用原文不截断（原为 1,200 字），可结合通用知识|别名同一性|
|拆分：加入双方各自的全部引用原文，可结合通用知识|实体拆分|
|3 条事实探针修正错字形；事实探针标为参考指标，检索器不变|完整事实探针覆盖|

描述口径不变：只看实体自己的引用段，整段判支持 / 不支持 / 不确定。Book QA 已移除。

## 规模

3,272 个任务，计划调用 4,072 次（不含重试）：断言正确性 800（每条两步）、关系粒度 800、实体所指 400、实体引用 400、类型 300、描述 200、事实探针 192、拆分 120、别名 60。
KGGen 的 "Reward → reward r" 别名任务引用 573 段、约 386KB，超过 350KB 上限，按现行规则标为 unassessed_size，不截断、不计为错误。

## 运行

```bash
llm-graph-benchmark workflow prepare --config studies/rl-rerun-20260926/workflow.json --run outputs/rl-rerun-fontfix-20260926
llm-graph-benchmark workflow launch --run outputs/rl-rerun-fontfix-20260926
llm-graph-benchmark workflow status --run outputs/rl-rerun-fontfix-20260926
llm-graph-benchmark workflow report --run outputs/rl-rerun-fontfix-20260926
```

prepare 已完成（不调用 API）。launch 需要 MINIMAX_API_KEY，会调用 MiniMax-M3 付费接口。
