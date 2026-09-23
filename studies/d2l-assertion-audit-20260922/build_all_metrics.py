from pathlib import Path
from types import SimpleNamespace
import json,sys,hashlib,collections,datetime
root=Path('/home/likefallwind/code/llm-graph-benchmark');sys.path.insert(0,str(root/'src'))
from llm_graph_benchmark.metrics import submission_metrics
out=root/'outputs/d2l-metrics-comparison-20260922';base=root/'outputs/d2l-baseline-correction-m3-c6-20260909-172849'
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
order=['ours','graphrag','autoschemakg','kggen'];names=['我们的方法','GraphRAG（修正后）','AutoSchemaKG（修正后）','KGGen（修正后）']
struct={'ours':rd(root/'studies/d2l-fullbook-vnext-20260826/structural-metrics.json')}
for s in order[1:]:struct[s]=rd(base/s/'evaluation/structural-metrics.json')
autopath=base/'autoschemakg/submission.json';payload=rd(autopath)
full=submission_metrics(SimpleNamespace(payload=payload,system_id=payload['system']['id'],submission_hash='file-sha256:'+sha(autopath)))
(out/'autoschemakg-full-structural-recomputed.json').write_text(json.dumps(full,ensure_ascii=False,indent=2)+'\n')
lines=['# 历次评测全指标汇总（2026-09-22）','','范围：既包含当前四种输出的指标，也保留旧配置、旧协议和早期快照实验。历史分数不会填充为修正后方法的新结果。所有数据是模型或程序评测，无独立人工金标准。','']
def table(title,headers,rows,note=''):
 lines.extend(['## '+title,'','|'+'|'.join(headers)+'|','|'+'|'.join(['---']+['---:']*(len(headers)-1))+'|'])
 for row in rows:lines.append('|'+'|'.join(str(x) for x in row)+'|')
 lines.extend(['',note,''])
def current(title,rows,note=''):table(title,['指标']+names,rows,note)
old=rd(root/'outputs/d2l-reliability-m3-c6-exploratory-20260920T132325Z/summary.json');new=rd(root/'outputs/d2l-assertion-ledger-v25-20260922-recovery02/summary.json');compiled=rd(out/'data.json')
rows=[]
for title,kind,metric,label in [('实体所指正确率（旧裁判，n=100）','entity','correctness','correct'),('实体引用支持率（旧裁判，n=100）','entity','evidence','supported'),('断言引用支持率（旧裁判，n=200）','assertion','evidence','supported')]:
 rows.append([title]+[f"{old['systems'][s][kind][metric][label]/old['systems'][s][kind]['selected']:.1%}" for s in order])
rows.insert(2,['完整断言确认正确率（最新，n=200）']+[f"{new['systems'][s]['correct']/200:.1%}" for s in order])
for k,title in [('L1','L1泛关联'),('L2','L2粗粒度'),('L3','L3具体关系'),('unassessed','粒度未判定')]:rows.append([title]+[f"{compiled['systems'][s]['granularity_counts'][k]/200:.1%}" for s in order])
rows.append(['L3内完整断言确认正确率']+[f"{compiled['systems'][s]['new_correct_by_granularity']['L3']/compiled['systems'][s]['granularity_counts']['L3']:.1%}" for s in order])
rows.append(['具体且正确 / 全部200条']+[f"{compiled['systems'][s]['new_correct_by_granularity']['L3']/200:.1%}" for s in order])
rows.append(['CaRB式事实覆盖（48探针）']+['44/48（91.7%）','48/48（100.0%）','45/48（93.8%）','37/48（77.1%）'])
current('A. 当前输出已有的主要质量结果',rows,'最新断言800/800有效。实体与引用沿用旧裁判，曾有开发检查失败；实体正确性技术缺失依次0/2/1/3，实体引用缺失0/0/1/0，均保留固定分母。粒度776/800有效。CaRB式覆盖是历史48探针，不是全书召回，不计算拼接F1。')
parts={'ours':{'edge_label':192,'description_label':197,'condition_label':198,'label':191}}
for s in order[1:]:
 c=collections.Counter();total=0
 for f in (base/s/'evaluation/results').glob('*.json'):
  r=rd(f);v=r.get('value',{})
  if r['status']=='done' and v.get('kind')=='quality':
   total+=1
   for k in ['edge_label','description_label','condition_label','label']:c[k]+=v[k]=='pass'
 assert total==200;parts[s]=dict(c)
