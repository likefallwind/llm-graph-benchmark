# 单条断言质量 v2.2 完整复跑

这是已有 Benchmark 的测量协议修订与一次描述性复跑，不是新的领域标准。
2026-09-09 已完成 [最终报告](RESULTS.md)：1000/1000 个有效判定，含 1 条解释文字引号的本地语法恢复；76 个软件测试通过。
已纳入版本管理的机器可读摘要见 [results-summary.json](results-summary.json)，格式恢复审计见 [syntax-recovery.json](syntax-recovery.json)。完整原始响应和逐条派生评分保留在本地 outputs，不随代码提交。
本方法历史 vNext 图联合通过 191/200（95.5%）；这是当前材料和裁判下的描述性结果。

## 版本链

- v1：单条准确性与来源完整性部分混淆；多候选恢复评分另保留。
- v2：允许合法拆分并列事实，明确必要限定；规则检查 25/26，指代歧义的标签边界存在分歧。
- v2.1：来源可读却不支持输出具体断言为 fail；缺失/不可读证据为 uncertain。规则检查 33/34，发现裁判将“包含”误读为“包含在”。
- v2.2：语义规则承接 v2.1；强制逐字回填主谓宾，分别返回 edge_label、description_label、condition_label，程序核对字段并汇总联合标签。34/34 开发规则检查通过。

旧规则常量、样例预期、运行快照和有效标签不覆盖。只对 API、解析或字段校验错误重试，不能重试有效判定直到符合预期。
规则检查是助手编写的开发样例，多轮结果全部报告；通过不证明裁判没有其他误判。

## 数据与复核

本次只发送此前已获用户授权的 1000 条历史断言及其完全相同的来源证据至 MiniMax 官方 API。
新增的 25 条自然样本在 v2.1 目录本地保留，不发送。自动审批曾拒绝包含新增自然样本的组合操作；
改为核对并只使用原有授权材料后，合成检查与完整复跑分别获准。

从原有 1000 条中每系统选 5 条，排除 95 条开发复核集和已经展示的案例。Codex 在看到本轮
MiniMax 标签之前冻结 25 条判断与哈希。这个面板是同书小规模模型间复核，不是独立人工金标准；
Codex 也是协议作者，一个长证据样本用全源词项搜索定位，四个边界案例已预先标记。
正式复跑全部使用同一 MiniMax-M3、temperature=0、max_tokens=8192、单进程并发=4；不设跨项目账户总并发保证。

## 可复现命令

```bash
PYTHONPATH=src python studies/d2l-quality-v22-20260908/prepare.py \
  --repo /home/likefallwind/code/llm-graph-benchmark \
  --out /tmp/a-fresh-v22-prepared-directory
```

准备脚本保护既有输出，保留旧版本任务内容核验、输入/输出哈希、抽样种子和私有映射。
`run.py --phase checks` 运行合成题；`run.py --phase full` 要求规则检查通过且已冻结 25 条本地复核。
默认从环境或用户 .bashrc 的静态 MiniMax 赋值加载密钥；不执行配置中的动态命令，不输出或写入密钥。
每个运行复制源码快照，保留请求结果、原始响应、尝试记录、输入/源码哈希及退出标记。
恢复只使用 `--resume <原运行目录>`，跳过有效语义标签，不覆盖旧响应。

```bash
python studies/d2l-quality-v22-20260908/run.py --phase full --resume /path/to/incomplete-run
PYTHONPATH=src python studies/d2l-quality-v22-20260908/analyze.py \
  --run /path/to/complete-run \
  --prepared outputs/d2l-quality-v22-20260908 \
  --previous outputs/d2l-quality-m3-official-c4-20260907-174524 \
  --out /path/to/fresh-analysis-directory
```

分析默认拒绝未完成运行；也拒绝重复/缺失标签、回填不符、分项与联合标签不符、源码快照变动、或晚于 API 启动才冻结的复核标签。

2026-09-09 重启最后 1 条后仍反复返回解释字符串内未转义的双引号，故增加显式离线选项 `--recover-reason-quotes`。
该选项仅处理已退出且无缺失条目的运行，并按时间顺序接受最早可恢复响应；解释前的评分字段必须已是合法 JSON，
随后用冻结的原始解析器重新验证所有字段。只补解释文字中必要的引号转义，不填分数、不修复三元组、不调用 LLM。
完整报告在新目录保存 `judgments.jsonl`、`syntax-recovery.json` 和 `.finished`。原运行的 999/1000、退出码 1、
全部错误及原始响应保留，不能把原始进程状态误读成派生报告未完成。

本次报告命令：

```bash
PYTHONPATH=src python studies/d2l-quality-v22-20260908/analyze.py \
  --run outputs/d2l-quality-v22-full-m3-c4-20260908-125935 \
  --prepared outputs/d2l-quality-v22-20260908 \
  --previous outputs/d2l-quality-m3-official-c4-20260907-174524 \
  --out /tmp/a-fresh-v22-analysis-directory --recover-reason-quotes
```

报告包含各方法联合与分项通过率、uncertain、明确判定区间、v1→v2.2 迁移、25 条复核分歧、Token 用量及基线范围。

## 适配审计

抽查 AutoSchemaKG 的因果方向案例：原始 `chunks/chunk-0253.json` 的 event_relation_dict
直接含 Head=已知样本标签 y 和损失函数 l、Relation=因为、Tail=可以计算单个数据样本的损失项 L。
`run_autoschemakg.py` 仅 strip 后按 Head→Relation→Tail 导入，没有反向或翻译；上游中文事件提示词
列出之前/之后/同时/因为/结果，未提供相反方向定义。因此不能将此例归因于导入器颠倒。
这是一条具体的原始产物审计，不推断所有错误都来自抽取器。
