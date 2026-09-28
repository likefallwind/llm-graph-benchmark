# 强化学习书统一重评（selected-metrics-v5-identity-sources）

四个方法在同一次运行里评测，使用按字形名重抽的原文（[rl-source-fontfix-20260926](../rl-source-fontfix-20260926/README.md)）和当前协议。
随机种子沿用 20260923；样本由种子和提交哈希决定，和上一轮逐条相同（已核对：我们 908、GraphRAG 878、AutoSchemaKG 778、KGGen 708 项），可以逐条对比新旧判定。

|相对上一轮的变化|影响的指标|
|---|---|
|原文修复：负号、希腊字母、∑∇∈′⊤ 等 4,327 个错误字形，剩 36 个|读原文的指标：断言正确性、实体所指、实体引用、类型、描述、别名、拆分|
|别名：全部引用原文不截断（原为 1,200 字），可结合通用知识|别名同一性|
|拆分：旧裁判加入双方各自的全部引用原文，可结合常识（split-legacy-full-sources-knowledge-v3）|实体拆分|
|3 条事实探针修正错字形；事实探针标为参考指标，检索器不变|完整事实探针覆盖|

描述口径不变：只看实体自己的引用段，整段判支持 / 不支持 / 不确定。Book QA 已移除。

## 规模

3,272 个任务，计划调用 4,072 次（不含重试）：断言正确性 800（每条两步）、关系粒度 800、实体所指 400、实体引用 400、类型 300、描述 200、事实探针 192、拆分 120、别名 60。
KGGen 的 "Reward → reward r" 别名任务引用 573 段、约 386KB，超过 350KB 上限，按现行规则标为 unassessed_size，不截断、不计为错误。

## 运行

```bash
llm-graph-benchmark workflow prepare --config studies/rl-rerun-20260926/workflow.json --run outputs/rl-rerun-fontfix-20260926-r3
llm-graph-benchmark workflow launch --run outputs/rl-rerun-fontfix-20260926-r3
llm-graph-benchmark workflow status --run outputs/rl-rerun-fontfix-20260926-r3
llm-graph-benchmark workflow report --run outputs/rl-rerun-fontfix-20260926-r3
```

2026-09-26 22:07 中断首次运行（outputs/rl-rerun-fontfix-20260926），修复关系粒度解析器：模型偶尔用 ```json 代码块包裹输出，其他 JSON 裁判本来会去掉，粒度没有，导致 19 条内容正确却解析失败。修复不改变任何标签。
随后在 -r2 目录重新 prepare，任务 ID 与内容哈希逐条一致，原样搬入已完成的 1,392 条结果，从断点继续；30 条技术失败重新请求。

2026-09-28 拆分裁判由 v2 改为 v3：v2 重写了整段提示词并禁止用系统描述证明两者不同，导致相关但不同的概念被判为应合并（我们 4 对、GraphRAG 3 对、AutoSchemaKG 3 对由通过变为不通过）。v3 回到旧裁判，只保留补原文和结合常识两处改动。只升级拆分的版本，其余任务 ID 与内容哈希不变；在 -r3 目录重新 prepare，原样搬入 -r2 的 3,149 条结果，重判 120 对拆分，另重请求 -r2 中 3 条技术失败的断言。

-r3 已跑完，3,269 条完成，报告仍为未完成：
- KGGen "Reward → reward r" 别名任务超长，未评（见上文）；已评 29 条中 26 条通过（89.7%）。
- GraphRAG 两条完整断言（MDPS related_to POMDPS；NOMINAL SOLUTION related_to STRING）在 -r2、-r3 共 45 次尝试均无合格输出：35 次推理用尽 8,192 token 上限，4 次漏核断言本身的边段，2 次证据编号或 JSON 不合格，4 次网络错误。校验拒绝正确，不是解析器问题。2026-09-28 决定不再重试、不为这两条单独调高上限，记为技术失败未评；已评 198 条中 175 条正确（88.4%），这两条无论判对判错，得分都在 87.5%–88.5% 之间。

launch 需要 MINIMAX_API_KEY，会调用 MiniMax-M3 付费接口。