current('B. 之前的v2.2分项质量（每方法200条）',[[label]+[f'{parts[s][k]/200:.1%}（{parts[s][k]}/200）' for s in order] for k,label in [('edge_label','关系/方向通过'),('description_label','描述通过'),('condition_label','必要条件通过'),('label','三项联合通过')]],'这是历史协议的另一轮抽样，不是最新完整断言正确率。GraphRAG通用谓词使关系分项更容易通过；分项不能相乘或替代完整断言评分。')
rows=[]
for label,get,format_ in [
 ('节点数（AutoSchemaKG含事件）',lambda x:x['summary']['entity_count'],lambda x:f'{x:,}'),
 ('被评断言数（AutoSchemaKG语义子集）',lambda x:x['summary']['assertion_count'],lambda x:f'{x:,}'),
 ('谓词标签数量（仅描述规模）',lambda x:x['summary']['unique_predicate_count_sum'],lambda x:f'{x:,}'),
 ('实体引用存在率',lambda x:x['summary']['entity_evidence_coverage'],lambda x:f'{x:.2%}'),
 ('断言引用存在率',lambda x:x['summary']['assertion_evidence_coverage'],lambda x:f'{x:.2%}'),
 ('孤立节点率（被评视图）',lambda x:x['summary']['isolated_entity_rate'],lambda x:f'{x:.2%}'),
 ('最大连通分量节点比例（被评视图）',lambda x:x['documents'][0]['largest_component_ratio'],lambda x:f'{x:.2%}'),
 ('连通分量数（被评视图）',lambda x:x['documents'][0]['component_count'],lambda x:f'{x:,}'),
 ('别名数',lambda x:x['summary']['identity']['alias_count'],lambda x:f'{x:,}'),
 ('非平凡别名数',lambda x:x['summary']['identity']['nontrivial_alias_count'],lambda x:f'{x:,}'),
 ('有别名的节点数',lambda x:x['summary']['identity']['entities_with_aliases'],lambda x:f'{x:,}'),
 ('规范名表面重复组',lambda x:x['summary']['surface_duplicate_group_count'],lambda x:f'{x:,}'),
 ('歧义表面词组',lambda x:x['summary']['identity']['ambiguous_surface_group_count'],lambda x:f'{x:,}'),
 ('涉及歧义表面的节点数',lambda x:x['summary']['identity']['entities_in_ambiguous_surface_groups'],lambda x:f'{x:,}')]:rows.append([label]+[format_(get(struct[s])) for s in order])
