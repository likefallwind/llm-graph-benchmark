# 当前四方法工作流配置

workflow.json 指向本机已有四份正确复现的图谱及同一 D2L benchmark。
AutoSchemaKG 使用已约定的语义边子集进行质量评测，完整图计算结构；构图用量来自已冻结的2026-09-23汇总。
我们的构图 Token 未记录，显式保留 null。

```bash
llm-graph-benchmark workflow prepare \
  --config studies/current-evaluation/workflow.json --run outputs/d2l-workflow-new
```

这条命令只准备，不调用 API。只有明确执行 workflow run 或 launch 才会开始新评测。
此配置用于未来统一重跑或替换图谱输入，不继承本次历史混合来源的分数。
默认实体100、断言200、别名30，事实探针沿用48条；Book QA与实体拆分已从当前评测移除，语义重复作为单独阶段运行。
目前已有结果仍见 outputs/d2l-consolidated-results-20260923/REPORT.md。
