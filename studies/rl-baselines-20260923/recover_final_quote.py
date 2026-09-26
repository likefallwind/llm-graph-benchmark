from pathlib import Path
import sys,json,shutil,time
ROOT=Path('/home/likefallwind/code/llm-graph-benchmark');OUT=ROOT/'outputs/rl-baselines-20260923';RUN=OUT/'graphrag/evaluation-official-c4-resume'
sys.path.insert(0,str(OUT/'source-official-c4-resume'))
from gateway_adapter import unwrap_json_fence
from llm_graph_benchmark.workflow import engine,protocol,transport
from llm_graph_benchmark.workflow.preparation import read,sha
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow.reporting import report
with engine.run_lock(RUN):
 audit=RUN/'short-evidence-id-retry';info=read(audit/'input.json');mapping=info['evidence_id_mapping']
 t=next(t for t in read(RUN/'tasks.json') if t['id']==info['task_id'])
 source=''.join(t['payload']['target']['description'].split());assert source.endswith('"')
 records=sorted((read(p)['started_at'],str(p),read(p)) for p in (audit/'api/requests').glob('*/attempt-*.json'))
 for _,path,a in records:
  try:
   raw=json.loads(a['raw_body']);transport.validate_response(raw);v=protocol._json(unwrap_json_fence(raw))
   if isinstance(v,list):v={'claims':v}
   # Restore only the final quotation mark, and only after proving all other
   # source characters already occur in the exact original order.
   if ''.join(''.join(c['text'].split()) for c in v['claims'])!=source[:-1]:continue
   before=json.loads(json.dumps(v));v['claims'][-1]['text']+='"'
   for c in v['claims']:c['evidence_ids']=[mapping[i] for i in c['evidence_ids']]
   value=protocol.parse({'choices':[{'message':{'content':json.dumps(v,ensure_ascii=False)}}]},t)
  except (ValueError,KeyError,TypeError):continue
  transport.write(audit/'rendering-recovery.json',{'rule':'Earliest full-content response, append only original trailing quotation mark; map display IDs back; labels/reasons untouched','source':path,'source_sha256':sha(Path(path)),'before':before,'after':v})
  p=RUN/'results'/(t['id']+'.json');shutil.copy2(p,audit/'prior-failure.json')
  transport.write(p,{'task_id':t['id'],'task_hash':canonical_hash(t),'status':'done','value':value,'value_hash':canonical_hash(value),'finished_at':time.time(),'recovery_audit':str(audit/'rendering-recovery.json')})
  break
 else:raise RuntimeError('No safe complete rendering found')
 s=report(RUN);print(json.dumps({'complete':s['complete'],'done':s['done'],'total':s['total']}))
