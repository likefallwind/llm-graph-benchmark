# D2L 历史图谱快照评测（pilot）

## 结论

两份历史快照表现出相似的模式：抽出的 Entity 基本都值得进入图谱，Assertion 的原文
支撑率也很高；当前最明显的短板是**事实完整恢复**，而不是“图里多数内容是错的”。

| 快照 | 已处理 chunk | Entity admission | Assertion grounding | Fact recovery（当前覆盖范围） |
|---|---:|---:|---:|---:|
| exact27 | 27 | 30/30 (100.0%; 95% CI 88.6%–100.0%) | 27/30 (90.0%; 95% CI 74.4%–96.5%) | 0/1 (0.0%; 95% CI 0.0%–79.3%) |
| fresh200 | 200 | 30/30 (100.0%; 95% CI 88.6%–100.0%) | 29/30 (96.7%; 95% CI 83.3%–99.4%) | 3/7 (42.9%; 95% CI 15.8%–75.0%) |

`exact27` 只覆盖 48 条冻结探针中的 1 条，`fresh200` 只覆盖 7 条，因此两者的 fact recovery
分母不同，**不能把 0/1 与 3/7 当作严格的系统间排名**。它们只能评价各快照已处理范围。

## 结构与规模

| 快照 | Entity | Assertion | Entity evidence | Assertion evidence | 孤立 Entity 比例 | 表面重复组 |
|---|---:|---:|---:|---:|---:|---:|
| exact27 | 132 | 76 | 100% | 100% | 40.9% | 0 |
| fresh200 | 603 | 625 | 100% | 100% | 33.0% | 1 |

规模不是质量分数。fresh200 从 27 增长到 200 个 chunk 后，Entity/Assertion 数量显著增长，
证据覆盖仍为 100%，盲样本 Assertion grounding 没有随规模下降。

## 主要错误

- exact27 的 Assertion 错误包括：从符号表构造出不存在的“记法采用”关系，以及把“代码散见于博客
  和 GitHub”过度投射成 GitHub 分别托管 LeNet、AlexNet。
- fresh200 的 Assertion 错误是关系方向失真：原文的 `P(A)` 表示事件 A 的概率，不等于“概率以
  随机事件为记号”。
- fresh200 的 4 个 fact recovery 失败分别是：四个机器学习核心组件只恢复了一部分、线性模型的
  正负权重单调方向缺失、MNIST“过于简单”的选择理由缺失、回归的一般定义缺失。
- Entity admission 并不等于类型准确率。盲样本中可见 LaTeX/GitHub、TensorFlow Variable、
  对称矩阵等对象带有可疑的额外类型；这应在下一版增加独立 `entity_typing` 指标，不能事后混入
  已冻结的 admission 尺度。

## 协议

- 输入：同一本 D2L 中文版，源文本 SHA-256
  `9b57a1cead18be493ddbf26a62d09031a85c3a7261306648c1a5c2fc93a68e76`。
- 精确性侧：每个快照以 seed `20260820` 固定抽取 30 个 Entity 和 30 个 Assertion，系统身份
  不出现在公开任务中；本次 120/120 均已裁判。
- 完整性侧：使用独立从原文冻结的 48 条分层 fact probes；只在快照已处理 passage 范围内出题。
- 检索：统一使用 `char-ngram-bm25-v1(top_k=10,k1=1.2,b=0.75)`，只索引图谱 Assertion 的
  subject、predicate、object、text、scope，不读取原文 passage 或 evidence。
- 内部 LLM checker 是被评系统的一部分；上述盲评是统一的外部结果裁判，没有重复调用抽取 API。

## 可信度边界

这是**同一强模型完成策展与裁判的自评 pilot**，没有独立人类校准，不能宣称人工金标准。
Wilson 区间已报告，但小样本 fact recovery 区间很宽。两份数据库也只是书籍前 27/200 个 chunk 的
历史快照，不是全书最终分数。事实恢复分数同时受图谱和统一检索器影响；后续应在人类校准小样本上
验证检索器，并加入其他提取系统后再做正式横向比较。

本轮结果足以验证 benchmark 可以端到端评价真实历史图谱，也给出明确诊断：优先提升跨 Assertion
组合、条件/理由保留和一般定义覆盖；不应只继续优化单条 Assertion 的证据支撑率。
