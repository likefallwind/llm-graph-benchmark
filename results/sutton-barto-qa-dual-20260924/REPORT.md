# 图谱评测结果

协议：selected-metrics-v2-qa；模型：MiniMax-M3；有效任务 96/96。
任务未完成时不发布最终得分。N/A 的具体原因、各项分母、语义不确定与技术状态见 summary.json。

|指标|我们的方法（强化学习）|GraphRAG|AutoSchemaKG|KGGen|
|---|---:|---:|---:|---:|
|Book QA 核心信息支持率|16.67%（4/24）|37.50%（9/24）|45.83%（11/24）|4.17%（1/24）|
|Book QA 完整答案支持率|8.33%（2/24）|25.00%（6/24）|41.67%（10/24）|4.17%（1/24）|

## 判定覆盖与不确定

|方法|指标|已判/可评|语义不确定|技术失败/未评|N/A 原因|
|---|---|---:|---:|---:|---|
|我们的方法（强化学习）|Book QA 核心信息支持率|24/24|0|0||
|我们的方法（强化学习）|Book QA 完整答案支持率|24/24|0|0||
|GraphRAG|Book QA 核心信息支持率|24/24|3|0||
|GraphRAG|Book QA 完整答案支持率|24/24|3|0||
|AutoSchemaKG|Book QA 核心信息支持率|24/24|2|0||
|AutoSchemaKG|Book QA 完整答案支持率|24/24|0|0||
|KGGen|Book QA 核心信息支持率|24/24|1|0||
|KGGen|Book QA 完整答案支持率|24/24|1|0||

## 口径

- 类型、描述主分数为实体内部通过比例的宏平均；不确定保留在分母。缺原生字段不补造，单列字段覆盖。
- 类型粒度只统计正确标签，每实体取最具体正确类型；覆盖分母是全部抽样实体。无正确类型与无类型字段分开。
- 关系粒度读取完整原生断言（含自然语言描述），与正确性独立。
- 实体正确性使用提交引用及左右各一段；实体引用、类型与描述只使用完整提交来源；断言使用引用所在完整小节。
- 完整事实覆盖只读 BM25 Top10 图候选，不能用目标事实或原文为图补信息；不是全书召回率。
- QA 先从来源制定共用答案要点，再用完整图断言逐项核对；核心与完整支持分别统计，参考答案不能补足图候选。来源要点与引文校验均不等于独立人工语义验证。
- 身份保留历史通用裁判：别名证据最多1200字符，拆分只展示双方描述与共享表面形式。
- 实体拆分仅针对共享规范化表面形式的候选对；没有候选不代表100%正确。
- 构图 Token 与本次评测调用用量分开；无构图记录记 N/A。
- 各图独立抽样，不是同实体配对实验；模型判断未经独立人工金标准校准，不据细小差距断言排名。
- 类型标签绑定属于新接口版本，其他迁移规则见 metric_versions；不同版本的历史结果不自动混合。

## 输入范围

- 我们的方法（强化学习）：Sutton–Barto source_id=2子图；1354实体、2708完整断言；来自D2L种子库的跨书增量构图，保留全部原生跨书引用
- GraphRAG：Pinned original construction, English RL source only; native output semantics retained.
- AutoSchemaKG：Semantic quality excludes native event-participation edges; structure retains full extracted graph; induced schema stored separately.
- KGGen：Pinned original construction, English RL source only; native output semantics retained.

本轮仅重评 QA；其余指标未运行，不更新历史结果。
