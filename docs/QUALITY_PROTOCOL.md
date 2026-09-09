# 构图质量评测 v1（2026-09-07）

本轮完善评分协议与离线工具。旧 D2L 探针、检索结果、裁判记录与报告保持原样。
新任务准备成功不代表裁判已运行，更不代表新协议已经通过独立校准。
多书扩展、重新构图与付费模型调用留待下一轮。

## 主指标与诊断指标

| 任务 kind | 角色 | pass 条件 |
|---|---|---|
| `assertion_quality_v1` | 主要精度指标 | 原文支持、主谓宾投影忠实、完整表达保留必要限定三项同时成立 |
| `fact_recovery_strict_v1` | 主要覆盖指标 | 一条或多条候选共同恢复 source_fact 陈述的全部信息，不忽略所谓次要维度 |
| `fact_recovery_core_v1` | 覆盖诊断 | 核心命题及关键真值条件成立，允许动机或代价等附加信息缺失并说明 |

三项使用单独任务，防止把核心覆盖冒充完整恢复。旧三轴评价继续作为历史诊断，新的联合
质量判断不是从旧轴分数相乘或换分母得到的。旧 `covered=yes` 不能迁移为新 strict 的 pass。
这里是自定义语义评测，不称为标准 CaRB 分数。

原文用于检验事实和关系，不能替候选图谱补全遗漏。紧凑边的限定可由同条 Assertion 的
text、scope、polarity 联合保存；不要求某个方法必须输出专用 scope、定义或别名字段。
多个候选可以共同覆盖事实，无关候选不降低已恢复事实的召回；错误候选由独立精度抽样评价。
候选明确冲突、方向错误或没有候选时按对应规则判 fail；真正无法判断才 uncertain。

## 离线准备

沿用已冻结 retrieval results 重新执行 `probe-tasks` 可补全私有 key 的 `retriever_params`，
其原任务 ID 与候选内容保持不变。不要为了新评分更改探针、重排候选或增大 top-k。
新任务 ID 包含评分文本、原任务 ID、候选、完整证据与比较上下文的哈希。
只将生成的公开任务交给裁判，私有 key 不应出现在裁判输入中。

```bash
llm-graph-benchmark probe-tasks \
  --benchmark /path/to/benchmark.json \
  --submission /path/to/system/submission.json \
  --retrieval-results /path/to/frozen/retrieval.jsonl \
  --seed 20260820 \
  --tasks-out outputs/quality-v1/probe-tasks.jsonl \
  --key-out outputs/quality-v1/probe-key.jsonl

llm-graph-benchmark quality-tasks \
  --tasks outputs/quality-v1/probe-tasks.jsonl \
  --key outputs/quality-v1/probe-key.jsonl \
  --tasks-out outputs/quality-v1/fact-tasks.jsonl \
  --key-out outputs/quality-v1/fact-key.jsonl
```

`quality-tasks` 也接受 `sample` 生成的完整 tasks/key，对其中 `assertion_grounding` 生成联合
质量任务，跳过其他维度。现有 `axis-tasks` 已改变 kind，不能当作原始抽样任务输入。
生成器保留全部输入证据，不使用历史脚本的字符截断；输出文件必须是新路径。

每条任务的 `rubric` 是评分指令，`content` 和 `source_evidence` 是待评价数据。裁判适配器
应完整传递这三项并记录模型/版本/参数，用统一 judge_id 表示冻结的裁判配置。
超上下文、解析失败和 API 失败记录 `label=error`；不得裁剪证据后仍沿用相同任务 ID。
当前命令只准备任务，不调用模型；旧 study runner 不识别新 kind，不能直接拿来执行。

## 汇总与同探针对比

`aggregate` 保留旧 `pass_rate`（pass / (pass + fail)）字段，新增：

- `pass_rate_all`：pass / expected，是全部预定样本中已确认通过的比例。
- `judgment_coverage`：有语义判断的比例，包含 uncertain。
- `decision_coverage`：得到明确 pass/fail 的比例。
- `error`、`unjudged` 与 `status`：错误、缺失单独报告；任务未完整判断时状态为 incomplete。

调用失败不是语义失败。不同裁判的 error 不参与语义多数票，但计入 `error_judgment_count`。
同一裁判的重复任务记录拒绝汇总；先按公开的重试选择规则整理，不能静默选择有利结果。
没有明确判断时 Wilson 区间是 null，不能伪装成 [0, 0]。区间只反映已判样本抽样误差，
不覆盖裁判系统误差；同一本书的相关断言也不等于独立的跨书重复。

```bash
llm-graph-benchmark aggregate --key outputs/quality-v1/fact-key.jsonl \
  --judgments /path/to/new-judgments.jsonl --out outputs/quality-v1/metrics.json

llm-graph-benchmark compare-paired --key /path/to/combined-fact-key.jsonl \
  --judgments /path/to/combined-new-judgments.jsonl \
  --left system-a --right system-b --judge-id frozen-judge-config \
  --kind fact_recovery_strict_v1 --out outputs/quality-v1/paired.json
```

配对命令要求同一 probe 集、原文证据、retriever 与参数、评分版本、同一显式 judge_id。
若仍有缺失或 error，只报告 incomplete，不计算 p 值，CLI 返回 1。
uncertain 在通过/未通过对比中计为未通过，并单独保留三分类转移表。使用双侧精确 McNemar；
结果是未做多重校正的探索性检验，不自动宣告胜出，不把不显著解释为等效。
不能用不同系统独立抽出的断言 item_id 做配对比较。

## 基线与裁判校准：下一轮运行的条件

每个比较行应附上游 commit、具体阶段、模型/提示词、输入范围、检索预算及已知适配差异。
完整流程、抽取阶段、精确并集对照和低成本 NLP 参照应明确标注；字段未输出报告为能力
未测或不适用，不能伪装成标注错误。当前重点缺口包括 KGGen 的 LLM 归一、AutoSchemaKG
的概念化、GraphRAG 中文适用配置。未完成这些阶段的旧行不得改名为完整方法。

先冻结规则，再选择少量按系统与维度分层的随机任务供独立复核；额外选出的疑难/分歧样本
单独统计，不能和随机样本直接混算总体准确率。不同模型家族的裁判分别出表，比较排名与
错误接受/拒绝；有人工复核时记录复核者、来源与裁定规则，不把模型互相同意称为人工校准。
新增规则不能在原 48 探针上反复挑选最高分版本后声称确认性实验，应保留新的留出样本。

尚未完成：新模型判定及校准、完整强基线、成本补测、Assertion 文本库/细关系图/粗类别
图的用途消融。当前通过软件测试与离线任务验证只证明工具行为，不证明测量效度已提升。

## 后续版本

单条精度协议修订见 [QUALITY_PROTOCOL_V2.md](QUALITY_PROTOCOL_V2.md)。本文保留为 v1 历史协议；
上述“尚未执行”描述为当时状态，实时运行状态须读取各 run 的 summary.json。v2 不改写 v1 标签。
