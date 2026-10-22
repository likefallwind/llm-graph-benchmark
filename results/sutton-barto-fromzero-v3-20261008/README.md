# 第二本书：强化学习从零构图（pipeline-v3）

llm-knowledge-graph pipeline-v3 只读强化学习书构图（1,268 实体、2,707 断言），按当前协议（selected-metrics-v7-two-level-types）评测。基线其余指标未重跑，沿用 [RL 统一重评](../sutton-barto-rerun-20260926/README.md) 与 [语义重复](../sutton-barto-semantic-duplicate-20260928/README.md)；类型按两级粒度对五列全部重判。配置与复现见 [studies/rl-fromzero-v3-20261008](../../studies/rl-fromzero-v3-20261008/README.md)。

|指标|从零构图|跨书增量（参考）|GraphRAG|AutoSchemaKG|KGGen|
|---|---:|---:|---:|---:|---:|
|完整断言正确率|未完成（198/200）：已判 94.4%，区间 93.5%–94.5%|94.0%|未完成：88.4%|70.5%|67.5%|
|具体且正确覆盖|未完成：区间 86.5%–87.5%|88.5%|未完成|57.0%|55.5%|
|实体所指 / 引用支持|100% / 99%|100% / 98%|100% / 97%|98% / 96%|89% / 87%|
|类型兼容正确率|83.7%|84.9%|92.9%|80.0%|N/A|
|正确且 L2 类型覆盖（两级）|60%|68%|4%|67%|N/A|
|整段描述支持率|81%|84%|91%|N/A|N/A|
|别名同一性|96.7%（29/30）|96.7%|N/A|N/A|未完成：89.7%|
|语义重复率（越低越好）|4.0%（4/100）|5.0%|37.0%|42.0%|54.5%|
|事实探针覆盖（参考）|58.3%（28/48）|52.1%|77.1%|81.3%|37.5%|
|构图总 Token（million）|N/A|510.5|9.7|27.3|25.5|

完整对照见 REPORT.md / comparison.csv；summary.json 为本方法合成分数，baseline-summary.json 为另外四列的合成分数；main/、stage/、types/ 为本方法主运行、语义重复阶段、类型重判阶段，baseline-types/ 为另外四列的类型重判阶段，各含报告、逐项判定、冻结配置与提示；raw/ 为这些运行目录的全部记录（含原始请求与返回，入库前用实际 API 密钥扫描，未命中）。

说明：
- 完整断言 2 条技术失败未评（a1090、a1066，均为 L3）：实体名 "Mean square value error (VĒ)" 中 Ē 是 E+组合长音符（U+0304），裁判复制时一律写成预组合 Ē（U+0112），完整复制校验不做 Unicode 规范化而拒收，3 轮共 9 次均如此，重试无效。已判 198 条：正确 187、错误 3、不确定 8。
- 另有 4 条技术失败（输出未通过格式校验）经 --retry-failed 补判成功，成功结果未重跑。
- 语义重复：20 个目标留下 24 对，判同指 4 对：Planning methods / Planning、Invariant updates / Importance weight aware updates、Mukundan and Martínez (2012) / MORSE、Actor-critic methods / Actor-critic architecture。
- 类型粒度改为两级（L1 泛类 / L2 具体类别，type-boundary-v3-two-level），只评价标签本身，不把实体的具体程度算到标签上。400 个类型任务（四列各 100，KGGen 无类型）全部判完，无技术失败；兼容性判法未变，兼容正确率与旧版相差不到 2.5 个百分点。
- 两级口径下泛标签已稳定：algorithm 9 次、method 22 次、concept 77 次全判 L1（旧版 algorithm 曾被判 L1/L2/L3）。仍不稳定的是"领域名当类型"一类标签，如 reinforcement learning（L1 10 次 / L2 13 次）、强化学习概念、learning algorithm。L2 只来自这类标签的实体：从零 18、跨书 4、GraphRAG 2、AutoSchemaKG 6，即从零构图的 L2 覆盖实际在 42%–60% 之间。
- 构图 Token 未记录（pipeline-v3 不写用量日志）。
- 与跨书增量列不是同一图、各自抽样，细小差距不足以判断优劣。
