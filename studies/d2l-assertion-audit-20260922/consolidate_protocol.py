from pathlib import Path
import json,datetime,hashlib
root=Path('/home/likefallwind/code/llm-graph-benchmark');out=root/'outputs/d2l-metrics-comparison-20260922'
base=root/'outputs/d2l-baseline-correction-m3-c6-20260909-172849'
paths={'ours':root/'outputs/d2l-full1105-vnext-20260826/submission.json','graphrag':base/'graphrag/submission.json','autoschemakg':base/'autoschemakg/evaluation/semantic-submission.json','kggen':base/'kggen/submission.json'}
names={'ours':'我们的方法','graphrag':'GraphRAG','autoschemakg':'AutoSchemaKG','kggen':'KGGen'}
rd=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
audit={}
for s,p in paths.items():
 es=[e for d in rd(p)['documents'] for e in d['entities']]
 audit[s]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nodes':len(es),'with_types':sum(bool(e.get('types')) for e in es),'with_definition':sum(bool(e.get('definition')) and e.get('metadata',{}).get('definition_available') is not False and e.get('definition')!='（该方法未输出实体定义）' for e in es),'with_aliases':sum(bool(e.get('aliases')) for e in es)}
text='''# 评估指标收敛版

状态：整理已有结果并确定重评范围；本文不表示新增语义评测已经启动或完成。历次原报告保留在 ALL_METRICS.md；当前主表不再混入旧配置结果。

## 保留的主指标

| 方面 | 指标 | 判定对象与边界 | 当前状态 |
|---|---|---|---|
| 实体 | 实体所指正确率 | 名称在原文中的指代和实体身份；不再另列旧实体准入分数，不沿用旧准入的更宽标准 | 保留当前历史值；旧裁判未经充分验证，统一重评清单包含此项 |
| 实体证据 | 实体引用支持率 | 原提交引用是否支持实体所指 | 保留历史值；统一重评清单包含此项 |
| 断言 | 完整断言确认正确率 | 实体、谓词、方向、描述全部实质命题、范围与极性 | 最新800条完成，184/156/151/139分别通过，不因新增指标再改写 |
| 断言证据 | 断言引用支持率 | 原提交引用能否支持完整断言，与扩展上下文下的正确性不同 | 保留历史值；引用判定须检查是否也存在只核验核心命题的宽松问题，列入重评 |
| 表达粒度 | L1/L2/L3分布 | 按谓词加原生关系描述评价表达粒度，独立于正确性 | 保留；24条技术缺失待补 |
| 表达粒度与正确性 | L3内确认正确率；具体且正确/全部样本 | 从现有粒度与新断言标签交叉统计，不增加裁判、不加权成总分 | 保留，受粒度缺失影响 |
| 覆盖 | 48探针事实覆盖 | 候选中一条或多条共同恢复源事实；统一BM25 Top-10口径 | 保留现有覆盖结果，不称全书召回，不拼F1 |
| 类型 | 实体类型正确率 | 原生输出类型是否与实体及语境兼容；不要求各方法采用同一粒度或类型词表 | 只对实际有类型的节点评，另报类型可用率；修正后三基线需重评，我们的方法用同协议重评 |
| 实体描述 | 实体定义/描述证据支持率 | 原生实体定义或描述中的实质内容是否得到原文支持，不惩罚输出形式差别 | 占位符不算定义；只评真实输出，另报可用率；各可评方法统一重评 |
| 身份 | 别名同一性正确率 | 别名与归一名称是否指向同一实体，检查错误合并 | 我们的方法、KGGen有可评对象，按当前产物重评；无对象记N/A |
| 身份 | 实体拆分正确率 | 同名或近名节点是否确实应当分开，检查错误拆分 | 固定候选形成规则后各方法重评；不能用重复组数替代正确率 |
| 下游用途 | 图谱问答支持率（Book QA） | 同24题、同图谱候选检索器与预算、同裁判；候选图内容能否支持答案 | 当前四方法统一重评；不是各系统原生查询器的端到端QA能力 |

类型可用率与类型正确率分别报告；没有类型、定义或别名时记“不提供/不适用”，不伪造0%正确率。实体/事件样本总体必须与所评图一致，AutoSchemaKG节点类型混合情况单独标注。

## 从主结果中移出的项目

| 项目 | 处理 | 原因 |
|---|---|---|
| v2.2关系、描述、条件分项及其联合通过率 | 历史附录 | 最新完整断言评估已覆盖这些语义要求 |
| v3 grounding/projection/scope与三轴联合 | 历史附录 | 旧规则和旧配置，不与最新断言结果并列作主指标 |
| 单独的旧实体准入指标 | 历史附录 | 与实体所指正确性高度重叠，且旧准入更宽；不把旧值直接更名合并 |
| 严格事实恢复v1、核心覆盖v1 | 历史附录 | 与现有覆盖形成多套口径，主表保留一个冻结探针覆盖定义 |
| 跨运行稳定性、检索器并集实验 | 诊断附录 | 目前仅本方法历史局部实验，没有当前四方法的对齐比较 |
| 裁判一致性、开发检查 | 评测可信度部分 | 是评估器检查，不是被评方法性能分数 |
| 通过率乘图规模的可消费产出估计 | 不作主指标 | 外推且忽略独立事实重复和样本偏差，不能当实际核验产量 |

## 结构描述保留，但不作质量排名

主表保留节点数、被评断言数、实体/断言引用存在率、孤立节点率、最大连通分量比例；别名数、表面重复组等放结构附表。谓词种类仅作描述或附录，不作为优势证据。
AutoSchemaKG完整提交图为41960节点、56149边；语义评测子集19965边。完整提交图孤立节点1个、最大分量60.84%。语义子图保留所有节点但删事件参与边，42.70%的孤立率不能当作完整图缺陷。schema概念层与来源断言层分开描述。

## 当前字段可用性：根据冻结产物实查

| 方法 | 有类型的节点 / 全部节点 | 有真实定义或描述的节点 / 全部节点 | 有别名的节点 / 全部节点 |
|---|---:|---:|---:|
'''
for s,a in audit.items():
 text+='|'+names[s]+'|'+'|'.join(f"{a[k]:,}/{a['nodes']:,}" for k in ['with_types','with_definition','with_aliases'])+'|\n'
