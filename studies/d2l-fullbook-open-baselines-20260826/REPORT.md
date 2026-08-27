# D2L 全书图谱：四方对比（llm-knowledge-graph / KGGen / GraphRAG Fast）

评测日期 2026-08-26。四份提交跑在同一份语料（`source_content_hash`
`sha256:9b57a1ce…`，1105 个 chunk）、同一份 benchmark（`d2l-fullbook-v1`，48 条冻结事实 +
24 道 Book QA）、同一个检索器（`char-ngram-bm25-v1`，top_k=10）。

## 结论

llm-knowledge-graph 在**每一个逐项质量维度上都领先**，但它和 KGGen 处在两个不同的工作点：
LKG 图小而准，KGGen 图大而糙。按「通过率 × 规模」折算成可用产出，KGGen（修正 dedup 后）
的接地断言数量是 LKG 的 7 倍。GraphRAG Fast 不构成可比对象。

本轮同时暴露了一个配置级缺陷：**KGGen 默认的 SemHash 去重在中文语料上会摧毁图**，
详见「KGGen 的 dedup 缺陷」一节。KGGen 因此有两列：`semhash`（默认配置）和
`exact`（关闭语义去重后从同一批原始抽取重新聚合）。

## 判定结果

裁判 `minimax-m3-source-grounded-v2`，888 个任务一次判完，temperature 0，并发 6。
分母为 decided（排除 uncertain）。

| 维度 | LKG | KGGen (semhash) | KGGen (exact) | GraphRAG Fast |
|---|---:|---:|---:|---:|
| entity_admission | **26/29 (89.7%)** | 8/29 (27.6%) | 9/28 (32.1%) | 5/29 (17.2%) |
| entity_typing | **22/27 (81.5%)** | 1/23 (4.3%) | 2/28 (7.1%) | 5/22 (22.7%) |
| entity_definition_grounding | **18/29 (62.1%)** | 2/25 (8.0%) | 1/24 (4.2%) | 2/25 (8.0%) |
| assertion_grounding | **28/30 (93.3%)** | 4/30 (13.3%) | 18/29 (62.1%) | 13/27 (48.1%) |
| alias_identity | **29/30 (96.7%)** | — | — | — |
| identity_split | **27/30 (90.0%)** | 4/19 (21.1%) | 0/23 (0.0%) | — |
| fact_recovery | **23/48 (47.9%)** | 0/48 (0.0%) | 3/48 (6.3%) | 4/48 (8.3%) |
| book_qa | **13/24 (54.2%)** | 1/24 (4.2%) | 3/24 (12.5%) | 8/24 (33.3%) |
| **合计** | **186/247 (75.3%)** | 20/198 (10.1%) | 36/204 (17.6%) | 37/175 (21.1%) |

30 个样本的 95% CI 约 ±15 个百分点，48 个样本约 ±13。因此 7.1% vs 4.2% 这类差距
在统计上区分不开，不应据此排名。

## 结构与规模

| | LKG | KGGen (semhash) | KGGen (exact) | GraphRAG Fast |
|---|---:|---:|---:|---:|
| 实体 | 2,140 | 7,511 | **13,555** | 270 |
| 断言 | 3,309 | 25,414 | **35,130** | 261 |
| 唯一谓词 | 919 | 2,272 | **6,500** | 1 |
| 实体证据覆盖 | 100% | 100% | 100% | 94.8% |
| 断言证据覆盖 | 100% | 100% | 100% | 85.1% |
| 孤立实体率 | 32.7% | 4.9% | **4.4%** | 44.8% |
| 最大连通分量 | 60.1% | **92.3%** | 89.3% | 17.8% |
| 别名 | **4,542** | 0 | 0 | 0 |
| 表面名重复组 | **0** | 151 | 543 | 0 |

## 通过率 × 规模：两个工作点

单看通过率会得出「LKG 全面碾压」，单看规模会得出「KGGen 覆盖远超」。两者要一起读：

| | 实体 × admission | 断言 × grounding |
|---|---:|---:|
| LKG | 2,140 × 89.7% ≈ **1,919** | 3,309 × 93.3% ≈ **3,088** |
| KGGen (exact) | 13,555 × 32.1% ≈ **4,357** | 35,130 × 62.1% ≈ **21,805** |
| KGGen (semhash) | 7,511 × 27.6% ≈ 2,072 | 25,414 × 13.3% ≈ 3,389 |
| GraphRAG Fast | 270 × 17.2% ≈ 47 | 261 × 48.1% ≈ 126 |

KGGen（exact）产出约 21,800 条接地断言，是 LKG 的 7 倍；代价是每 3 条里有 1 条不接地，
且完全没有类型、定义和身份层。选哪个取决于下游能否承受噪声：需要高精度直接消费选 LKG，
需要广覆盖再过滤选 KGGen。

## KGGen 的 dedup 缺陷

KGGen 0.4.0 默认的 `DeduplicateMethod.SEMHASH` 用 SemHash（model2vec 英文嵌入）
做语义去重。中文串在该嵌入空间里没有有效区分，0.95 阈值下互为重复：

```
16 个中文谓词  → selected 4 个
   使用/包含/属于/用于/提供/调用/涉及/计算/返回/应用于/等待/被称为 → 全部合并进「是」
10 个对应英文谓词 → selected 10 个，零合并
```

在全书 1105 chunk 上的后果：

| | 原始抽取 | semhash 之后 |
|---|---:|---:|
| 关系数 | 36,289 | 25,414 |
| 唯一谓词 | 6,602 | 2,272 |
| 谓词 `等待` 出现次数 | 9 | **12,764（占 50.2%）** |

