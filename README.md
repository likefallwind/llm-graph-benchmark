# LLM Graph Benchmark

方法无关的文档知识图谱评测。将原生输出适配为 submission.json，与原文 benchmark 一起交给固定工作流，得到质量、粒度、事实覆盖、结构与构图用量对照表。

**当前入口是 workflow；指标以 [评测协议](docs/PROTOCOL.md) 为准。**
[操作说明](docs/WORKFLOW.md)包含配置、后台运行和失败恢复。
旧 study 和旧质量协议仅用于历史追溯，不再作为新评测的默认指标集合。

## 保留指标

|类别|当前保留内容|
|---|---|
|断言与关系|完整断言正确/错误/不确定；关系 L1/L2/L3；具体且正确覆盖、L3 内正确率|
|实体|实体所指正确率、实体引用支持率|
|类型|类型标签兼容正确率（实体宏平均）；最具体正确类型粒度与正确且细粒度覆盖|
|描述|整段描述支持率；同时报告不支持率与不确定率|
|身份|别名同一性；语义重复率（同一对象被建成多个节点，写法不同也算，逐对从严判定，越低越好）|
|覆盖|完整事实探针覆盖（参考指标，受检索召回影响）|
|结构|实体/断言数、语义评测范围、引用存在、孤立率、最大连通分量、原生字段覆盖、别名数|
|资源|构图输入/输出/总 Token，单位 million|

不再评测 Book QA（含核心信息/完整答案双指标）、历史断言引用支持率、旧关系分项、三轴联合分数、核心事实覆盖或稳定性；不计算综合加权分。引用存在率属于结构统计，不能当作引用支持率。QA试评仅保留为历史记录。

## 快速开始

运行环境为 Linux / WSL，Python 3.11+。准备和查看结果无需 API 密钥。

```bash
python -m pip install -e '.[dev]'

# 只校验输入、固定抽样、估算调用数；不请求模型
llm-graph-benchmark workflow prepare \
  --config examples/tiny/workflow.json --run outputs/tiny-workflow

# 明确执行才调用 MiniMax-M3；从运行环境读取 MINIMAX_API_KEY
llm-graph-benchmark workflow launch --run outputs/tiny-workflow
llm-graph-benchmark workflow status --run outputs/tiny-workflow

# 已成功结果原样复用；仅补技术失败需要这个开关
llm-graph-benchmark workflow launch --run outputs/tiny-workflow --retry-failed
llm-graph-benchmark workflow report --run outputs/tiny-workflow
```

输出 REPORT.md、comparison.csv、summary.json 和 case-results.json，以及冻结任务、提示、来源哈希、原始 API 响应。
默认每文档抽实体100、断言200、别名30；事实探针数量由 benchmark 提供。语义重复沿用实体样本，作为单独阶段运行，见[操作说明](docs/WORKFLOW.md)。
MiniMax-M3、temperature=0，同一 OS 用户的工作流运行共享最多6个 HTTP 请求槽，重试也占槽。
技术失败、不确定、缺原生字段分别统计；未完成指标不发布最终分数。

当前四方法的输入配置见 [current-evaluation](studies/current-evaluation/README.md)；
已完成的历史汇总见 [2026-09-23 结果](outputs/d2l-consolidated-results-20260923/REPORT.md)。
工作流新抽样、新任务版本不会自动继承历史标签。

## 输入边界

benchmark 由 benchmark.json、documents.jsonl、fact_probes.jsonl 和 rubric.json 组成。可选 qa_probes.jsonl 仅保留历史输入兼容，新工作流不评QA。
图谱使用现有 Entity / Assertion / Evidence 契约，详见 [适配指南](docs/ADAPTER_GUIDE.md)。
原生自然语言关系描述放在 Assertion.text 中；没有原生类型用 types=[]，没有描述用 definition="" 并标记 metadata.definition_available=false，不生成替代字段。
运行器只读取提交快照，不修改图谱。源码适配器可只读转换 SQLite。

新图谱来自同一原文时可复用原文与事实探针；新原文需要自己的来源侧基准。
只有图谱不能反推出构图 Token，缺日志时报告 N/A。

## 开发与历史兼容

```bash
pytest
```

离线测试使用合成响应验证程序，不证明语义裁判准确率。真实模型评测需要独立人工抽查。
旧 sample / quality-tasks / aggregate / report 等低层命令保留用于复现历史实验；
当前工作流不会调用已移除的指标，也不会混用历史不同口径的结果。

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
  --fact-probes examples/d2l-pilot/fact_probes.jsonl
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
