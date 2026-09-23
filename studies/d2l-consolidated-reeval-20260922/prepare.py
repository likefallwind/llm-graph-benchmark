"""Prepare frozen tasks; no API calls or labels used in sampling."""
from pathlib import Path
import sys,json,hashlib,random,shutil,re,collections
ROOT=Path('/home/likefallwind/code/llm-graph-benchmark');HERE=Path(__file__).parent
sys.path[:0]=[str(ROOT/'src'),str(HERE)]
import assertion_ledger as ledger
import granularity
from llm_graph_benchmark.bundle import BenchmarkBundle,SubmissionBundle
from llm_graph_benchmark.identity import create_identity_tasks
from llm_graph_benchmark.retrieval import retrieve_qa_probes
from evaluate import wr,rd,sha,messages
BASE=ROOT/'outputs/d2l-baseline-correction-m3-c6-20260909-172849'
OLD=ROOT/'outputs/d2l-reliability-m3-c6-exploratory-20260920T132325Z'
ASSERT=ROOT/'outputs/d2l-assertion-ledger-v25-20260922-recovery02'
GRAN=ROOT/'outputs/d2l-granularity-m3-c6-20260922T030615Z'
PATHS={'ours':ROOT/'outputs/d2l-full1105-vnext-20260826/submission.json','graphrag':BASE/'graphrag/submission.json','autoschemakg':BASE/'autoschemakg/evaluation/semantic-submission.json','kggen':BASE/'kggen/submission.json'}

def split(text):return [x.strip() for x in re.findall(r'[^。！？\n]+[。！？]?|[。！？]',text) if x.strip()]
def make(metric,target,sources,segments=None,context=None):
 return {'metric':metric,'payload':{'metric':metric,'target':target,'segments':[{'id':'s'+str(i),'text':s} for i,s in enumerate(segments or [json.dumps(target,ensure_ascii=False)])],'sources':sources,'candidate_context':context or {}}}
