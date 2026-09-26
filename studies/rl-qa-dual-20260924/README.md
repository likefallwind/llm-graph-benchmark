# 强化学习 QA 双指标试评

仅处理讨论中的第一项 QA。固定四方法原来的 24 道题、参考答案、来源和 Top10 图候选；不改构图、检索或其他指标，不覆盖历史结果。

`book-qa-dual-v2` 先制定方法无关的来源侧答案要点，再对完整断言逐要点核验。四方法共享同一题的要点，核心支持与完整支持由程序分别聚合。完整断言包含主语、谓词、宾语、原生文本、条件范围和肯否定，不再按500字符截断。

运行目录：`outputs/rl-qa-dual-20260924`。官方 MiniMax-M3，temperature=0，4并发，与现有工作流共用请求槽；120次计划调用（24份要点、96份判断），实际调用含技术重试。首个有效输出缓存，不按标签好坏重试。

```bash
PYTHONPATH=src .venv/bin/python studies/rl-qa-dual-20260924/run.py prepare
PYTHONPATH=src .venv/bin/python studies/rl-qa-dual-20260924/run.py rubrics
PYTHONPATH=src .venv/bin/python studies/rl-qa-dual-20260924/run.py run
# 仅补技术失败
PYTHONPATH=src .venv/bin/python studies/rl-qa-dual-20260924/run.py run --retry-failed
```

`qa-requirements.json` 保存评分前固定的共用要点；`previous-qa.json` 绑定历史判定及候选哈希；`COMPARISON.md` 展示新旧结果；`CASE_REVIEW.md` 展示每题各要点及图谱引文；`api/` 保存原始请求、响应和实际用量。

测试与引文校验只能验证程序约束。要点是否合理、引文是否真正支持结论需另行语义审查。本轮沿用原检索和题集，不能据此解决跨语言检索或题集代表性问题。
