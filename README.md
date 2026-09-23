# LLM Graph Benchmark

一个独立、方法无关的文档到知识图谱评估框架。它不读取任何提取系统的内部数据库；每个
系统只需把结果转换成统一的 `submission.json`，即可在同一份 benchmark、rubric 和盲测
样本上比较。

第一版聚焦“低人工标注但有说服力”的评估证据链：

- **输出契约**：统一 Entity、Assertion、Evidence 和运行成本格式；
- **可追溯校验**：拒绝不存在的文档、证据单元和关系端点；
- **盲化抽样**：按系统、文档和对象类型确定性抽样，公开任务不包含系统名称；
- **内在指标**：证据覆盖、孤立实体、连通分量、谓词规模和表面重复；
- **外部裁判聚合**：接受 LLM 或人工的相同 judgment 格式，按多数票和 Wilson 区间汇总；
- **对比报告**：结构指标与 Entity/Assertion 裁判结果分栏报告，不制造单一总分。

报告优先展示语义质量，结构规模与引用存在率随后展示。引用存在不代表引用正确或充分。
[粗粒度可靠性协议](docs/RELIABILITY_PROTOCOL.md)补充两个简单问题：抽取内容是否正确、
提交的原文引用是否足以支持内容。完整 Assertion 已包含关系方向与必要条件，不再拆成
更多独立分数；来源覆盖单独报告。对应的[D2L补评](studies/d2l-reliability-20260920/README.md)
使用新随机样本和冻结历史输出，不改写旧评分、不预设方法胜负。

## 边界

本仓库拥有 benchmark、submission 和 judgment 契约，以及所有公共评估逻辑。被评系统拥有
自己的适配器：

```text
method A internal DB ─┐
method B JSON output ─┼─> submission.json ─> validate/sample/judge/aggregate/report
method C RDF graph ───┘
```

评估器不会把裁判结果写回被评图谱。实际书籍正文、大模型密钥和未公开人工标签也不应提交
到仓库；benchmark 可以只保存内容哈希和受控环境中的证据单元文件。

## 数据格式

一个 benchmark 目录包含：

```text
benchmark.json       # benchmark ID 和相对文件路径
documents.jsonl      # 文档及可引用的 text/image/table 单元
fact_probes.jsonl    # 从原文侧构造的覆盖率探针
qa_probes.jsonl      # 可选：冻结的 Book QA 问题与参考答案
rubric.json          # 冻结的评价维度与标签定义
```

`submission.json` 的核心结构：

```json
{
  "schema_version": "1.0",
  "benchmark_id": "tiny-book-v1",
  "system": {"id": "example", "name": "Example extractor", "version": "0.1"},
  "documents": [{
    "document_id": "book-1",
    "entities": [{
      "id": "e1",
      "name": "gradient descent",
      "definition": "An optimization method.",
      "types": ["method"],
      "evidence": [{"unit_id": "p1", "quote": "gradient descent"}]
    }],
    "assertions": [{
      "id": "a1",
      "subject_id": "e1",
      "predicate": "minimizes",
      "object_id": "e2",
      "text": "Gradient descent minimizes an objective.",
      "scope": "under suitable step sizes",
      "polarity": "positive",
      "evidence": [{"unit_id": "p1"}]
    }]
  }],
  "runtime": {"elapsed_seconds": 12.3, "cost_usd": 0.04, "input_tokens": 1000,
              "output_tokens": 200}
}
```

证据单元支持 `text`、`image`、`table` 和 `mixed` modality；图片/扫描教材可以在
`location` 中保存页码和 bbox，而无需改变 submission 契约。

## 基线配置修正（2026-09-09）

[修正实验说明](studies/d2l-baseline-correction-20260909/README.md)记录 KGGen 官方 LLM 归一、
AutoSchemaKG 完整概念化和 GraphRAG 中文 LLM 图构建的配置与运行方式。旧结果保留；
新全书结果以独立运行目录的校验、评分和完成标记为准。

## 使用