current('C. 当前图的结构、引用存在与身份统计',rows,'AutoSchemaKG被评视图保留41960个节点但只保留19965条语义边；其42.70%孤立率和15.73%最大分量是删边视图的性质，不能据此说原生图连通性差。谓词种类多不等于质量高；引用存在不等于引用支持。')
table('AutoSchemaKG全图与语义视图核对',['指标','全提交图（含事件参与边）','语义评测视图'],[[k,full['documents'][0][f],struct['autoschemakg']['documents'][0][f]] for k,f in [('节点数','entity_count'),('断言数','assertion_count'),('谓词数','unique_predicate_count'),('孤立节点数','isolated_entity_count'),('连通分量数','component_count'),('最大分量比例','largest_component_ratio')]],'全提交图统计由冻结submission按仓库同一结构程序重算，不含额外schema概念层。')
gs=rd(base/'graphrag/summary.json');a=rd(base/'autoschemakg/summary.json');k=rd(base/'kggen/summary.json')
usage={'graphrag':gs['usage'],'autoschemakg':a['usage'],'kggen':{x:k['normalization_usage'][x]+k['historical_extraction_usage'][x] for x in ['input_tokens','output_tokens']}}
current('D. 当前构图资源消耗',[[label,'未记录']+[f"{usage[s][key]:,}" for s in order[1:]] for key,label in [('input_tokens','输入Token'),('output_tokens','输出Token')]]+[['总Token','未记录']+[f"{usage[s]['input_tokens']+usage[s]['output_tokens']:,}" for s in order[1:]]]+[['总Token / 被评断言','未记录']+[f"{(usage[s]['input_tokens']+usage[s]['output_tokens'])/struct[s]['summary']['assertion_count']:.1f}" for s in order[1:]]]+[['有效运行耗时 / 吞吐量']+['未记录']*4,['实际货币成本']+['未记录']*4], 'KGGen合计包含复用的历史抽取和新增官方归一，不能把结构文件里仅归一的Token冒充总成本。AutoSchemaKG包含概念化，除以语义边数量只是摊销描述，不能称公平算法效率。所有Token不含本次质量评测费用。')
headers=['历史指标','我们（vNext）','GraphRAG Fast（旧）','AutoSchemaKG抽取子集（旧）','KGGen exact（旧）','KGGen semhash（旧）']
rows=[
 ['实体准入','89.7%','17.2%','23.3%','32.1%','27.6%'],['实体类型','81.5%','22.7%','44.4%','7.1%','4.3%'],['实体定义证据支持','62.1%','8.0%','14.8%','4.2%','8.0%'],['别名同一性','96.7%','无可评对象','无可评对象','无可评对象','无可评对象'],['实体拆分正确性','90.0%','无可评对象','3.7%','0.0%','21.1%'],['Book QA','54.2%','33.3%','56.5%','12.5%','4.2%'],
 ['v3 grounding','99.5%','47.1%','86.8%','73.1%','28.2%'],['v3 projection','90.4%','68.1%','85.9%','66.0%','16.2%'],['v3 scope','83.5%','66.9%','68.3%','62.7%','40.1%'],['v3三轴联合 / 200','75.0%','33.5%','56.0%','42.5%','11.0%'],
 ['旧CaRB覆盖 / 48','91.7%','0.0%','95.8%','79.2%','12.5%'],['严格事实恢复v1 / 48','54.2%（26）','0.0%（0）','75.0%（36）','18.8%（9）','0.0%（0）'],['核心事实覆盖v1 / 48','77.1%（37）','0.0%（0）','85.4%（41）','56.3%（27）','0.0%（0）']]
table('E. 旧配置的实体、身份、问答、三轴与恢复指标',headers,rows,'历史实体/身份多数每格约19–30个明确判定，QA约24，旧三轴每方法200；除标明全样本的行外，沿用旧报告排除uncertain的decided分母。AutoSchemaKG旧三轴有7条调用错误；其旧实体抽样混有事件（纯实体准入4/14=28.6%，事件3/16=18.8%）。旧KGGen、GraphRAG缺类型/定义，AutoSchemaKG旧类型是占位分类且概念化未完成，低分不能解读为当前完整方法能力。当前修正后三基线尚未重测这些实体、身份、QA及严格/核心恢复指标。历史旧协议曾存在噪声惩罚或条件假设问题，只供追溯。')
table('F. 我们的方法早期快照评测',['指标','exact27','fresh200','全书vNext（Codex首评）'],[
 ['实体准入','30/30','30/30','30/30'],['实体类型','25/30','23/30','25/30'],['定义证据支持','16/30','23/30','27/30'],['断言证据支持','27/30','29/30','29/30'],['别名同一性','30/30','29/30','28/30'],['实体拆分','2/2','13/14','28/30'],['原口径事实恢复','0/1','3/7','36/48'],['Book QA','0/1','2/6','12/24'],['节点数',132,603,2140],['断言数',76,625,3309],['孤立率','40.9%','33.0%','32.7%'],['表面重复组',0,1,0],['观察到的时间跨度','2.16小时','44.62小时','190.8小时'],['有效运行耗时 / Token / 费用','不可得','不可得','不可得']], '是不同覆盖范围及裁判版本；前两份仅部分书籍。观察时间跨度包括暂停和退避，不当作构图用时。全书Codex首评与MiniMax旧复评是同输出的不同裁判结果，不能解释为方法退步。')
