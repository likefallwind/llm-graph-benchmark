# 第二本书：强化学习统一重评（最终结果）

四个方法在同一次运行里按 selected-metrics-v5-identity-sources 评测，使用重抽原文；拆分为 split-legacy-full-sources-knowledge-v3。
来源运行目录 `outputs/rl-rerun-fontfix-20260926-r3`（不入库），配置与过程说明见 [studies/rl-rerun-20260926](../../studies/rl-rerun-20260926/README.md)。

REPORT.md 为完整表格，comparison.csv 为表格文件，summary.json 为机器可读分数，case-results.json 为逐项判定（含裁判看过的原文段落），
manifest.json、config.json、prompts.json、sampling.json、systems.json、structure.json 记录冻结的协议、提示、抽样、检索与结构统计。

有效任务 3,269/3,272，报告中两格为"未完成"：
- GraphRAG 完整断言 198/200：两条 45 次尝试均无合格输出，记为技术失败未评；按已评部分 88.4%（175/198），缺项全对或全错时为 87.5%–88.5%。
- KGGen 别名 29/30：一条原文超 350KB 上限，未评；按已评部分 89.7%（26/29），区间 86.7%–90.0%。

本方法是跨书增量图谱的 RL 子图，基线只读强化学习书。本目录取代 sutton-barto-20260923 与 sutton-barto-baselines-20260923 作为 RL 的当前结果；两者保留为历史记录。
