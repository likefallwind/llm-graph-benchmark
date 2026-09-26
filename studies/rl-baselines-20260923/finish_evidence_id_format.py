from pathlib import Path
import sys,json,copy,shutil,time
ROOT=Path('/home/likefallwind/code/llm-graph-benchmark');OUT=ROOT/'outputs/rl-baselines-20260923';RUN=OUT/'graphrag/evaluation-official-c4-resume'
sys.path.insert(0,str(OUT/'source-official-c4-resume'))
from gateway_adapter import install,GatewayClient
install()
from llm_graph_benchmark.workflow import engine,protocol,transport
from llm_graph_benchmark.workflow.preparation import read,sha
from llm_graph_benchmark.workflow.reporting import report
from llm_graph_benchmark.bundle import canonical_hash
with engine.run_lock(RUN):
 tasks=[t for t in read(RUN/'tasks.json') if read(RUN/'results'/(t['id']+'.json'))['status']!='done'];assert len(tasks)==1
 t=tasks[0];shown=copy.deepcopy(t);mapping={}
 for i,e in enumerate(shown['payload']['evidence'],1):
  alias=f'E{i}';mapping[alias]=e['id'];e['id']=alias
 messages=protocol.messages(shown)+[{'role':'user','content':'请核对输出格式：text 按顺序完整覆盖原描述，包括末尾的符号；evidence_ids 只能选择输入 evidence 的 id。评分仍按原任务，如实判断。'}]
 audit=RUN/'short-evidence-id-retry';audit.mkdir(exist_ok=True)
 transport.write(audit/'input.json',{'task_id':t['id'],'base_task_hash':canonical_hash(t),'messages':messages,'evidence_id_mapping':mapping,'scope':'Bijective display-ID renaming only; source text and semantic rubric unchanged'})
 client=GatewayClient(audit/'api',engine.slots_path(),concurrency=4)
 def parse(raw):
  value=protocol.parse(raw,shown)
  for row in value['claims']:row['evidence_ids']=[mapping[x] for x in row['evidence_ids']]
  return protocol.parse({'choices':[{'message':{'content':json.dumps(value,ensure_ascii=False)}}]},t)
 raw=client.complete(messages,max_tokens=t['max_tokens'],validator=parse);value=parse(raw)
 transport.write(audit/'response.json',raw)
 p=RUN/'results'/(t['id']+'.json');shutil.copy2(p,audit/'prior-failure.json')
 transport.write(p,{'task_id':t['id'],'task_hash':canonical_hash(t),'status':'done','value':value,'value_hash':canonical_hash(value),'finished_at':time.time(),'evidence_id_mapping_audit':str(audit/'input.json'),'response_sha256':sha(audit/'response.json')})
 s=report(RUN);print(json.dumps({'complete':s['complete'],'done':s['done'],'total':s['total']}))
