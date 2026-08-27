# D2L 全书 vNext 图谱评测

## 结论

这份全书图谱已完成 1105/1105 个 chunk，SQLite `quick_check` 通过，且 Benchmark 与 Submission
schema 均通过验证。它不是只看内部 checker 的自评：本轮使用冻结的 48 条事实和 24 道 Book QA，
并对 180 个抽样实体、关系和身份任务逐条做来源证据盲评，共 252 个任务。

| 维度 | 结果 |
|---|---:|
| Entity admission | 30/30 (100.0%; 95% CI 88.6%–100.0%) |
| Entity typing | 25/30 (83.3%; 95% CI 66.4%–92.7%) |
| Entity definition grounding | 27/30 (90.0%; 95% CI 74.4%–96.5%) |
| Assertion grounding | 29/30 (96.7%; 95% CI 83.3%–99.4%) |
| Alias identity | 28/30 (93.3%; 95% CI 78.7%–98.2%) |
| Identity split correctness | 28/30 (93.3%; 95% CI 78.7%–98.2%) |
| Fact recovery | 36/48 (75.0%; 95% CI 61.2%–85.1%) |
| Book QA | 12/24 (50.0%; 95% CI 31.4%–68.6%) |

核心判断：单条 Assertion 的证据化很强，实体准入与身份解析也可靠；但复合事实的完整恢复仍是主要
瓶颈。失败多发生在遗漏对比条件、动机、代价或多步骤机制，而不是凭空制造完全错误的事实。

## 结构与身份

- Entity: 2140；Assertion: 3309；Source Passage: 9034。
- Entity/Assertion 证据覆盖率均为 100%。
- 孤立 Entity: 700（32.7%）。
- 最大连通分量覆盖 60.1% 的 Entity，共 762 个分量。
- 谓词有 919 种，说明开放谓词仍高度碎片化。
- 75 个模糊表面词组涉及 137 个 Entity；规范名表面重复组为 0。

类型错误集中在“多标签越多越好”的过度标注，例如把交叉熵损失标成平方误差损失、把 BERT 表示
标成模型、把优化算法同时标成损失函数/正则化/注意力机制。定义错误则集中于把常识或实现细节补进
证据没有说到的定义。

## 运行完整性与血缘

- 数据库：`/home/likefallwind/code/llm-knowledge-graph/tmp/d2l-full1105-c6-20260817-193600.db`（只读评测，未修改来源仓库）。
- schema v10，模型 `MiniMax-M3`，进度
  `1105/1105`，chunk 范围
  0–1104。
- 来源提交：`1aed294b7b5dbb6c1e779d000d2fdb2b1ace21d4`；运行时 worktree patch SHA-256
  `23ce929894845b64cbf32e7a84047ded51dacdffaab704cf0238f90f25326123`。
- Claim observation: 4862；支持 3313；
  insufficient 1008；contradicts 6；
  materialized 3279。
- Entity observation: 7289；unresolved 0。

active runtime、token 与成本没有被运行产物可靠记录，因此明确记为 unavailable。数据库更新时间跨度包含
失败重试、暂停和退避，不能冒充真实运行耗时。

## 可信度边界

本轮逐项判定由同一 Codex 做一次来源证据审查，没有调用外部模型，也没有使用图数据库内部 judge 的
标签作为最终答案。没有独立模型复审或人工校准，所以置信区间只表达抽样不确定性，不包含裁判偏差；
该结果适合作为工程诊断和后续回归基线，不应包装成已完成人类标注验证的论文结论。

## 复现

```bash
.venv/bin/python -m llm_graph_benchmark adapt-llmkg-sqlite \
  --db ../llm-knowledge-graph/tmp/d2l-full1105-c6-20260817-193600.db \
  --out-dir outputs/d2l-full1105-vnext-20260826 \
  --benchmark-id d2l-fullbook-v1 \
  --system-id llm-knowledge-graph-full1105-vnext \
  --system-name "LLM Knowledge Graph" \
  --system-version 1aed294+scopefix-23ce92989484 \
  --fact-probes examples/d2l-book-v1/fact_probes.jsonl \
  --qa-probes examples/d2l-book-v1/qa_probes.jsonl \
  --chunk-chars 8000 --overlap-chars 500

.venv/bin/python studies/d2l-open-baselines-20260820/evaluate_submission.py \
  --benchmark outputs/d2l-full1105-vnext-20260826/benchmark.json \
  --submission outputs/d2l-full1105-vnext-20260826/submission.json \
  --out-dir outputs/d2l-full1105-vnext-20260826/evaluation

.venv/bin/python studies/d2l-fullbook-vnext-20260826/build_results.py
```