新一轮构图质量评测使用[版本化质量协议](docs/QUALITY_PROTOCOL.md)：联合断言质量、严格
事实恢复与核心覆盖分开生成盲评任务；同时报告全样本通过率、判定覆盖率和调用错误，并
支持同裁判、同探针的配对比较。新评分需要新判断，不能继承旧 `covered` 标签。

```bash
python -m pip install -e '.[dev]'

llm-graph-benchmark validate-benchmark examples/tiny/benchmark.json
llm-graph-benchmark validate-submission \
  examples/tiny/submissions/example.json \
  --benchmark examples/tiny/benchmark.json

llm-graph-benchmark sample \
  --benchmark examples/tiny/benchmark.json \
  --submission examples/tiny/submissions/example.json \
  --entities-per-document 10 \
  --assertions-per-document 10 \
  --tasks-out outputs/tasks.jsonl \
  --key-out outputs/task-key.jsonl

llm-graph-benchmark probe-tasks \
  --benchmark examples/tiny/benchmark.json \
  --submission examples/tiny/submissions/example.json \
  --retrieval-results examples/tiny/retrieval_results.jsonl \
  --tasks-out outputs/probe-tasks.jsonl \
  --key-out outputs/probe-task-key.jsonl

llm-graph-benchmark identity-tasks \
  --benchmark examples/tiny/benchmark.json \
  --submission examples/tiny/submissions/example.json \
  --tasks-out outputs/identity-tasks.jsonl \
  --key-out outputs/identity-task-key.jsonl

llm-graph-benchmark retrieve-qa-lexical \
  --benchmark examples/tiny/benchmark.json \
  --submission examples/tiny/submissions/example.json \
  --out outputs/qa-retrieval.jsonl

llm-graph-benchmark qa-tasks \
  --benchmark examples/tiny/benchmark.json \
  --submission examples/tiny/submissions/example.json \
  --retrieval-results outputs/qa-retrieval.jsonl \
  --tasks-out outputs/qa-tasks.jsonl \
  --key-out outputs/qa-task-key.jsonl

llm-graph-benchmark metrics \
  examples/tiny/submissions/example.json \
  --benchmark examples/tiny/benchmark.json \
  --out outputs/example-metrics.json

llm-graph-benchmark aggregate \
  --key outputs/task-key.jsonl \
  --judgments outputs/judgments.jsonl \
  --out outputs/judged-metrics.json

llm-graph-benchmark report \
  --metrics outputs/example-metrics.json \
  --judged outputs/judged-metrics.json \
  --out outputs/report.md
```

公开的 `tasks.jsonl` 只含盲化后的待评价内容；私有 `task-key.jsonl` 才保存 task 与系统、
文档、原始 item 的映射。裁判输出统一为：

```json
{"task_id":"t_...","judge_id":"judge-a","label":"pass","confidence":0.9,"reason":"..."}
```

语义标签是 `pass`、`fail`、`uncertain`；调用或解析失败可记录 `error`，不当作语义投票。
同一任务可由不同模型或人评价，同一 judge_id 的重复任务须先显式整理重试记录。
聚合结果会同时报告 expected、judged 和 unjudged；缺失裁判不会被静默排除。
新版还报告 error、全样本通过率与判定覆盖率；旧 pass_rate 字段保留原 decided 分母。
若 fact probe 带有 `metadata` 分层字段，私有 task key 会保留这些字段，`aggregate` 会额外
按复杂度、位置、章节等维度分别报告结果；公开盲评任务不暴露这些分层标签。

完整性评估不会默认把整张图塞给裁判。`probe-tasks` 接受冻结的 retrieval results，把每个
source-side fact probe 与同一检索器为各系统召回的候选 Assertion 组合成盲测任务。检索器
可以是词法、embedding 或图检索，但其名称、版本、top-k 和参数必须与结果一起冻结，并且
对所有系统完全一致。这样可以把“图里没有该事实”和“检索器没有找到该事实”分别分析。

retrieval results 每行格式如下：

```json
{"system_id":"example","probe_id":"f1","retriever":"manual-tiny-v1","assertion_ids":["a1"]}
```

仓库内置一个确定性的图谱文本基线，可用于所有系统的统一召回：

