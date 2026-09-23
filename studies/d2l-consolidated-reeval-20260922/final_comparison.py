from pathlib import Path
import json,collections,hashlib
R=Path('/home/likefallwind/code/llm-graph-benchmark/outputs');out=R/'d2l-final-comparison-20260922';out.mkdir(exist_ok=True);sources={}
def rd(p):sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
systems=['ours','graphrag','autoschemakg','kggen'];names=['我们的方法','GraphRAG','AutoSchemaKG','KGGen'];B=R/'d2l-baseline-original-rubric-m3-c6-20260922';A=R/'d2l-assertion-ledger-v25-20260922-recovery02';E=rd(R/'d2l-entity-missing7-m3-c6-20260922/summary.json')['systems'];base=rd(B/'summary.json')['groups'];assertion=rd(A/'summary.json')['systems'];old=rd(R/'d2l-reliability-m3-c6-exploratory-20260920T132325Z/summary.json')['systems'];cov=rd(R/'d2l-reliability-m3-c6-exploratory-20260920T132325Z/legacy-coverage.json')['systems'];avail=rd(R/'d2l-metrics-comparison-20260922/field-availability-audit.json')['submissions'];usage=rd(R/'d2l-metrics-comparison-20260922/all-metrics-provenance.json')['construction_usage_with_historical_extraction']
g=rd(B/'granularity-preserved.json')
for t in rd(B/'tasks.json'):
 if t['metric']=='granularity':g[t['id']]=rd(B/'results'/(t['id']+'.json'))
key=rd(A/'private-key.json');joint=collections.defaultdict(collections.Counter)
for i,v in g.items():
 assert v['status']=='done';s=key[i]['system'];l=v['value']['label'];joint[s][l]+=1
 if rd(A/'results'/(i+'.json'))['value']['label']=='correct':joint[s]['correct_'+l]+=1
assert all(sum(joint[s][l] for l in ['L1','L2','L3'])==200 for s in systems)
structure={s:rd(R/('d2l-full1105-vnext-20260826/evaluation/structural-metrics.json' if s=='ours' else 'd2l-metrics-comparison-20260922/autoschemakg-full-structural-recomputed.json' if s=='autoschemakg' else 'd2l-baseline-correction-m3-c6-20260909-172849/'+s+'/evaluation/structural-metrics.json')) for s in systems}
lines=['# 最终关注指标对照表（2026-09-22）','','三个基线均使用修正后的产物；我们的方法保留既有结果。关系粒度与实体技术缺失均已补齐。仅汇总，不新增模型调用。','']
def pct(n,d):return f'{n/d:.1%}（{n}/{d}）' if d else 'N/A'
def table(title,rows):
 lines.extend([title,'','|指标|'+'|'.join(names)+'|','|---|---:|---:|---:|---:|']);lines.extend('|'+ '|'.join(map(str,row))+'|' for row in rows);lines.append('')
rows=[]
for metric,dim,label in [('实体所指正确率','correctness','correct'),('实体引用支持率','evidence','supported')]:rows.append([metric]+[pct(E[s][dim][label],100) for s in systems])
rows+=[['完整断言确认正确率']+[pct(assertion[s]['correct'],200) for s in systems],['完整断言明确错误率']+[pct(assertion[s]['incorrect'],200) for s in systems],['完整断言不确定率']+[pct(assertion[s]['uncertain'],200) for s in systems],['断言引用支持率（保留旧裁判）']+[pct(old[s]['assertion']['evidence']['supported'],200) for s in systems]]
table('内容正确性与引用支持：以下以全部抽样为分母，不确定不算确认正确，也不自动算错误。',rows)
rows=[]
for l,title in [('L1','L1：泛关联'),('L2','L2：粗粒度关系'),('L3','L3：具体关系')]:rows.append([title]+[pct(joint[s][l],200) for s in systems])
rows += [['L3内完整断言确认正确率']+[pct(joint[s]['correct_L3'],joint[s]['L3']) for s in systems],['具体且正确 / 全部样本']+[pct(joint[s]['correct_L3'],200) for s in systems]]
table('关系表达粒度：按谓词加原生关系描述判断，不按谓词种类计分。',rows)
lines+=['GraphRAG的自然语言关系描述可以表达具体关系，因此 related_to 标签不意味着整条关系只有泛关联。粒度高本身不表示正确。','']
rows=[]
for m,title in [('entity_typing','实体类型正确率'),('entity_definition_grounding','实体定义/描述支持率'),('alias_identity','别名同一性正确率'),('identity_split','实体拆分正确率'),('book_qa','Book QA支持率')]:
 rows.append([title]+[pct(base[s][m].get('pass',0),base[s][m].get('pass',0)+base[s][m].get('fail',0)) if m in base[s] else 'N/A' for s in systems])
