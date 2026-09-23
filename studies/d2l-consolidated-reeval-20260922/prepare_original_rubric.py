from pathlib import Path
import sys,json,hashlib,shutil,collections,random
R=Path('/home/likefallwind/code/llm-graph-benchmark'); H=Path(__file__).parent
sys.path[:0]=[str(R/'src'),str(R/'studies/d2l-fullbook-open-baselines-20260826')]
from llm_graph_benchmark.bundle import BenchmarkBundle,SubmissionBundle
from llm_graph_benchmark.sampling import create_blind_sample
from llm_graph_benchmark.identity import create_identity_tasks
from llm_graph_benchmark.qa import create_qa_tasks
import judge_tasks as oldjudge
run=R/'outputs/d2l-baseline-original-rubric-m3-c6-20260922'; assert not run.exists();run.mkdir()
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(l) for l in p.read_text().splitlines() if l]
def wr(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=R/'outputs/d2l-baseline-correction-m3-c6-20260909-172849'; parent=R/'outputs/d2l-consolidated-m3-c6-20260922-v6'
paths={'graphrag':base/'graphrag/submission.json','autoschemakg':base/'autoschemakg/evaluation/semantic-submission.json','kggen':base/'kggen/submission.json'}
b=BenchmarkBundle.load(R/'outputs/d2l-full1105-vnext-20260826/benchmark.json'); tasks=[]; key={}; exclusions=[];inputs={};seed=20260820
for system,path in paths.items():
 sub=SubmissionBundle.load(path);inputs[str(path)]=sha(path);em={(d['document_id'],e['id']):e for d in sub.payload['documents'] for e in d['entities']}
 sample=create_blind_sample(b,[sub],entities_per_document=30,assertions_per_document=0,seed=seed)
 ident=create_identity_tasks(b,[sub],aliases_per_document=30,collision_pairs_per_document=30,seed=seed)
 retrieval=rd(parent/'retrieval'/(system+'.json')); assert all(r['retriever_params']=={'top_k':10,'k1':1.2,'b':0.75} for r in retrieval)
 qa=create_qa_tasks(b,[sub],retrieval,seed=seed);wr(run/'retrieval'/(system+'.json'),retrieval)
 for output in [sample,ident,qa]:
  km={x['task_id']:x for x in output.key}
  for t in output.tasks:
   k=km[t['task_id']];m=t['kind']
   if m=='entity_admission':continue
   if m in {'entity_typing','entity_definition_grounding'}:
    e=em[(k['document_id'],k['item_id'])]
    absent=(not e.get('types')) if m=='entity_typing' else (not e.get('definition') or e.get('metadata',{}).get('definition_available') is False)
    if absent:exclusions.append({'system':system,'task_id':t['task_id'],'metric':m,'reason':'native field unavailable'});continue
   messages=[{'role':'system','content':oldjudge.SYSTEM_PROMPT},{'role':'user','content':oldjudge.build_prompt(t)}]
   tasks.append({'id':t['task_id'],'metric':m,'messages':messages,'task':t,'max_tokens':6144});key[t['task_id']]={**k,'system':system}
# Preserve our actual original M3 judgments; no new API jobs for our five metrics.
ourdir=R/'outputs/d2l-full1105-vnext-20260826/evaluation'; ourtasks={t['task_id']:t for t in jl(ourdir/'all-tasks.jsonl')}; ownmetrics={'entity_typing','entity_definition_grounding','alias_identity','identity_split','book_qa'}
latest={}
for row in jl(R/'outputs/d2l-fullbook-judge-v2-20260826/judgments.jsonl'):
 if row['task_id'] in ourtasks and ourtasks[row['task_id']]['kind'] in ownmetrics:
  if row['label']!='error':latest[row['task_id']]={**row,'metric':ourtasks[row['task_id']]['kind']}
assert len(latest)==144
wr(run/'preserved-ours.json',list(latest.values()))
# Reproduce original entity sample IDs as a check that sampling code/settings match.
ownsub=SubmissionBundle.load(R/'outputs/d2l-full1105-vnext-20260826/submission.json')
chk=create_blind_sample(b,[ownsub],entities_per_document=30,assertions_per_document=0,seed=seed)
assert {t['task_id'] for t in chk.tasks}=={i for i,t in ourtasks.items() if t['kind'].startswith('entity_')}
# Only complete failed granularity tasks. Reuse successful recovery judgments already obtained.
sys.path.insert(0,str(parent)); import granularity
G=R/'outputs/d2l-granularity-m3-c6-20260922T030615Z';gkey=rd(G/'private-key.json'); prior_tasks=rd(parent/'tasks.json'); prior_key=rd(parent/'private-key.json'); recovery={prior_key[t['id']]['original_id']:t['id'] for t in prior_tasks if t['metric']=='granularity'}
gran_preserved={};recovered=0
for t in rd(G/'tasks.json'):
 r=rd(G/'results'/(t['id']+'.json'))
 if r['status']=='done':gran_preserved[t['id']]=r;continue
 k=gkey[t['id']];uid=t['id'];tasks.append({'id':uid,'metric':'granularity','messages':granularity.messages(t,granularity.PROMPT),'task':t,'max_tokens':4096});key[uid]={**k,'system':k['system']}
 f=parent/'results'/(recovery[uid]+'.json')
 if f.exists() and rd(f)['status']=='done':
  old=rd(f);wr(run/'results'/(uid+'.json'),{'task_id':uid,'metric':'granularity','status':'done','value':old['value'],'reused_from':str(f),'source_sha256':sha(f)});recovered+=1
wr(run/'granularity-preserved.json',gran_preserved)
random.Random(20260826).shuffle(tasks);wr(run/'tasks.json',tasks);wr(run/'private-key.json',key);wr(run/'excluded-fields.json',exclusions)
for name,source in {'judge_tasks.py':R/'studies/d2l-fullbook-open-baselines-20260826/judge_tasks.py','review_tasks.py':R/'studies/d2l-fullbook-open-baselines-20260826/review_tasks.py','transport.py':parent/'transport.py','granularity.py':parent/'granularity.py','runner.py':H/'original_rubric_runner.py'}.items():shutil.copy2(source,run/name)
protocol='''# 原通用裁判：基线修正补测

只替换已修正的 GraphRAG、AutoSchemaKG、KGGen 产物。原 SYSTEM_PROMPT、各指标问题、任务展示、返回标签和聚合定义保持原版；不增加案例规则、不设置期望分数。每项最多30个实体/身份任务，原种子20260820；24题、同BM25 Top10。无原生字段记N/A，不将占位定义送评。

MiniMax-M3，temperature=0，6个共享请求槽含重试。每请求最多3次技术重试，结束后仅技术失败补一次；有效pass/fail/uncertain均保留。不使用已撤回方案的语义标签。我们的方法144条旧M3标签原样保留；新指标最多282条。粒度仅补原24条技术失败，并复用此前已成功恢复的同提示结果。

沿用旧协议的限制：实体等证据展示最多1200字符；身份拆分展示双方描述和共享表面信息，原脚本未展示原文证据；QA每条候选最多500字符，并展示参考来源。为仅替换复现产物，本轮不修改这些历史输入行为。因此本轮是原裁判口径下的对比，不是对裁判可靠性的重新验证，也不宣称完整上下文下的金标准正确率。

主表沿用历史pass/(pass+fail)，同时列出pass/fail/uncertain、技术缺失及全样本支持率；不能把uncertain等同于错。完整断言800条、已修正图的实体/引用、48覆盖、图规模与million tokens成本都不重评。来源和提示冻结哈希见manifest.json。
'''
(run/'PROTOCOL.md').write_text(protocol)
wr(run/'manifest.json',{'protocol':'original-rubric-baseline-correction-only','model':'MiniMax-M3','workers':6,'sample_seed':seed,'counts':dict(collections.Counter(t['metric'] for t in tasks)),'counts_by_system':dict(collections.Counter(key[t['id']]['system'] for t in tasks)),'reused_granularity_recoveries':recovered,'original_judge_source':str(R/'studies/d2l-fullbook-open-baselines-20260826/judge_tasks.py'),'frozen_files':{str(f.relative_to(run)):sha(f) for f in run.rglob('*') if f.is_file() and 'results/' not in str(f.relative_to(run))},'input_hashes':inputs,'independent_validation':False})
(H/'LATEST_RUN.txt').write_text(str(run)+'\n');print(json.dumps({'run':str(run),'total':len(tasks),'new_metric_tasks':sum(t['metric']!='granularity' for t in tasks),'already_recovered_granularity':recovered,'counts':dict(collections.Counter(t['metric'] for t in tasks))},ensure_ascii=False))