def devs():
 tasks=[]
 def add(name,m,target,sources,expected,segs=None,context=None):
  t=make(m,target,[{'id':'P'+str(i),'text':s} for i,s in enumerate(sources)],segs,context);t.update(id='dev-'+name,expected=expected);tasks.append(t)
 add('entity-valid','entity_correctness',{'name':'学习率'},['学习率控制每次参数更新的步长。'],'correct')
 add('entity-fragment','entity_correctness',{'name':'学习率进口随机模型'},['学习率控制步长。代码为import random。'],'uncertain')
 add('entity-code','entity_correctness',{'name':'np.zeros'},['from mxnet import np\nx=np.zeros((2,3))'],'correct')
 add('entity-citation-name','entity_evidence',{'name':'学习率'},['学习率控制步长。'],'supported')
 add('entity-citation-wrong','entity_evidence',{'name':'学习率'},['本节介绍图像标注。'],'not_supported')
 add('entity-citation-empty','entity_evidence',{'name':'学习率'},[],'not_supported')
 add('type-super','entity_typing',{'name':'梯度下降','types':['优化算法','算法']},['梯度下降是一种通过沿负梯度更新参数来最小化目标的优化算法。'],'correct',['梯度下降的类型为优化算法','梯度下降的类型为算法'])
 add('type-extra','entity_typing',{'name':'优化器A','types':['优化算法','损失函数']},['A是一种优化算法，不是损失函数。'],'incorrect',['优化器A的类型为优化算法','优化器A的类型为损失函数'])
 add('type-context','entity_typing',{'name':'softmax','types':['损失函数']},['这里softmax只指将得分转换为概率的运算，不指任何损失函数。'],'incorrect')
 add('definition-good','entity_definition',{'name':'方法A','description':'方法A在条件H下减少误差。'},['条件H成立时，方法A减少误差。'],'supported',['方法A在条件H下减少误差。'])
 add('definition-extra','entity_definition',{'name':'方法A','description':'方法A减少误差，并且总是加速十倍。'},['方法A可以减少误差。'],'not_supported',['方法A减少误差，并且总是加速十倍。'])
 add('definition-nitpick','entity_definition',{'name':'方法A','description':'方法A兼顾准确性与速度。'},['方法A在准确性与速度之间采取折中。'],'supported',['方法A兼顾准确性与速度。'])
 add('definition-self','entity_definition',{'name':'方法A','description':'方法A加速十倍。'},['本节提出方法A。'],'not_supported',context={'definition':'方法A加速十倍。'})
 add('alias-good','alias_identity',{'name':'小批量随机梯度下降','alias':'mini-batch SGD'},['小批量随机梯度下降（mini-batch SGD）用于训练模型。'],'correct')
 add('alias-distinct','alias_identity',{'name':'NumPy','alias':'mxnet.np'},['mxnet.np是MXNet的兼容接口，并不是NumPy包本身。'],'incorrect')
 add('alias-no-evidence','alias_identity',{'name':'DataLoader','alias':'通用数据迭代器'},['这里DataLoader专指库A的类。'],'uncertain')
 add('split-distinct','identity_split',{'left':{'name':'sum'},'right':{'name':'sum'}},['左侧sum是库A的函数，右侧sum是库B中不同的函数；本节明确区分它们。'],'correct')
 add('split-duplicate','identity_split',{'left':{'name':'随机梯度下降'},'right':{'name':'SGD'}},['随机梯度下降又称SGD，二者在这里为同一个算法。'],'incorrect')
 add('split-generated-context','identity_split',{'left':{'name':'X'},'right':{'name':'X'}},['本节提到X，但未解释它。'],'uncertain',context={'left_definition':'X是方法','right_definition':'X是数据集'})
 add('qa-complete','book_qa',{'question':'训练需要哪两项？','reference_answer':'数据和模型。'},['训练需要数据。','训练还需要模型。'],'supported',['数据和模型。'])
 add('qa-noise','book_qa',{'question':'A包含什么？','reference_answer':'B。'},['A包含B。','无关实体Z用于图像。'],'supported',['B。'])
 add('qa-incomplete','book_qa',{'question':'训练需要哪两项？','reference_answer':'数据和模型。'},['训练需要数据。'],'not_supported',['数据和模型。'])
 add('qa-no-leak','book_qa',{'question':'A使用什么？','reference_answer':'B。'},[],'not_supported',['B。'])
 add('qa-paraphrase','book_qa',{'question':'A与B关系？','reference_answer':'A抑制B。'},['A降低B的活性。'],'supported',['A抑制B。'])
 # Retain representative assertion regression cases exactly; only change the evidence estimand.
 original=rd(ASSERT/'development.json')
 selected=[t for t in original if t['expected'] in {'correct','incorrect'}][:10]
 for i,t in enumerate(selected):
  a=json.loads(json.dumps(t));a.update(id='dev-citation-'+str(i),metric='assertion_evidence',expected='supported' if t['expected']=='correct' else 'not_supported');tasks.append(a)
 for i,t in enumerate(granularity.checks()):tasks.append({'id':'dev-gran-'+str(i),'metric':'granularity','original_task':t,'expected':t['expected']})
 return tasks

