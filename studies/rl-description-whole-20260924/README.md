# 强化学习整段描述支持试评

仅重评 entity_description，MiniMax-M3，temperature=0，并发6。
沿用四方法已完成的强化学习评测实体样本、原生描述与全部提交证据，不截断或重新抽样。
本方法与 GraphRAG 各100条，AutoSchemaKG 与 KGGen 无原生描述，记 N/A。
每条返回 supported / not_supported / uncertain 之一；支持数除以有描述样本数。
不确定保留在分母；技术失败保持未评。历史分段分数不能直接作为新分数。

准备（无API调用）：

```bash
PYTHONPATH=src .venv/bin/python studies/rl-description-whole-20260924/prepare.py
```

新目录 outputs/rl-description-whole-m3-c6-20260924 保留冻结输入、历史结果映射与代码快照。
在继承 MINIMAX_API_KEY 的 detached tmux 中运行该目录的 background.sh。
worker.log、state.json、progress.json 记录进度，.started / .exit / .finished 记录启动、退出和成功。
最终结果为 REPORT.md / comparison.csv / summary.json / case-results.json。
旧运行和历史报告均不覆盖。
