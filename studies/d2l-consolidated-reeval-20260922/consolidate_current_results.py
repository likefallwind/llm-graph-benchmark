from pathlib import Path
import json,hashlib
R=Path("/home/likefallwind/code/llm-graph-benchmark/outputs")
P=R/"d2l-consolidated-results-20260923";P.mkdir(exist_ok=True)
sources={"historical":R/"d2l-final-comparison-20260922/data.json","entity100":R/"d2l-entity100-m3-c6-20260923/summary.json","coverage":R/"d2l-three-metrics-repaired-m3-c6-20260922/summary.json","identity_qa":R/"d2l-baseline-original-rubric-m3-c6-20260922/summary.json"}
rd=lambda p:json.loads(p.read_text())
d=rd(sources["historical"]);e=rd(sources["entity100"]);cov=rd(sources["coverage"]);iq=rd(sources["identity_qa"])["groups"]
assert e["complete"] and e["done"]==497 and cov["complete"]
systems=["ours","graphrag","autoschemakg","kggen"];names=["我们的方法","GraphRAG","AutoSchemaKG","KGGen"]
lines=["# 关注指标完整汇总（2026-09-23）","","类型、类型粒度和描述使用最新100实体结果；替换所有旧30实体版本。48探针采用修复后的完整覆盖。其余保留此前确定的结果。已被完整断言替代的旧关系分项与三轴联合分数不再重复作为主指标。","","除注明实体宏平均的指标外，确认率使用全部抽样为分母，不排除不确定项。N/A表示无原生可评字段，不等于零分。所有质量分数仍是自动裁判结果，不是独立人工金标准。"]
def table(title,rows):
 lines.extend(["","## "+title,"","|指标|"+"|".join(names)+"|","|---|---:|---:|---:|---:|"])
 for label,vals in rows:lines.append("|"+label+"|"+"|".join(vals)+"|")
def rate(n,total,digits=1):return f"{n/total:.{digits}%}（{n}/{total}）"
def row(label,fn):return(label,[fn(s) for s in systems])
rows=[]
for key,label in [("correct","完整断言确认正确率"),("incorrect","完整断言明确错误率"),("uncertain","完整断言不确定率")]:
 rows.append(row(label,lambda s,key=key:rate(d["assertion"][s].get(key,0),200)))
for key,label in [("L1","关系L1：泛关联"),("L2","关系L2：粗粒度关系"),("L3","关系L3：具体关系")]:
 rows.append(row(label,lambda s,key=key:rate(d["granularity_and_joint"][s].get(key,0),200)))
rows.append(row("具体且正确 / 全部断言",lambda s:rate(d["granularity_and_joint"][s]["correct_L3"],200)))
rows.append(row("具体关系内部的断言正确率",lambda s:rate(d["granularity_and_joint"][s]["correct_L3"],d["granularity_and_joint"][s]["L3"])))
table("完整断言与关系表达（每方法200条）",rows)
lines+=["","关系粒度依据谓词与原生关系描述共同判断，不按谓词种类数量评分。GraphRAG自然语言描述可表达具体关系。"]
rows=[row("实体所指正确率（100条）",lambda s:rate(d["entity"][s]["correctness"]["correct"],100)),row("实体引用支持率（100条）",lambda s:rate(d["entity"][s]["evidence"]["supported"],100))]
for m,label in [("entity_typing","类型标签兼容正确率（实体宏平均）"),("entity_definition_grounding","描述上下文支持率（实体宏平均）")]:
 rows.append(row(label,lambda s,m=m:f"{e['groups'][s][m]['macro_supported_rate']:.2%}" if m in e["groups"].get(s,{}) else "N/A"))
rows.append(row("整段描述全部支持（辅助，100条）",lambda s:rate(e["groups"][s]["entity_definition_grounding"]["whole"].get("pass",0),100) if "entity_definition_grounding" in e["groups"].get(s,{}) else "N/A"))
for m,label in [("alias_identity","别名同一性正确率（30条）"),("identity_split","实体拆分正确率（30条）")]:
 rows.append(row(label,lambda s,m=m:rate(iq[s][m].get("pass",0),iq[s][m]["total"]) if m in iq[s] else "N/A"))
table("实体、类型、描述与身份",rows)
lines+=["","宏平均：先求每实体内部的支持比例，再对实体平均。不确定项留在分母；我们的类型指标评97个有标签实体，另3个缺失单列；描述双方各100。实体所指与引用支持来自此前独立100实体抽样，并非本轮100实体的同一批案例。别名和拆分沿用30条，已统一为全部样本分母，因此与旧版排除不确定项的百分比不同。","","实体所指正确性、引用支持与描述支持分别回答实体指什么、引用能否支持实体、描述的实质内容是否有依据，不把三项简单相加。类型汇总已复算，但仍发现裁判理由错位及评价越界，详见原100实体TYPE_AUDIT.md；不据细小分差直接断言优劣。"]
rows=[]
for level,label in [("L1","最具体正确类型仍为泛类L1"),("L2","最具体正确类型为一般类别L2"),("L3","最具体正确类型为具体类别L3"),("none","有类型标签但无确认正确类型")]:
 rows.append(row(label,lambda s,level=level:rate(e["groups"][s]["entity_typing"]["finest_supported_type"].get(level,0),100) if s in e["groups"] else "N/A"))
