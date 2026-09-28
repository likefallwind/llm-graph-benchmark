# 第二本书：强化学习统一重评（最终结果）

2026-09-28 实体拆分退役，由语义重复率取代；当前 RL 总表见 [sutton-barto-semantic-duplicate-20260928](../sutton-barto-semantic-duplicate-20260928/README.md)。本目录其余指标不变，下表中的实体拆分行为历史口径。

四个方法在同一次运行里按 selected-metrics-v5-identity-sources 评测，使用重抽原文；拆分为 split-legacy-full-sources-knowledge-v3。
来源运行目录 `outputs/rl-rerun-fontfix-20260926-r3`（不入库），配置与过程说明见 [studies/rl-rerun-20260926](../../studies/rl-rerun-20260926/README.md)。

REPORT.md 为完整表格，comparison.csv 为表格文件，summary.json 为机器可读分数，case-results.json 为逐项判定（含裁判看过的原文段落），
manifest.json、config.json、prompts.json、sampling.json、systems.json、structure.json 记录冻结的协议、提示、抽样、检索与结构统计。

有效任务 3,269/3,272，报告中两格为"未完成"：
- GraphRAG 完整断言 198/200：两条 45 次尝试均无合格输出，记为技术失败未评；按已评部分 88.4%（175/198），缺项全对或全错时为 87.5%–88.5%。
- KGGen 别名 29/30：一条原文超 350KB 上限，未评；按已评部分 89.7%（26/29），区间 86.7%–90.0%。

本方法是跨书增量图谱的 RL 子图，基线只读强化学习书。本目录取代 sutton-barto-20260923 与 sutton-barto-baselines-20260923 作为 RL 的当前结果；两者保留为历史记录。

`raw/` 保存可逐条复核的原始记录（压缩后入库，tasks.json 原文件 119MB 超过 GitHub 单文件上限）：
- r3-tasks.json.gz：最终运行冻结的全部任务及发给裁判的完整消息。
- r1/r2/r3-run-records.tar.gz：三个运行目录（首次运行、-r2、-r3）除 tasks.json 外的全部内容，含逐任务结果、API 请求与原始返回、技术重试存档、运行与看守日志。最终结果中 1,392 条来自首次运行、其余来自 -r2，拆分 120 对与 3 条断言重试来自 -r3。-r1/-r2 的 tasks.json 与 r3 仅拆分任务不同（v2 提示），未另存。
入库前用实际 API 密钥扫描，未命中。
