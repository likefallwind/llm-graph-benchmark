from pathlib import Path
import shutil,json,time
from llm_graph_benchmark.workflow import transport
from llm_graph_benchmark.workflow.preparation import read,sha,verify
from llm_graph_benchmark.workflow.reporting import report
root=Path('/home/likefallwind/code/llm-graph-benchmark');out=root/'outputs/rl-baselines-20260923';old=out/'source-gateway-c6';new=out/'source-official-c4-resume'
assert not new.exists();shutil.copytree(old,new,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(out/'source/common.py',new/'common.py')
p=new/'gateway_adapter.py'
p.write_text('''"""Official MiniMax continuation; only whole JSON fence rendering is retained."""
from pathlib import Path
from llm_graph_benchmark.workflow import transport,engine
_NATIVE_SECRET=transport.load_secret
_NATIVE_VALIDATE=transport.validate_response
ENDPOINT='https://api.minimaxi.com/v1/text/chatcompletion_v2'
MODEL='MiniMax-M3'
SLOTS=Path('/home/likefallwind/code/llm-graph-benchmark/outputs/rl-baselines-20260923/official-request-slots-c4')
def load_secret():return _NATIVE_SECRET()
def validate_response(response):return _NATIVE_VALIDATE(response)
def install():
    transport.ENDPOINT=ENDPOINT
    transport.MODEL=MODEL
    transport.load_secret=load_secret
    transport.validate_response=validate_response
    engine.slots_path=lambda:SLOTS
'''+(old/'gateway_adapter.py').read_text().split('\ndef unwrap_json_fence',1)[1].join(['\ndef unwrap_json_fence','']))
p=new/'run_kggen.py';s=p.read_text().replace('workers=6','workers=4').replace('min(max_workers,6)','min(max_workers,4)').replace('executor 64 to 6','executor 64 to 4').replace('transport MiniMax API Gateway continuation','transport MiniMax official continuation; previous routes preserved').replace("'manifest.json'","'manifest-official-c4.json'");p.write_text(s)
p=new/'controller.py';s=p.read_text().replace('workers=6','workers=4').replace("'workers':6","'workers':4").replace("backend='api-gateway'","backend='minimax-official'").replace("model='minimax-m3'","model='MiniMax-M3'").replace('launch-gateway-manifest.json','launch-official-c4-manifest.json').replace("run=folder/'evaluation-gateway-c6'","run=folder/'evaluation-official-c4-resume'");p.write_text(s)
for name in ['graphrag','autoschemakg']:
 prior=out/name/'evaluation-gateway-c6';dest=out/name/'evaluation-official-c4-resume'
 m=verify(prior);dest.mkdir()
 for f in m['frozen_files']:shutil.copy2(prior/f,dest/f)
 shutil.copy2(prior/'manifest.json',dest/'parent-manifest.json')
 c=read(dest/'config.json');c['workers']=4;transport.write(dest/'config.json',c)
 m['workers']=4;m['frozen_files']['config.json']=sha(dest/'config.json');m['backend']={'route':'minimax-official','model':'MiniMax-M3','endpoint':'https://api.minimaxi.com/v1/text/chatcompletion_v2'};m['parent_run']=str(prior);m['parent_manifest_sha256']=sha(prior/'manifest.json');transport.write(dest/'manifest.json',m)
 (dest/'results').mkdir();count=0
 for f in (prior/'results').glob('*.json'):
  if read(f)['status']=='done':shutil.copy2(f,dest/'results'/f.name);count+=1
 transport.write(dest/'route-migration.json',{'parent':str(prior),'copied_successful':count,'backend':'minimax-official','workers':4,'at':time.time()});report(dest)
 print(json.dumps({'method':name,'preserved':count}))
# Adapt launcher; frozen source and old launch manifests remain untouched.
s=(root/'studies/rl-baselines-20260923/launch_gateway.py').read_text().replace('source-gateway-c6','source-official-c4-resume').replace('launch-gateway-manifest.json','launch-official-c4-manifest.json').replace('launch-gateway.json','launch-official-c4.json').replace('controller-gateway.log','controller-official-c4.log').replace("'workers':6","'workers':4").replace("'api-gateway'","'minimax-official'").replace("'minimax-m3'","'MiniMax-M3'").replace('OpenAI-compatible envelope; exact model validation; optional whole JSON fence removed without semantic changes; original response preserved','Official MiniMax envelope; whole JSON fence rendering only; original responses preserved')
(root/'studies/rl-baselines-20260923/launch_official_c4.py').write_text(s)
