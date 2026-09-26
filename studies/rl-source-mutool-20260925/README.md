# 强化学习书原文用 mutool 重建

> 已被 [rl-source-fontfix-20260926](../rl-source-fontfix-20260926/README.md) 替代：本版只补回被丢掉的符号，π、θ、α、ff、′、∇、∈、∑ 等被错映射的字形仍是错的。保留仅供追溯。

旧冻结原文（studies/rl-baselines-20260923/frozen-benchmark）由 llm-knowledge-graph 的 `pdftotext -layout` 抽取。
这本 PDF 的 CMSY/CMMI 字体没有 Unicode 映射，pdftotext 会丢掉负号、λ、γ、δ、≥ 等符号，例如 "reward is −1" 变成 "reward is 1"，"PTD(λ)" 变成 "PTD( )"。
mutool 1.23.10 能按字形名恢复这些符号。四个方法的构图输入和裁判原文都来自旧文本，因此这是 benchmark 自身原文的问题。

重建保持全部段落编号、顺序、位置和小节标题不变，只替换 S2（PDF）段落文字；D2L（S1）段落不动：

- mutool_span：段落的英文字母数字骨架在所在页 mutool 文本中原样出现，整段换成 mutool 对应片段；
- symbol_patch：骨架对不上（图中文字、并排排版、复杂公式），保留 pdftotext 文字，只在对齐字符之间补回丢失符号；
- unchanged / heading_kept：无可补符号或为标题。

每个改写段落的字母数字骨架与原文完全一致，脚本会校验。mutool 的前置重音（ˆv、¨o）合并回字母，大括号产生的替换字符 U+FFFD 删除。
四个方法现有 submission 均通过新原文校验；benchmark_id 不变（submission 锁定该值），原文版本记录在 metadata 和 benchmark 哈希中。

```bash
python studies/rl-source-mutool-20260925/rebuild_source.py
```

输出 frozen-benchmark/（事实探针、QA、rubric 原样复制）、REBUILD.json 汇总和 changes.jsonl 逐段新旧对照。

已知未解决：
- π、θ、α、ε、∇、∈ 和 ff 连字在 PDF 自带映射中就是错的（⇡、✓、↵、"、r、2、↵），两个工具相同，未处理；
- 并排排版和重叠文字层导致的错位段落（约 250 段，多为图表、索引和公式碎片）需要重新分段才能修复，改段落编号会使现有提交失效，本次不处理；
- 各方法构图时读到的是旧文本，重评只更新裁判使用的原文。
