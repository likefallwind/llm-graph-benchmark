"""Retry only malformed description judgments, with the existing format contract explicit."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys,json,time,shutil
ROOT=Path('/home/likefallwind/code/llm-graph-benchmark');OUT=ROOT/'outputs/rl-baselines-20260923';RUN=OUT/'graphrag/evaluation-official-c4-resume'
sys.path.insert(0,str(OUT/'source-official-c4-resume'))
from gateway_adapter import install,GatewayClient
install()
from llm_graph_benchmark.workflow import engine,protocol,transport
from llm_graph_benchmark.workflow.preparation import read,sha
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow.reporting import report
NOTE='输出格式核对：claims.text 必须按顺序完整摘录原描述，保留原有字符，包括末尾的引号或 > 等符号；evidence_ids 只能逐字选用本次输入 evidence 中的 id，不得改变数字或自行生成编号。评分标准仍按原任务，支持、不支持、不确定均可如实返回。'
def main():
 with engine.run_lock(RUN):
  tasks=[t for t in read(RUN/'tasks.json') if read(RUN/'results'/(t['id']+'.json'))['status']!='done']
  assert all(t['metric']=='entity_description' for t in tasks)
  audit=RUN/'format-retry-20260924';audit.mkdir(exist_ok=True)
  transport.write(audit/'contract.json',{'note':NOTE,'reason':'Original full-span and evidence-ID requirements; no semantic rubric changes','task_ids':[t['id'] for t in tasks],'model':'MiniMax-M3','concurrency':4})
  client=GatewayClient(audit/'api',engine.slots_path(),concurrency=4)
  def one(t):
   messages=t['messages']+[{'role':'user','content':NOTE}]
   transport.write(audit/(t['id']+'-request.json'),{'base_task_hash':canonical_hash(t),'messages':messages,'max_tokens':t['max_tokens']})
   raw=client.complete(messages,max_tokens=t['max_tokens'],validator=lambda r:protocol.parse(r,t))
   value=protocol.parse(raw,t)
   transport.write(audit/(t['id']+'-response.json'),raw)
   p=RUN/'results'/(t['id']+'.json');shutil.copy2(p,audit/(t['id']+'-prior-failure.json'))
   transport.write(p,{'task_id':t['id'],'task_hash':canonical_hash(t),'status':'done','value':value,'value_hash':canonical_hash(value),'finished_at':time.time(),'format_retry_audit':str(audit/(t['id']+'-request.json')),'response_sha256':sha(audit/(t['id']+'-response.json'))})
   return t['id']
  with ThreadPoolExecutor(max_workers=4) as pool:
   futures=[pool.submit(one,t) for t in tasks]
   for f in futures:
    try:print(json.dumps({'completed':f.result()}),flush=True)
    except Exception as e:print(json.dumps({'error_type':type(e).__name__}),flush=True)
  summary=report(RUN);print(json.dumps({'complete':summary['complete'],'done':summary['done'],'total':summary['total']}),flush=True)
if __name__=='__main__':main()