text+='''
GraphRAG当前LLM构图版实际有类型和实体描述，不能继承旧Fast版的“无此能力”结论。AutoSchemaKG类型来自本次概念化（1节点缺失），但未提供实体定义。KGGen当前官方归一结果已有别名，不能继续沿用旧exact版无别名的结论。

## 构图资源：单位统一为million tokens（M）

1 M = 1,000,000 tokens。以下均为已记录构图消耗，不含外部评测。缺失记“未记录”，不记0。

| 指标 | 我们的方法 | GraphRAG | AutoSchemaKG | KGGen |
|---|---:|---:|---:|---:|
'''
p=rd(out/'all-metrics-provenance.json')['construction_usage_with_historical_extraction']
for title,k in [('输入Token（M）','input_tokens'),('输出Token（M）','output_tokens'),('总Token（M）',None)]:
 vals=[(p[s][k] if k else p[s]['input_tokens']+p[s]['output_tokens'])/1e6 for s in ['graphrag','autoschemakg','kggen']]
 text+='|'+title+'|未记录|'+'|'.join(f'{v:.3f}' for v in vals)+'|\n'
text+='''
KGGen合计历史抽取与官方归一；AutoSchemaKG包含概念化。分项独立四舍五入，总量由原始计数计算。有效运行耗时、吞吐量与货币成本未可靠记录，不用数据库时间跨度或自行猜测单价补值。“Token/断言”保留历史附录，不作为统一工作量下的效率排名。

## 重评执行清单

1. 固定当前四份submission与同一教材，不重新构图，不再使用Fast/未归一/概念化未完成的旧基线产物。
2. 实体所指与实体引用使用既有每方法100条冻结样本，统一完善评判规则后重评；不得合并旧准入标签充当新判断。
3. 类型、实体定义/描述、别名、身份拆分与Book QA制定共同规则、检查开发题与真实边界案例；有字段才有正确率，字段可用率单独报告。对于语义宽泛但合法的类型，不因粒度粗判错；实体描述也不要求字典式定义。
4. 当前三基线要重评，我们的方法也用同一协议和采样规则；不只给基线换规则后与我们的旧分数比较。
5. 原提交引用支持采用完整输出核验；补齐24条粒度技术缺失。现有最新完整断言判断保留；争议案例复核须另留记录，不挑选分数回写。
6. 所有新增模型判断沿用已授权MiniMax API和并发上限6。重评结果有效前，旧分数保留历史标识，新表填“待重评”，不得声称已启动或完成。

历史全表：ALL_METRICS.md。现有主质量数值与判定分布：REPORT.md。
'''
(out/'CONSOLIDATED_PROTOCOL.md').write_text(text,encoding='utf-8')
(out/'field-availability-audit.json').write_text(json.dumps({'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'submissions':audit,'new_evaluation_started':False},ensure_ascii=False,indent=2)+'\n')
print('saved',str(out/'CONSOLIDATED_PROTOCOL.md'));print(text[text.index('## 构图资源'):text.index('## 重评执行清单')])
