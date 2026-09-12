# D2L 基线修正实验（2026-09-09）

本轮只修正比较基线的配置、阶段完整性和适配，不修改本方法，不开展消融或跨书实验。
用户已授权使用 MiniMax API，所有构图、概念化与评测进程共用最多 6 个实际请求槽。
旧图、旧评分和失败原件均保留。新实验的完成状态以运行目录的持久产物为准。

## 修正范围

| 基线 | 原比较的限制 | 本轮运行 |
|---|---|---|
| KGGen | 只有抽取与 SemHash/精确去重，没有 LLM 归一；变换后证据来自端点交集/并集 | 复用冻结、尚未去重的逐片段抽取；调用官方 aggregate 与公开 LM_BASED 归一模式，配置 multilingual-e5-small；记录逐三元组变换来源 |
| AutoSchemaKG | 只完成抽取；概念化未完成；混合路由与少量有效空结果被重抽 | 新目录、官方 MiniMax 重新抽取全部片段；完成官方实体/事件/关系概念化、CSV 和 GraphML；有效空结果不重抽 |
| GraphRAG | Fast regex_english 配置不适用于中文 | 官方 LLM 抽取及描述汇总；官方 domain/persona/examples 生成器与中文 untyped 提示模板；保留原生关系描述 |

上游版本固定，不升级到未经审计的最新版本：

- KGGen: `6259b4c71523ceae75dafb4acec2eb833bef8f8e`。
- AutoSchemaKG: `d0a1666ae6621806faf814504c73678de4e809f2`。
- GraphRAG: `7bb23cc7f32f47cf618a1ae9cca39a6695f434ae`。

官方接口依据：
[KGGen](https://github.com/stair-lab/kg-gen)、
[AutoSchemaKG](https://github.com/HKUST-KnowComp/AutoSchemaKG)、
[GraphRAG prompt tuning](https://microsoft.github.io/graphrag/prompt_tuning/auto_prompt_tuning/)。
本机源码是具体参数和实现行为的最终依据，README 的旧 cluster 示例与当前 API 可能不同。

## 方法边界与适配

KGGen 使用官方支持的 `DeduplicateMethod.LM_BASED`，不是默认 SemHash，也不称为所有可选模式均运行。
多语言召回模型通过上游公开 `retrieval_model` 参数传入，revision 为
`614241f622f53c4eeff9890bdc4f31cfecc418b3`。没有把本方法的证据裁判加入 KGGen。
归一的成功逐项决策和成功聚类均保存；任何聚类异常都会阻止导出，避免上游捕获异常后输出不完整图。
关系变换必须能由官方代表映射完整重放；证据只沿原三元组传递，不用端点共现补造证据。

AutoSchemaKG 使用上游原有中文抽取提示与三个 schema，经官方 `process_stage` 与 parser 处理。
每个成功阶段独立缓存，失败阶段才重试。概念化沿用官方邻居采样和提示，固定随机种子，保留完整请求缓存。
概念化的全部输入条目必须有输出；原生 CSV 三元组集合须与适配重放一致。
实体 types 来自上游实际生成的概念，不使用 entity/event 占位类型；不存在的定义不由适配器补写。
完整原生图包含 schema/概念边，另存 `schema.json`；来源支持的断言评测仍与概念归纳分开。

GraphRAG 以原冻结 chunk 为 text unit，默认一次 gleaning，之后执行官方实体/关系合并、孤儿关系过滤与描述汇总。
提示词生成从语料固定随机抽样，未读取评测标签；对代码/公式的字面花括号做模板转义，输入文字含义不变。
GraphRAG 原生关系没有开放谓词字段，适配采用 `related_to` 并保留原生描述，不使用另一次 LLM 虚构谓词。
这覆盖标准 LLM 图构建；面向问答的社区报告、向量索引与查询器不是本轮构图比较的对象。
空关系表保留列 schema，避免上游汇总在合法空图上失败。

统一使用 MiniMax-M3、temperature=0、官方 `text/chatcompletion_v2`。提供方的 `service_tier=standard`
不属于 OpenAI SDK 枚举；适配只丢弃 SDK 不接受的提供方外层字段，原始响应、答案、模型与用量均保留。
拒绝提供方错误、模型标识不符和截断响应。进程间文件锁保证实际 API 并发不超过 6，重试也占槽。
密钥仅从环境或已有静态配置读取，不写入脚本、日志、命令行或产物。

## 运行与完成

```bash
python3 studies/d2l-baseline-correction-20260909/launch.py \
  --out outputs/d2l-baseline-correction-m3-c6-RUN
```

长运行使用独立 tmux。controller 同时启动三个方法，所有进程共享 6 个请求槽。
每种方法构图成功后自动生成并评分 200 条单断言质量样本及 48 条冻结事实恢复任务。
运行目录保存源码快照、语料哈希、上游版本、请求与中间阶段结果；同一目录可断点继续。
不要修改活动运行的 source 快照。停止后修代码应创建新版本目录并显式审计可复用输入。

完成需同时满足：

1. 三个方法各自 `summary.json: status=complete`、统一 submission 校验成功和 `.finished`。
2. 三个方法的 `evaluation/summary.json` 全部完成，无缺失/错误标签，存在 `evaluation/.finished`。
3. controller 生成 `results.json`、`RESULTS.md`、`.exit=0` 与 `.finished`。

原始调用成功不等于语义准确。AutoSchemaKG 概念化完成也不等于 schema 质量已独立校准。
新质量使用冻结 v2.2，辅助恢复使用历史 CaRB covered；不将 unsupported 当作精度，不拼接 F1。
这是基线配置修正，不解决同预算消融、独立人工校准或跨语料泛化。

## 验证

```bash
python -m pytest -q tests
python -m pytest -q studies/d2l-baseline-correction-20260909/test_corrections.py
```

单元测试覆盖共享并发、失败时有界派发、成功与空结果缓存、来源变换、模型与截断检查、响应外层兼容。
真实冒烟覆盖三个方法完整的小样本阶段；实际记录在运行说明指定的 smoke 目录，不能当成全书结果。
验证记录见 [VALIDATION.md](VALIDATION.md)。运行 `evaluate.py --smoke` 仅执行一条质量与一条覆盖任务，
写入独立的 `evaluation-smoke/`，不会被正式 controller 当作全量评测完成。