def prepare(run):
 if run.exists():raise ValueError('Fresh directory required')
 run.mkdir(parents=True)
 b=BenchmarkBundle.load(ROOT/'outputs/d2l-full1105-vnext-20260826/benchmark.json');units={d['document_id']:d['units'] for d in b.documents};um=b.unit_by_document
 submissions={s:SubmissionBundle.load(p) for s,p in PATHS.items()};docs={s:{d['document_id']:d for d in sub.payload['documents']} for s,sub in submissions.items()}
 em={s:{doc:{e['id']:e for e in d['entities']} for doc,d in ds.items()} for s,ds in docs.items()}
 tasks=[];key={};avail={};oldtasks=rd(OLD/'tasks.json');oldkey=rd(OLD/'private-key.json')
 def add(t,s,item,doc,original=None):
  uid='r_'+hashlib.sha256(json.dumps([20260922,s,item,doc,t],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:28];t['id']=uid
  t['oversized']=len(json.dumps(t,ensure_ascii=False).encode())>350000
  if uid in key:raise ValueError('duplicate task')
  tasks.append(t);key[uid]={'system':s,'item_id':item,'doc_id':doc,'metric':t['metric'],'original_id':original}
 def sources(doc,refs,expand=True):
  ids=sorted({x['unit_id'] for x in refs});assert all(i in um[doc] for i in ids)
  return ledger.section_context(units[doc],ids) if expand else [{'id':i,'text':um[doc][i]['text']} for i in ids]
 for s in PATHS:
  es=[e for d in docs[s].values() for e in d['entities']]
  avail[s]={'nodes':len(es),'with_types':sum(bool(e.get('types')) for e in es),'with_definition':sum(bool(e.get('definition')) and e.get('metadata',{}).get('definition_available') is not False for e in es),'with_aliases':sum(bool(e.get('aliases')) for e in es),'eligible_sample':collections.Counter()}
 for t in oldtasks:
  if t['payload']['kind']!='entity':continue
  k=oldkey[t['id']];s=k['system'];doc=k['doc_id'];e=em[s][doc][k['item_id']];assert t['payload']['target']['name']==e['name'];ctx=sources(doc,e.get('evidence',[]));name={'name':e['name']}
  for m in ['entity_correctness','entity_evidence']:
   add(make(m,name,ctx if m=='entity_correctness' else t['payload']['submitted_sources'],[e['name']]),s,e['id'],doc,t['id']);avail[s]['eligible_sample'][m]+=1
  if e.get('types'):
   add(make('entity_typing',dict(name,types=e['types']),ctx,[e['name']+'的类型为'+str(x) for x in e['types']]),s,e['id'],doc,t['id']);avail[s]['eligible_sample']['entity_typing']+=1
  if e.get('definition') and e.get('metadata',{}).get('definition_available') is not False:
   add(make('entity_definition',dict(name,description=e['definition']),ctx,split(e['definition'])),s,e['id'],doc,t['id']);avail[s]['eligible_sample']['entity_definition']+=1
 # Reuse exact latest 800 targets; citation-only context is copied from original references, not expanded.
 for t in rd(ASSERT/'tasks.json'):
  k=rd_assert_key[t['id']];old=next(x for x in oldtasks if x['id']==t['id']);a=json.loads(json.dumps(t));a.pop('id');a['metric']='assertion_evidence';a['payload']['reference_context']=old['payload']['submitted_sources'];add(a,k['system'],k['item_id'],k['doc_id'],t['id'])
 # Fixed collision sampling, no model-label-dependent selection.
 for s,sub in submissions.items():
  ident=create_identity_tasks(b,[sub],aliases_per_document=100,collision_pairs_per_document=100,seed=20260922)
  kmap={x['task_id']:x for x in ident.key}
  for t in ident.tasks:
   k=kmap[t['task_id']];doc=k['document_id'];c=t['content'];m=t['kind']
   if m=='alias_identity':
    e=em[s][doc][k['item_id'].split(':alias:')[0]];tar={'name':c['name'],'alias':c['alias']};ctx=sources(doc,e.get('evidence',[]));cc={'definition':c['definition'],'types':c['types']}
   else:
    l,rr=k['item_id'].split(':split:');le,re_=em[s][doc][l],em[s][doc][rr];tar={'left':{'name':le['name'],'source_ids':sorted({v['unit_id'] for v in le.get('evidence',[])})},'right':{'name':re_['name'],'source_ids':sorted({v['unit_id'] for v in re_.get('evidence',[])})}};ctx=sources(doc,le.get('evidence',[])+re_.get('evidence',[]));cc={'left':c['left'],'right':c['right'],'shared_surfaces':c['shared_surfaces']}
   add(make(m,tar,ctx,context=cc),s,k['item_id'],doc);avail[s]['eligible_sample'][m]+=1
  # Use the repository's unmodified graph-only BM25 retriever for every method.
  retrieved=retrieve_qa_probes(b,[sub],top_k=10);wr(run/'retrieval'/(s+'.json'),retrieved)
  qp={q['qa_id']:q for q in b.qa_probes}
  for rr in retrieved:
   q=qp[rr['qa_id']];doc=q['document_id'];am={a['id']:a for a in docs[s][doc]['assertions']};ev=[]
   for i,aid in enumerate(rr['assertion_ids']):
    a=am[aid];tar={'subject':em[s][doc][a['subject_id']]['name'],'predicate':a['predicate'],'object':em[s][doc][a['object_id']]['name'],'description':a.get('text',''),'scope':a.get('scope',''),'polarity':a.get('polarity','positive')};ev.append({'id':'C'+str(i),'text':json.dumps(tar,ensure_ascii=False)})
   add(make('book_qa',{'question':q['question'],'reference_answer':q['reference_answer']},ev,split(q['reference_answer'])),s,q['qa_id'],doc);avail[s]['eligible_sample']['book_qa']+=1
  print('prepared',s,dict(avail[s]['eligible_sample']),flush=True)
 # Only retry the 24 missing granularity judgments; preserve the other 776 verbatim.
 gkey=rd(GRAN/'private-key.json');preserved={}
 for gt in rd(GRAN/'tasks.json'):
  f=GRAN/'results'/(gt['id']+'.json');r=rd(f)
  if r['status']=='done':
   dest=run/'granularity-preserved'/f.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(f,dest);preserved[f.name]=sha(dest)
  else:
   assert r['status']=='failed';k=gkey[gt['id']];add({'metric':'granularity','original_task':gt},k['system'],k['item_id'],k.get('doc_id','d2l-zh-official'),gt['id']);wr(run/'prior-granularity-failures'/f.name,r)
 random.Random(20260922).shuffle(tasks)
 pilot=[]
 for s in PATHS:
  for m in sorted({x['metric'] for x in tasks if key[x['id']]['system']==s}):
   eligible=sorted([x for x in tasks if key[x['id']]['system']==s and x['metric']==m],key=lambda x:x['id']);pilot.extend(random.Random('pilot:'+s+':'+m).sample(eligible,min(2,len(eligible))))
 for n,v in [('tasks.json',tasks),('private-key.json',key),('availability.json',avail),('pilot.json',pilot),('development.json',devs()),('preserved-assertion-results.json',{f.name:sha(f) for f in (ASSERT/'results').glob('q_*.json')})]:wr(run/n,v)
 for n in ['evaluate.py','prepare.py','driver.py','finalize.py','PROTOCOL.md','transport.py','assertion_ledger.py','alignment.py','granularity.py']:shutil.copy2(HERE/n,run/n)
 inputs=list(PATHS.values())+[OLD/'tasks.json',OLD/'private-key.json',ASSERT/'tasks.json',ASSERT/'summary.json',GRAN/'tasks.json',GRAN/'prompts.json',ROOT/'outputs/d2l-full1105-vnext-20260826/documents.jsonl',b.path.parent/'qa_probes.jsonl']
 frozen={str(f.relative_to(run)):sha(f) for f in run.rglob('*') if f.is_file() and 'granularity-preserved' not in str(f) and 'prior-granularity-failures' not in str(f)}
 wr(run/'manifest.json',{'protocol':'consolidated-reeval-v1','workers':6,'model':'MiniMax-M3','seed':20260922,'frozen_files':frozen,'input_hashes':{str(f):sha(f) for f in inputs},'preserved_granularity_sha256':preserved,'assertion_run':str(ASSERT),'granularity_run':str(GRAN),'historical_reliability_run':str(OLD),'counts':dict(collections.Counter(t['metric'] for t in tasks)),'oversized':sum(t['oversized'] for t in tasks),'independent_validation':False})
 print(json.dumps({'run':str(run),'total':len(tasks),'pilot':len(pilot),'development':len(devs()),'metrics':dict(collections.Counter(t['metric'] for t in tasks)),'oversized':sum(t['oversized'] for t in tasks)},ensure_ascii=False))

if __name__=='__main__':
 rd_assert_key=rd(ASSERT/'private-key.json');prepare(Path(sys.argv[1]))