```bash
llm-graph-benchmark retrieve-lexical \
  --benchmark examples/d2l-book-v1 \
  --submission outputs/system-a/submission.json \
  --top-k 10 \
  --out outputs/retrieval-lexical.jsonl
```

该基线只索引 Assertion 的 subject、predicate、object、text 和 scope，不读取 source
passage 或 evidence，避免用原文证据替图谱回答。其默认配置固定为 Unicode 规范化、中文
单字/双字与拉丁词 token、BM25（`k1=1.2`、`b=0.75`），结果中的 retriever id 会记录
版本和参数。

## 开发

```bash
pytest
pytest --cov=llm_graph_benchmark
```

`examples/tiny` 是完全合成的小型端到端样例，不包含真实书籍内容。

## 真实案例

- [D2L 全书 vNext 图谱评测（2026-08-26）](studies/d2l-fullbook-vnext-20260826/REPORT.md)：
  对 1105/1105 chunk 的 schema 10 只读 SQLite 图谱完成 252 项来源证据盲评，覆盖 Entity、
  Assertion、身份解析、48 条冻结事实、24 道 Book QA、结构完整性与运行血缘。
- [D2L 历史图谱快照评测（2026-08-20 pilot）](studies/d2l-historical-pilot-20260820/REPORT.md)：
  对 27/200 chunk 两份只读 SQLite 快照完成 Entity 准入/类型/定义、Assertion、事实恢复、
  身份解析、Book QA、结构、稳定性、效率和裁判一致性评测，并保存判断、输入哈希与重建脚本。

## `llm-knowledge-graph` SQLite 适配器

schema 10 的静态数据库快照可以只读转换为本仓库的中立契约：

```bash
llm-graph-benchmark adapt-llmkg-sqlite \
  --db /path/to/snapshot.db \
  --out-dir outputs/d2l-pilot \
  --benchmark-id d2l-pilot-v1 \
  --system-id llm-knowledge-graph \
  --system-name "LLM Knowledge Graph" \
  --system-version snapshot-name \
  --fact-probes examples/d2l-pilot/fact_probes.jsonl \
  --qa-probes examples/d2l-book-v1/qa_probes.jsonl
```

适配器不导入原项目，也不写 SQLite。它导出已处理范围内的 Source Passage 作为可引用单元，最终
Entity/Assertion 作为 submission，并把 source progress、未裁判与未落实 Observation、
模型及 prompt 版本放进 `adapter-report.json`。默认拒绝包含 failed/running progress 的
数据库；`--allow-incomplete` 只应用于明确标记的诊断试验。

适配器按声明的 `--chunk-chars`（默认 8000）和 `--overlap-chars`（默认 500）从持久化
Passage 重建 chunk，只把 `source_progress=done` 的 chunk 所覆盖的 Passage 放入 benchmark。
评估范围和重建得到的整书 chunk 数会写入 manifest，避免用 partial graph 对比 full-book
输入。如果历史实验使用了不同参数，必须在适配时显式传入。

完整冻结集位于 `examples/d2l-book-v1/fact_probes.jsonl`。对只处理了书籍前部的历史快照，
可显式传入 `--filter-probes-to-scope`；适配报告会记录输入、保留和排除的探针数及被排除的
ID。默认仍采用严格模式，任何越界探针都会使适配失败。

`examples/d2l-pilot/fact_probes.jsonl` 只有一条接口探针，仅用于验证工作流。

单条提取质量的新版协议与裁判验证边界见 [质量协议 v2](docs/QUALITY_PROTOCOL_V2.md)。
`quality-tasks --version v2` 区分断言正确性与来源信息覆盖，旧版默认及已有结果保持不变。

当前 v2.2 协议及版本记录见 [QUALITY_PROTOCOL_V22.md](docs/QUALITY_PROTOCOL_V22.md)，复跑工具见 [study](studies/d2l-quality-v22-20260908/README.md)。

2026-09-09 已完成 1000 条单条质量评分，结果与局限见 [v2.2 最终报告](studies/d2l-quality-v22-20260908/RESULTS.md)。其中 1 条使用保留原始响应的本地引号转义恢复。