st=rd(root/'studies/d2l-historical-pilot-20260820/stability-metrics.json')
table('G. 跨运行稳定性（仅本方法历史快照）',['指标','结果'],[[label,f'{st[k]:.1%}'] for label,k in [('规范实体名Jaccard','entity_canonical_name_jaccard'),('实体保留率','entity_reference_retention'),('名称加别名词表Jaccard','entity_surface_vocabulary_jaccard'),('完整三元组Jaccard','assertion_triplet_jaccard'),('断言保留率','assertion_reference_retention'),('有向端点对Jaccard','assertion_endpoint_pair_jaccard')]],'共同范围164个原文单元；是exact27与fresh200两份历史快照比较，不是当前四方法的重复运行实验。')
ag=rd(root/'studies/d2l-historical-pilot-20260820/judge-agreement.json')['dimensions']
table('H. 裁判一致性（历史诊断）',['维度','同Codex反序复核一致率','Cohen kappa','共同任务数'],[[key,f"{value['mean_pairwise_agreement']:.1%}",f"{value['mean_pairwise_cohen_kappa']:.3f}",value['pairs'][0]['shared_tasks']] for key,value in ag.items()], '不是独立裁判或人工一致性。另有全书Codex与MiniMax同252任务一致率84.5%、kappa=0.538；v2.2冻结25条模型间复核23/25=92.0%。无人工校准分数。')
hy=rd(root/'outputs/d2l-hybrid-retrieval-20260903/lkg-results.json')
table('I. 检索候选对覆盖的影响（仅本方法）',['候选方案','恢复事实 / 48','覆盖比例'],[[label,str(hy[k]['yes'])+'/48',f"{hy[k]['yes']/48:.1%}"] for label,k in [('BM25 Top-10','baseline'),('E5 Top-10','embedding_only'),('两者候选并集','union')]],'并集平均14.875条候选，BM25与E5平均重叠5.125条。旧MiniMax覆盖与本地Codex复核混合，并集未全量重新调用同一裁判，不是严格同裁判消融。')
# Preserve the historical tables with their exact original denominators/configuration labels, without reproducing obsolete superiority claims.
hist=root/'studies/d2l-fullbook-open-baselines-20260826/RESULTS.md';hs=hist.read_text()
def extract(title,start,end):
 section=hs.split(start,1)[1].split(end,1)[0];ts=[line for line in section.splitlines() if line.startswith('|')]
 lines.extend(['## '+title,'']+ts+['','历史配置和口径，仅供追溯；不能替代当前配置。旧报告的通过率乘图规模是外推量，不是实际逐条核验数量，也不是本文推荐的总分。',''])
extract('J. 历史结构表','## D. 结构与规模','## E. 效率')
extract('K. 历史效率表','## E. 效率','## F. 派生')
extract('L. 历史派生产出估计（不作为主指标）','## F. 派生：可直接消费的产出','## 各列指标的含义')
lines+=['## 补充：引用长度（旧可靠性评测）','','仅对旧裁判判引用充分的样本计算中位数，非配对指标，不是引用效率证明。','']
current('引用长度描述',[[label]+[old['systems'][s][kind]['citation_length_descriptive_only'][key] for s in order] for label,kind,key in [('实体引用字符中位数','entity','median_characters'),('实体引用原文单元中位数','entity','median_units'),('断言引用字符中位数','assertion','median_characters'),('断言引用原文单元中位数','assertion','median_units')]])
sources=[root/'studies/d2l-fullbook-open-baselines-20260826/RESULTS.md',root/'studies/d2l-fullbook-open-baselines-20260826/REPORT.md',root/'studies/d2l-fullbook-vnext-20260826/REPORT.md',root/'studies/d2l-historical-pilot-20260820/REPORT.md',root/'studies/d2l-quality-v22-20260908/RESULTS.md',root/'outputs/d2l-quality-m3-official-c4-20260907-174524/REPORT.md',base/'results.json',root/'outputs/d2l-hybrid-retrieval-20260903/lkg-results.json',out/'REPORT.md']
lines+=['## 来源索引','']
for p in sources:
 link='//wsl.localhost/Ubuntu'+str(p);lines.append(f'- [{p.relative_to(root)}](<{link}>)')
(out/'ALL_METRICS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(out/'all-metrics-provenance.json').write_text(json.dumps({'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources_sha256':{str(p):sha(p) for p in sources},'corrected_v22_parts':parts,'construction_usage_with_historical_extraction':usage,'autoschemakg_full_structure':full},ensure_ascii=False,indent=2)+'\n')
print('report',str(out/'ALL_METRICS.md'));print('auto_full',full['documents'][0]);print('usage',usage);print('tokens_per_assertion',{s:(usage[s]['input_tokens']+usage[s]['output_tokens'])/struct[s]['summary']['assertion_count'] for s in usage})
