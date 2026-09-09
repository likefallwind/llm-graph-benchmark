# MiniMax 官方评分运行

- 模型：MiniMax-M3；全局并发上限：6。
- 地址：`https://api.minimaxi.com/v1/text/chatcompletion_v2`。
- 任务：1480；三个评分维度分别记录。旧样本、候选和历史判断保持不变。
- tmux：`bench-quality-m3-c6-20260907-162620`。
- 运行目录：`/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-quality-m3-official-c6-20260907-162620`。
- 配置、代码快照与输入哈希：`launch.json`、`run-config.json`、`source/`。
- 进度及完成依据：`summary.json` 的 `status`、`scored/total`，配合 `.exit` 和 `.finished`。
- 日志：`run.log`；每次原始响应：`responses/`；可恢复单项记录：`results/`。
- 自动汇总：`judgments.jsonl`、`metrics.json`、`paired-comparisons.json`、`REPORT.md`。

本文只记录启动配置，不宣称评分已经完成。单模型新评分仍不等于独立校准。
重试会保留每次响应和 token 用量。鉴权/余额/用量上限等终止错误会停止派发；失败任务保持可恢复。

如本轮退出，先核实没有同目录运行进程，再在已配置 MINIMAX_API_KEY 的环境恢复：

```bash
bash /home/likefallwind/code/llm-graph-benchmark/outputs/d2l-quality-m3-official-c6-20260907-162620/run.sh
```

恢复只处理未成功任务；输入、评分参数与源码指纹不同会拒绝复用缓存。

## 并发 4 续跑（20260907-174524）

用户要求将本评分进程并发从 6 降到 4。原 c6 运行已退出；保留原目录，新目录复制相同任务、源码与原始响应，复用 286 项成功评分。仅变更 workers，详细缓存哈希和前序配置见 `resume-lineage.json`。

- 当前 tmux：`bench-quality-m3-c4-20260907-174524`。
- 当前运行目录：`/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-quality-m3-official-c4-20260907-174524`。
- 本评分进程并发上限：4；不构成跨项目或账户总并发限制。
- 续跑命令：`bash /home/likefallwind/code/llm-graph-benchmark/outputs/d2l-quality-m3-official-c4-20260907-174524/run.sh`。
- 完成依据仍为 `summary.json`、`.exit` 与 `.finished`。
