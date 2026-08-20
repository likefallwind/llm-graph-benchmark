# D2L 历史图谱快照完整评测（pilot）

## 结论

本轮覆盖 Entity 准入、类型、定义、Assertion、事实完整性、身份解析、Book QA、结构、跨运行
稳定性、效率和裁判一致性，不再只是三个指标。

| 语义维度 | exact27 | fresh200 |
|---|---:|---:|
| Entity admission | 30/30 (100.0%; 88.6%–100.0%) | 30/30 (100.0%; 88.6%–100.0%) |
| Entity typing | 25/30 (83.3%; 66.4%–92.7%) | 23/30 (76.7%; 59.1%–88.2%) |
| Entity definition grounding | 16/30 (53.3%; 36.1%–69.8%) | 23/30 (76.7%; 59.1%–88.2%) |
| Assertion grounding | 27/30 (90.0%; 74.4%–96.5%) | 29/30 (96.7%; 83.3%–99.4%) |
| Alias identity | 30/30 (100.0%; 88.6%–100.0%) | 29/30 (96.7%; 83.3%–99.4%) |
| Identity split correctness | 2/2 (100.0%; 34.2%–100.0%) | 13/14 (92.9%; 68.5%–98.7%) |
| Fact recovery（当前覆盖范围） | 0/1 (0.0%; 0.0%–79.3%) | 3/7 (42.9%; 15.8%–75.0%) |
| Book QA（当前覆盖范围） | 0/1 (0.0%; 0.0%–79.3%) | 2/6 (33.3%; 9.7%–70.0%) |

最强项是 Entity admission 与 Assertion grounding；主要弱项是定义证据化、事实完整恢复和 Book QA。
内部 checker 提升了单条精确性，但没有解决遗漏、组合事实和定义外加知识。

`exact27` 仅覆盖 48 条 fact probes 中 1 条和 24 道 QA 中 1 道；`fresh200` 分别覆盖 7 条和
6 道。分母不同，不能把 completeness/QA 当作两系统排名。

## 身份与结构

| 快照 | Entity | Assertion | 孤立率 | 模糊表面词组 | 涉及 Entity | 表面重复组 |
|---|---:|---:|---:|---:|---:|---:|
| exact27 | 132 | 76 | 40.9% | 2 | 4 | 0 |
| fresh200 | 603 | 625 | 33.0% | 12 | 25 | 1 |

典型身份错误包括把特定 `DataLoader` 当作通用跨框架数据迭代器别名，以及把定义相同的随机梯度
下降/小批量随机梯度下降拆成两个实体。同名但应分开的 Torch/PyTorch、数学 Variable/tf.Variable、
求导/概率 sum rule 等则被正确保留。

## 跨运行稳定性

以 exact27 的 164 个 Source Passage 为共同范围：Entity 规范名 Jaccard
为 34.7%，reference retention 为 52.3%；
名称+别名词表 Jaccard 为 40.1%。完整 Assertion 三元组
Jaccard 为 4.3%，reference retention 为 7.9%，
只看有向端点对 Jaccard 为 12.4%。

精确性虽高，但不同运行抽取对象与关系表达仍不稳定；正式对比必须冻结模型、prompt、chunk 和随机参数。

## 效率与成本

| 快照 | observed wall span | chunk/hour | Entity/hour | Assertion/hour | Token/成本 |
|---|---:|---:|---:|---:|---:|
| exact27 | 2.16 h | 12.48 | 61.03 | 35.14 | unavailable |
| fresh200 | 44.62 h | 4.48 | 13.51 | 14.01 | unavailable |

SQLite 时间戳只能恢复包含暂停和退避的 observed wall span，不能冒充 active runtime。历史库未保存
token/cost，因此明确记为 unavailable；框架已支持后续提交这些字段及单位产出成本。

## 裁判一致性与可信度

本轮全部 331 个任务都进行了同一 Codex 的第二次反序复核，并保存 pairwise agreement
和 Cohen's kappa。边界分歧集中在宽泛类型、常识性定义补充和框架专用别名。这只能说明同模型重复
稳定性，不是独立模型或人工校准。

没有人工标签，human calibration 明确为 `unavailable-no-human-labels`，没有伪造分数。正式论文只需
从失败、分歧和随机通过项抽少量样本校准，不需要标完整本书。

## 主要诊断

- 类型：通用对象被错标为 data/deep-learning-model/computing-operation，或带不兼容附加类型。
- 定义：从符号表、代码调用或一句提及扩写出原文未支持的机制和背景知识。
- Assertion：从集合性表述投射到具体对象、关系方向失真、从符号邻接构造伪关系。
- 完整性/QA：组合组件不全、关键条件或原因缺失、一般定义只恢复成特例。
- 稳定性：同一输入范围两次运行的规范名和完整三元组重合度偏低。

优化优先级应是：定义证据约束 > 组合事实与条件保留 > Entity 类型清理 > 跨运行规范化；
而不是继续只提高已经很高的单条 Assertion 支撑率。
