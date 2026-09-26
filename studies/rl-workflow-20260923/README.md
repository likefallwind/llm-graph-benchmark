# 第二本书：Sutton–Barto 强化学习评测

使用固定 selected-metrics-v1 工作流评估现有图谱，不重构图。

## 图谱与来源范围

- 原始运行：llm-knowledge-graph/tmp/rl-full-structured-m3-official-c6-20260912/full.db，source_id=2。
- 该运行来自 D2L 种子库的增量构图；仅评估强化学习书对应的 1,354 个实体、2,708 条完整 Assertion，不把双书合计规模当成本书规模。
- 111 个实体带跨书原生引用。实体定义、类型、别名按数据库当前原生内容导出；引用合并该实体所有原始 Observation 与 Evidence 的声明来源，保留原文。
- D2L 原文作为引用上下文保存在同一评测文档，unit_id 按来源前缀隔离；不加入 D2L 图谱对象、不为 D2L 生成 QA/事实探针。
- SQLite 以只读 immutable 模式打开；要求 WAL 为空，导出前后校验数据库 SHA256。原库不修改。
- 构图资源采用原运行及恢复日志中的成功响应汇总：输入 465.142485M、输出45.316314M，总计510.458799M；不包含此次评测调用，也不等于完整失败请求或货币账单。

## 来源侧基准

17章固定随机种子20260923，先选章节中的说明性原文窗口，再由 MiniMax-M3 生成48条事实与24道QA。
每个事实窗口一条事实；题目、答案、事实及必要条件仅依据原文，不向生成器展示图谱、旧评价或预期答案。
引用编号及来源窗口须匹配冻结输入，真正证据由程序按编号取回完整原文；模型抄写的引用文本仅作审计，不能充当原文。题数、编号与来源窗口覆盖也由程序检查。
初稿与原响应保留；10项引用抄写失败从原响应本地恢复，未新增调用、未改写事实或答案。随后在图谱评分前按原文修正11处基准表述/条件问题，来源窗口未变。最终版见 BENCHMARK_REVIEWED.md、benchmark-provenance-reviewed.json 与 benchmark-editorial-audit.json。

此基准为自动生成并作格式/原文引用校验，尚非人工金标准。书籍抽取文本已知存在部分数学符号丢失；
本轮测量对冻结解析文本的支持，不能替代对 PDF 公式保真的检查。
检索仍为原工作流的 BM25 Top10，未为跨语言输出特别调参。

## 执行

prepare_book.py 只读导出并冻结来源与图谱，已经执行，不能覆盖现有冻结目录。
run_pipeline.py 生成/复用来源基准，准备统一工作流，然后执行；提供 --prepare-only 时在评测前停止。
MiniMax-M3、temperature=0，基准生成与正式工作流共享同一套最多6个 HTTP 请求槽。

运行目录：outputs/rl-book2-20260923。
- pipeline-state.json / pipeline.log：总体阶段与日志。
- benchmark-generation/：原始模型请求、响应及冻结来源题。
- evaluation-reviewed-v1/：正式工作流任务、分数、报告和逐项明细；evaluation/ 是未执行评分的题目初稿准备目录。
- 正式评测完成后自动保存到 results/sutton-barto-20260923。

第一本书已独立保存于 results/d2l-20260923，包括 Markdown、CSV、JSON、来源哈希及类型裁判审计。
第二本书文件不覆盖第一本书，跨书比较需说明构图方式、来源语言与基准差异。

查看正式任务进度（准备完成后）：

    llm-graph-benchmark workflow status --run outputs/rl-book2-20260923/evaluation-reviewed-v1

技术失败恢复：

    python studies/rl-workflow-20260923/run_pipeline.py --retry-failed

已有有效语义标签原样复用。基准生成若遭供应商账户错误，修复环境后需显式归档其 terminal-error.json 再恢复；
不得因得分或结果不符合预期而重新生成题目或裁判标签。


正式后台启动器为 launch_evaluation.py；932个任务，预期首轮模型调用1132次（断言采用既定的两步核对），实际调用另计缓存与技术重试。不要重复启动。

## 2026-09-23 英文句点解析修复

正式运行现在位于 `outputs/rl-book2-20260923/evaluation-reviewed-v1-periodfix/`。
旧 `evaluation-reviewed-v1/` 保留不覆盖。提示词、抽样、证据、分母和语义评分规则均未改变。
解析器允许省略原描述中句末英文句点（后接空白或全文结尾），仍拒绝小数点、名称内部句点、漏字、改写、重复和乱序。
迁移原样保留 912 个成功结果；对 20 个失败案例按请求时间选择第一个能通过修复后校验的原始返回，离线恢复 16 个，剩余 4 个后台重新请求。
选择不参考 pass/fail 标签，审计在新运行的 `parser-recovery-audit.json`；旧清单在 `parent-manifest.json`。
