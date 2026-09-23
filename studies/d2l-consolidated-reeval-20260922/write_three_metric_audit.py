from pathlib import Path
import json,collections,statistics
R=Path('/home/likefallwind/code/llm-graph-benchmark');B=R/'outputs/d2l-baseline-original-rubric-m3-c6-20260922';O=R/'outputs/d2l-final-comparison-20260922';rd=lambda p:json.loads(p.read_text());ts=rd(B/'tasks.json');key=rd(B/'private-key.json');our={t['task_id']:t for t in [json.loads(x) for x in (R/'outputs/d2l-full1105-vnext-20260826/evaluation/all-tasks.jsonl').read_text().splitlines()]};judgments={v['task_id']:v for v in rd(B/'preserved-ours.json')};cases=[]
for t in ts:
 if t['id'] in {'t_c51569fff41f999ace8c','t_ec5eeb940ca343dc1ae1','t_59acdc1fce2206eed723'}:cases.append({'system':'graphrag','task':t['task'],'exact_judge_messages':t['messages'],'original_judgment':rd(B/'results'/(t['id']+'.json'))})
for i in ['t_b9d5a3cfe47577c8301c','t_2dc203d2b99890d327d0','t_1361cc30f579ab52d48c','t_4b44dd149d6b47f49432','t_8859e4df60f1bc52a348']:
 cases.append({'system':'ours','task':our[i],'original_judgment':judgments[i]})
P=R/'outputs/d2l-baseline-correction-m3-c6-20260909-172849/graphrag/evaluation';inp=rd(P/'inputs.json')
for t in inp['fact_tasks']:
 if t['task_id'] in ['t_ab2630f29f4de109eeae','t_d2ba8e91c044fc197b4b']:cases.append({'system':'graphrag','task':t,'original_judgment':rd(P/'results'/(t['task_id']+'.json'))})
(O/'AUDIT_CASES.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
report='''# 类型、描述与48探针覆盖核查

结论：原表数值可从原始标签复算，但不能据此确认GraphRAG在类型和描述方面优于本方法。描述裁判存在明确串项及尺度不一致；48/48是历史宽口径核心覆盖，且至少一条必要条件漏判。所有原始标签和分数保留，本次没有新增API调用或按预期排名改分。

|检查|我们的方法|GraphRAG|
|---|---:|---:|
|类型 pass/fail/uncertain|22/5/3|26/4/0|
|描述 pass/fail/uncertain|18/11/1|20/8/2|
|每实体平均类型标签数|2.23|1.27|
|30个类型样本中含CONCEPT的实体|不使用统一大类；有1个concept标签|13|
|定义/描述字符长度中位数|43.5|31.5|
|30实体样本中原引用展示超过1200字符上限|5|12|

类型问题：原规则要求全部提交标签兼容，既不评类型细粒度，也不评类型完整性。不同输出数量和粒度对应不同难度，但粗标签兼容应当算对。本方法也有真实类型错误，如nn.CrossEntropyLoss带“平方误差损失”、BERT表示带“model”、隐藏单元带“超参数”。不能只因标签更多、更细就把这些错误取消。30个样本各自独立抽样，不能把当前5.2个百分点差距当作稳健优劣结论。

描述问题：
- 本方法nn.CrossEntropyLoss的定义判fail，理由只在批评types里的“平方误差损失”。原文明确支持未规范化预测及softmax/对数计算。这是类型错误被重复计入描述维度。
- 本方法“向量空间”提交的是其在凸集定义中的角色描述，裁判因“未给出向量空间本身定义”判fail；加入了原rubric未要求的字典式定义标准。
- GraphRAG SIGMA描述“通常设置为0.01”，原文仅说本例设为0.01；裁判理由承认缺少常用值依据，但仍pass，与“全部实质内容有支持”不一致。
- GraphRAG“硬性类别”的描述只是“属于哪个类别”的正常改述，却因为“明确”“最终”被判有额外实质内容。说明错误并非只偏向一个方法。

覆盖问题：已核对48个不同探针、48个yes标签，以及480条候选与正确GraphRAG原提交边一一一致，未发现错图、重复计数或伪造候选。旧提示显式允许复合事实次要维度缺失仍判yes，因此测的是核心事实覆盖，不是完整事实恢复。
- BPTT探针包含“长序列带来高时间和内存成本”；10个候选没有该部分，理由也承认缺失，仍yes。这符合旧宽口径，但不能解释为完整恢复。
- 卷积输出形状探针要求“无填充且步幅1”。10条候选没有将这两项条件与该公式关联；裁判承认条件未出现，仍yes。这涉及命题成立的必要条件，应属于原规则也要求保留的部分，存在明确漏判风险。

输入还向覆盖裁判展示源事实及原文参考来源。源事实用于比对是必要的，不能把其出现本身称作泄漏；风险在于裁判用来源给候选补缺失信息。本次确认了候选内容和漏条件现象，未把该风险直接归因为已证实的泄漏。

处置：三项保留原分数并标记“探索性/待复核”，48探针更准确称“历史核心事实覆盖”。不直接从48扣成46，不用挑出的个案改写整表，也不调整提示到某个期望排名。若继续修复，只隔离待评字段、避免机械截断、明确完整事实需保留必要条件；规则应简短、各方法一致，受影响维度统一复核后才给新分数。

原始案例和判定：AUDIT_CASES.json。此核查包括全量计数、输入结构统计及GraphRAG覆盖候选来源验证；上述语义结论来自列明案例，不是所有样本的独立人工重标。
'''
(O/'AUDIT.md').write_text(report)
p=O/'REPORT.md';s=p.read_text();note='> 后续核查：类型与描述分数不能直接用于确认方法优劣；描述裁判发现串项及尺度不一致。48探针应称“历史核心事实覆盖”，48/48不代表完整事实恢复，已发现必要条件漏判案例。原分数保留，详见 [核查记录](AUDIT.md)。\n\n';s=s.replace('# 最终关注指标对照表（2026-09-22）\n\n','# 最终关注指标对照表（2026-09-22）\n\n'+note,1);p.write_text(s);print(str(O/'AUDIT.md'))
