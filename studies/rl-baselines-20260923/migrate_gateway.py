from pathlib import Path
import json,shutil,time,sys
from llm_graph_benchmark.workflow.preparation import read,sha,verify
from llm_graph_benchmark.workflow import protocol,transport
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow.reporting import report
root=Path('/home/likefallwind/code/llm-graph-benchmark');out=root/'outputs/rl-baselines-20260923'
for name in ['graphrag','autoschemakg']:
 old=out/name/'evaluation';new=out/name/'evaluation-gateway-c6';assert not new.exists()
 m=verify(old);new.mkdir()
 for file in m['frozen_files']:shutil.copy2(old/file,new/file)
 shutil.copy2(old/'manifest.json',new/'parent-manifest.json')
 config=read(new/'config.json');config['workers']=6;transport.write(new/'config.json',config)
 m['workers']=6;m['frozen_files']['config.json']=sha(new/'config.json');m['backend']={'route':'api-gateway','request_model':'minimax-m3','endpoint':'http://127.0.0.1:8111/v1/chat/completions'}
 m['parent_run']=str(old);m['parent_manifest_sha256']=sha(old/'manifest.json')
 transport.write(new/'manifest.json',m)
 copied=0;remaining=[]
 for t in read(old/'tasks.json'):
  p=old/'results'/(t['id']+'.json');r=read(p)
  if r['status']=='done':
   assert r['task_hash']==canonical_hash(t) and r['value_hash']==canonical_hash(r['value'])
   (new/'results').mkdir(exist_ok=True);shutil.copy2(p,new/'results'/p.name);copied+=1
  else:remaining.append({'task_id':t['id'],'metric':t['metric'],'prior_status':r['status']})
 transport.write(new/'route-migration.json',{'parent':str(old),'copied_successful':copied,'pending':remaining,'reason':'User authorized API Gateway MiniMax-M3, concurrency 6; prompts, samples and successful judgments unchanged','at':time.time()})
 print(json.dumps({'method':name,'copied':copied,'pending':remaining}))
 report(new)
# Persist the successful real probe as a normal validated result, without another call.
r=out/'graphrag/evaluation-gateway-c6';t=read(out/'gateway-probe/task.json');raw=read(out/'gateway-probe/response.json')
sys.path.insert(0,str(out/'source-gateway-c6'));from gateway_adapter import validate_response
validate_response(raw);v=protocol.parse(raw,t)
p=r/'results'/(t['id']+'.json');assert not p.exists()
transport.write(p,{'task_id':t['id'],'task_hash':canonical_hash(t),'status':'done','value':v,'value_hash':canonical_hash(v),'backend':'api-gateway','raw_response':str(out/'gateway-probe/response.json'),'response_sha256':sha(out/'gateway-probe/response.json')})
report(r);print('Gateway probe reused')
