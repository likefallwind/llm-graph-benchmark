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

## 使用

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

允许的标签是 `pass`、`fail`、`uncertain`。同一任务可由多个模型或人重复评价。
聚合结果会同时报告 expected、judged 和 unjudged；缺失裁判不会被静默排除。

完整性评估不会默认把整张图塞给裁判。`probe-tasks` 接受冻结的 retrieval results，把每个
source-side fact probe 与同一检索器为各系统召回的候选 Assertion 组合成盲测任务。检索器
可以是词法、embedding 或图检索，但其名称、版本、top-k 和参数必须与结果一起冻结，并且
对所有系统完全一致。这样可以把“图里没有该事实”和“检索器没有找到该事实”分别分析。

retrieval results 每行格式如下：

```json
{"system_id":"example","probe_id":"f1","retriever":"manual-tiny-v1","assertion_ids":["a1"]}
```

## 开发

```bash
pytest
pytest --cov=llm_graph_benchmark
```

`examples/tiny` 是完全合成的小型端到端样例，不包含真实书籍内容。