半数断言的谓词被替换成了一个无意义的词。这直接压垮了 assertion_grounding（13.3%）和
fact_recovery（0%）。

这不是本仓库兼容补丁引入的：`run_kggen.py` 的 `install_semhash_compatibility()` 只是把
SemHash 0.3.2 的 `result.filtered` 映射回 KGGen 期望的 `result.duplicates`，逻辑与
`kg-gen/src/kg_gen/utils/deduplicate.py:45-90` 逐行一致。`DeduplicateMethod.FULL` 内部
也先跑 semhash，同样受影响。

修正方式：`run_kggen.py` 新增 `--dedup-method {semhash,exact}`（默认仍为 `semhash`）。
`exact` 跳过语义去重，只保留聚合阶段本就有的精确字符串合并，从已保存的
`chunks/*.json` 重新聚合，耗时 3.2 秒，无需重新调用 LLM。

修正后 assertion_grounding 从 13.3% 升到 62.1%，但 identity_split 从 21.1% 降到 0%——
`exact` 不做任何身份消解，`valid_loss` 与 `valid loss`、`Model` 与 `model` 被判定为
应合并而未合并。这是诚实的取舍，不是提分。

## 读数限制

**一、部分维度实际在测「有没有这个字段」。** KGGen 的 `types` 为空、definition 恒为
「（该方法未输出实体定义）」，GraphRAG 同理。因此 entity_typing 和
entity_definition_grounding 上的低分应读作能力缺失，而非标注错误。assertion_grounding、
fact_recovery、book_qa 不受此影响。

**二、fact_recovery 的评分口径对大图不利。** 该维度要求「恢复事实且不添加证据外内容」，
而检索固定取 top-10。图越大，top-10 越容易混入无关断言。KGGen（exact）多条 fail 的理由
是「候选 3-10 添加了证据未支持的内容」，尽管候选 1-2 已正确覆盖事实。该口径需要在后续
版本中区分「未能恢复」与「恢复了但夹带噪声」。

**三、裁判是被评系统的生成模型。** MiniMax-M3 同时生成了 LKG 和 KGGen 两张图，对这两者
属于自评；GraphRAG Fast 不使用 LLM 抽取，对它是外部裁判。在 LKG 的 252 个任务上，
本轮 M3 判定与上一轮 Codex 判定（`codex-source-grounded-fullbook-v1`，相同 task_id）的
一致性为：

```
agreement = 0.845    Cohen's kappa = 0.538
混淆: pass→pass 181 | fail→fail 32 | pass→fail 29 | fail→pass 5 | pass→uncertain 5
```

M3 判自己生成的图比 Codex **更严**，而非更松（29 条被翻成 fail，反向仅 5 条），分歧集中在
entity_definition_grounding（90%→60%）与 fact_recovery（75%→48%）。这不能推广到 KGGen
——需要 Codex 交叉判定 KGGen 的 222 个任务才能确认。

**四、非严格盲评。** 任务已打乱且不显示 system_id，但图的形态本身泄露身份（只有 LKG 有
别名，GraphRAG 谓词恒为单一值）。记为 system-anonymized，不是盲评。

**五、无人工校准。** 置信区间只表达抽样不确定性，不包含裁判偏差。本结果适合作为工程诊断
与回归基线，不应作为已完成人工标注验证的结论使用。

## 效率

| | LKG | KGGen | GraphRAG Fast |
|---|---:|---:|---:|
| 抽取耗时 | unavailable | 68,232s chunk 累计（6 worker，墙钟约 6h） | 73.6s |
| 输入 token | unavailable | 3,285,694 | 未记录 |
| 输出 token | unavailable | 6,264,623（含 reasoning 3,486,058） | 未记录 |
| 成本 | 无权威单价 | 无权威单价 | 0（fast 模式不调 LLM） |

LKG 的数据库时间跨度为 190.8 小时，但包含失败重试、暂停与退避，不能充当运行耗时，
因此记为 unavailable。KGGen 两列共用同一批抽取，效率数据相同；`exact` 的重新聚合额外
耗时 3.2 秒。

## 复现

```bash
# KGGen：从已保存的原始抽取重新聚合（不重新调用 LLM）
/home/likefallwind/code/llm-graph-baselines/kg-gen/.venv/bin/python \
  studies/d2l-open-baselines-20260820/run_kggen.py \
  --corpus outputs/d2l-fullbook-open-baselines-20260826/corpus/chunks.jsonl \
  --benchmark-id d2l-fullbook-v1 --document-id d2l-zh-official \
  --kggen-repo /home/likefallwind/code/llm-graph-baselines/kg-gen \
  --out-dir outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105-exactdedup \
  --model openai/MiniMax-M3 --api-base https://api.minimaxi.com/v1 \
  --api-key-env MINIMAX_API_KEY --system-id kggen-minimax-m3-exactdedup \
  --max-tokens 8192 --dedup-method exact --workers 6

# 生成评测任务
.venv/bin/python studies/d2l-open-baselines-20260820/evaluate_submission.py \
  --benchmark outputs/d2l-full1105-vnext-20260826/benchmark.json \
  --submission <run>/submission.json --out-dir <run>/evaluation

# 四方混合判定
bash studies/d2l-fullbook-open-baselines-20260826/run_judge_v2.sh
```

判定产物：`outputs/d2l-fullbook-judge-v2-20260826/`
（`judgments.jsonl`、`pool-map.json`、`judge-report.json`）。
