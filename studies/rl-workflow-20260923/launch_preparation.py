from pathlib import Path
import importlib.util,json,subprocess,sys,os
R=Path('/home/likefallwind/code/llm-graph-benchmark')
p=R/'studies/rl-workflow-20260923/run_pipeline.py'
spec=importlib.util.spec_from_file_location('rl_pipeline',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
job=mod.read(mod.OUT/'probe-jobs.json')[0]
facts=[]
for block in job['blocks']:
 u=next(u for u in block['evidence'] if len(u['text'])>=50)
 facts.append({'block_id':block['block_id'],'statement':'Synthetic parser test fact '+block['block_id'],
  'evidence_ids':[u['id']],'quotes':[{'id':u['id'],'text':u['text']}]})
qa=[{**facts[i],'question':'Synthetic parser test question '+str(i),'reference_answer':'Synthetic parser test answer'} for i in range(job['qa_count'])]
payload={'facts':facts,'qa':qa}
wire=lambda v:{'choices':[{'message':{'content':json.dumps(v)}}]}
mod.parse(wire(payload),job)
bad=json.loads(json.dumps(payload));bad['facts'][0]['evidence_ids']=['unknown-source-unit']
try:mod.parse(wire(bad),job)
except ValueError:pass
else:raise AssertionError('Missing source ID protection')
assert not (mod.OUT/'benchmark-provenance-reviewed.json').exists(), 'Reviewed benchmark already frozen; use launch_evaluation.py'
assert os.environ.get('MINIMAX_API_KEY')
with (mod.OUT/'pipeline.log').open('ab') as log:
 child=subprocess.Popen([sys.executable,str(p),'--prepare-only'],cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
mod.transport.write(mod.OUT/'launch.json',{'pid':child.pid,'stage':'prepare-only','max_http_concurrency':6})
print(json.dumps({'pid':child.pid,'out':str(mod.OUT),'stage':'source-only benchmark preparation','max_http_concurrency':6}))