rows.append(row("类型字段缺失",lambda s:rate(e["groups"][s]["entity_typing"]["field_absent"],100) if s in e["groups"] else "N/A"))
rows.append(row("正确且L2/L3类型覆盖",lambda s:rate(sum(e["groups"][s]["entity_typing"]["finest_supported_type"].get(z,0) for z in ["L2","L3"]),100) if s in e["groups"] else "N/A"))
table("类型粒度（全部100实体为分母）",rows)
lines+=["","各实体取最具体的正确类型；L3一行同时就是正确且细粒度类型覆盖率，不再重复计分。L2/L3覆盖只要求至少一个正确类型，不代表该实体其他标签也正确。标签级粒度构成保留在100实体REPORT.md，不作为独立主指标。"]
table("用途与事实覆盖",[
 row("Book QA支持率（24题）",lambda s:rate(iq[s]["book_qa"]["pass"],24)),
 row("完整事实覆盖（48探针）",lambda s:rate(cov["groups"][s]["fact_recovery"]["pass"],48))
])
lines+=["","48探针覆盖不是全书召回，不与断言正确率组合F1。Book QA沿用旧协议：展示参考来源且图候选有长度限制；实体拆分旧协议未向裁判展示原文证据。两项作为历史辅助结果保留，未在本轮100实体扩样中重测。"]
table("图规模与结构",[
 row("节点数",lambda s:f"{d['structure'][s]['summary']['entity_count']:,}"),
 row("完整提交图边数",lambda s:f"{d['structure'][s]['summary']['assertion_count']:,}"),
 row("语义评测范围内断言数",lambda s:f"{19965 if s=='autoschemakg' else d['structure'][s]['summary']['assertion_count']:,}"),
 row("实体引用存在率",lambda s:f"{d['structure'][s]['summary']['entity_evidence_coverage']:.2%}"),
 row("断言引用存在率",lambda s:f"{d['structure'][s]['summary']['assertion_evidence_coverage']:.2%}"),
 row("完整图孤立节点率",lambda s:f"{d['structure'][s]['summary']['isolated_entity_rate']:.4%}" if s=="autoschemakg" else f"{d['structure'][s]['summary']['isolated_entity_rate']:.2%}"),
 row("最大连通分量节点占比",lambda s:f"{d['structure'][s]['documents'][0]['largest_component_ratio']:.2%}"),
 row("别名条目数",lambda s:f"{d['structure'][s]['summary']['identity']['alias_count']:,}")
])
lines+=["","AutoSchemaKG节点包含事件，完整图56,149条边；语义质量评测沿用约定的19,965条语义边子集。结构统计使用完整图，规模与连通性不直接作为质量总分。引用存在率不等于引用支持率。"]
table("全图原生字段覆盖",[
 row("有类型的节点 / 全部节点",lambda s:f"{d['availability'][s]['with_types']:,}/{d['availability'][s]['nodes']:,}"),
 row("有描述的节点 / 全部节点",lambda s:f"{d['availability'][s]['with_definition']:,}/{d['availability'][s]['nodes']:,}"),
 row("有别名的节点 / 全部节点",lambda s:f"{d['availability'][s]['with_aliases']:,}/{d['availability'][s]['nodes']:,}")
])
rows=[]
for key,label in [("input_tokens","构图输入Token（M）"),("output_tokens","构图输出Token（M）"),("total","构图总Token（M）")]:
 rows.append(row(label,lambda s,key=key:"未记录" if s not in d["construction_usage"] else f"{(d['construction_usage'][s]['input_tokens']+d['construction_usage'][s]['output_tokens'] if key=='total' else d['construction_usage'][s][key])/1e6:.3f}"))
table("构图资源消耗",rows)
lines+=["","1 M = 1 million = 1,000,000 tokens；不含外部评测调用。AutoSchemaKG包含概念化，KGGen包含抽取与官方归一。有效耗时、货币成本及我们的构图Token未可靠记录，不补猜测值。"]
# 历史断言引用支持率已退出最终展示；历史原始结果仍保留。
lines+=["","以上均为单教材、模型裁判结果。各方法独立抽样，非同名实体配对实验。已知判定争议保留，不按预期排名修改分数。"]
(P/"REPORT.md").write_text("\n".join(lines)+"\n")
(P/"data.json").write_text(json.dumps({"latest_entity100":e["groups"],"latest_coverage":{s:cov["groups"][s]["fact_recovery"] for s in systems},"historical_entity":d["entity"],"assertion":d["assertion"],"relation_granularity":d["granularity_and_joint"],"identity_qa":{s:{m:iq[s][m] for m in ["alias_identity","identity_split","book_qa"] if m in iq[s]} for s in systems},"structure":d["structure"],"availability":d["availability"],"construction_usage":d["construction_usage"]},ensure_ascii=False,indent=2))
(P/"provenance.json").write_text(json.dumps({k:{"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in sources.items()},ensure_ascii=False,indent=2))
print(str(P/"REPORT.md"))