rows.append(['48探针事实覆盖']+[pct(cov[s]['counts']['yes'],48) for s in systems]);table('类型、描述、身份与下游用途：前五项沿用原协议，以明确判定为分母；N/A表示没有对应可评输出。',rows)
lines+=['类型/描述/身份每项原抽样最多30条，Book QA固定24题；分母小于抽样数是排除了不确定项。48探针覆盖不是全书召回，不与正确率拼F1。','']
table('原生字段可用性：有字段的节点数 / 全部节点数。',[[title]+[f"{avail[s][k]:,}/{avail[s]['nodes']:,}" for s in systems] for k,title in [('with_types','有类型的节点'),('with_definition','有定义/描述的节点'),('with_aliases','有别名的节点')]])
rows=[]
for k,title in [('entity_count','节点数'),('assertion_count','完整提交图边数')]:rows.append([title]+[f"{structure[s]['summary'][k]:,}" for s in systems])
rows.append(['语义评测范围内断言数']+['3,309','31,542','19,965','34,539'])
for k,title in [('entity_evidence_coverage','实体引用存在率'),('assertion_evidence_coverage','断言引用存在率')]:rows.append([title]+[f"{structure[s]['summary'][k]:.2%}" for s in systems])
rows.append(['完整提交图孤立节点率']+[f"{structure[s]['documents'][0]['isolated_entity_count']/structure[s]['summary']['entity_count']:.4%}" if s=='autoschemakg' else f"{structure[s]['summary']['isolated_entity_rate']:.2%}" for s in systems]);rows.append(['最大连通分量节点占比']+[f"{structure[s]['documents'][0]['largest_component_ratio']:.2%}" for s in systems]);rows.append(['别名条目数']+[f"{structure[s]['summary']['identity']['alias_count']:,}" for s in systems]);table('当前图规模与结构：描述产物，不作为质量总分。',rows)
lines+=['AutoSchemaKG节点包含事件；完整图56,149条边，质量评测使用已约定的19,965条语义边子集。连通性用完整提交图计算，不能使用删边子图的42.70%孤立率评价完整图。引用存在率不等于引用支持率。','']
rows=[]
for k,title in [('input_tokens','输入Token（M）'),('output_tokens','输出Token（M）'),('total','总Token（M）')]:rows.append([title]+['未记录' if s not in usage else f"{(usage[s]['input_tokens']+usage[s]['output_tokens'] if k=='total' else usage[s][k])/1e6:.3f}" for s in systems])
table('构图资源消耗：1 M = 1 million = 1,000,000 tokens，不含本次外部评测。',rows)
lines+=['KGGen包含历史抽取和官方归一消耗；AutoSchemaKG包含概念化。有效运行时间及货币成本未可靠记录，不补猜测值。分项独立四舍五入。','','解释边界：这些是同模型、单教材的模型评分，未经独立人工金标准验证。实体与引用沿用旧探索性裁判；完整断言为修复后的版本，两者不能作差解释引用效率。类型/身份/QA沿用历史展示限制：身份拆分未向裁判提供原文证据，QA展示了参考来源且候选有长度限制，因此保留为原协议结果。旧分项关系/描述/条件、旧三轴联合等已被完整断言指标替代，不再重复列入主表。','','判定明细（pass/fail/uncertain，实体等使用对应语义标签）见 data.json；各行结果来源和哈希见 provenance.json。']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n');(out/'data.json').write_text(json.dumps({'entity':E,'assertion':assertion,'granularity_and_joint':joint,'type_identity_qa':base,'coverage':cov,'availability':avail,'structure':structure,'construction_usage':usage},ensure_ascii=False,indent=2)+'\n');(out/'provenance.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n');print((out/'REPORT.md').read_text())
