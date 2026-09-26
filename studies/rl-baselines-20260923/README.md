# 强化学习书：顺序基线工作流

使用 `launch.py` 后台执行：本方法剩余评测 → GraphRAG 构图及评测 → AutoSchemaKG 构图及评测 → KGGen 构图及评测。
全部调用 MiniMax-M3 官方 API，temperature=0；构图与统一评测均最多 4 个实际并发请求（含重试）。三种方法不同时构图。

构图复用已纠正、固定提交的上游实现。GraphRAG 使用官方英文自动提示生成、标准 LLM 抽取及描述汇总；AutoSchemaKG 使用官方英文三阶段抽取和完整概念化；KGGen 重新抽取本书，再执行公开 LM_BASED 归一。无 D2L 抽取结果混入。
324 个共同片段覆盖 2,920 个强化学习原文单元，顺序拼接完整段落、目标 6,000 字符、不截断段落。构图不读取 QA 或事实答案。
本方法为跨书增量图，基线仅用强化学习书，此范围差异必须随结果报告，不能解释为等预算或完全相同构图条件。

评测直接使用新写的 `workflow.prepare/engine.execute/report`，共用已冻结的 48 个事实探针、24 道 QA；默认每方法 100 实体、200 断言、30 别名和 30 拆分样本。原生缺失字段 N/A；AutoSchemaKG 质量排除 event-participation 边，结构保留全抽取图，概念 schema 另存。
不调用旧 evaluate.py；所有成功标签原样保留。技术失败有限重试，凭证/额度异常或构图失败停止队列并写状态，不输出伪完整结果。

运行：`python studies/rl-baselines-20260923/launch.py`。凭证继承自环境。
进度：`outputs/rl-baselines-20260923/status.json`；日志为 `controller.log` 和各方法 construction 日志。
快照：`outputs/rl-baselines-20260923/source/`，启动时冻结并保存 SHA256，活动运行不可修改。
输出：每方法 `evaluation/REPORT.md`、`comparison.csv`、`summary.json` 和逐项结果；总表为 `RESULTS.md`。
自动归档：`results/sutton-barto-baselines-20260923/`。第一本书归档保持不变。

## 2026-09-24 Gateway 续跑

按用户指示改用本地 API Gateway `minimax-m3`，并发 6。入口为 `launch_gateway.py`。
来源快照独立保存为 `outputs/rl-baselines-20260923/source-gateway-c6`；冻结清单为 `launch-gateway-manifest.json`。
原生官方 API 的 2067 停止记录保留，Gateway 使用独立共享 6 请求槽。凭证在进程中从现有 Gateway 配置读取，不落入请求、日志或快照。
GraphRAG 与 AutoSchemaKG 的已有有效判定原样复制到 `evaluation-gateway-c6/`，只重试剩余项；KGGen 保留已完成逐片段抽取。原运行不覆盖。
Gateway 响应采用 OpenAI 兼容信封，严格校验返回模型与结束状态；允许移除完整 JSON 代码块外壳，不改标签/理由/证据。原始响应保留。
本轮报告属于官方 MiniMax 与 Gateway MiniMax 混合路由续跑，来源及用量须据原始请求记录追踪。

2026-09-24 后续切换：用户要求暂停 Gateway，已停止其控制器进程组；官方 MiniMax-M3 实测恢复成功。新入口 `launch_official_c4.py`，独立快照 `source-official-c4-resume`，并发 4。官方续跑评测目录为 `evaluation-official-c4-resume`，日志为 `controller-official-c4.log`。旧 Gateway 输出和原生构图检查点保留；KGGen 当前执行配置写入 `manifest-official-c4.json`。
