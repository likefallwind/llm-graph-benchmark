from pathlib import Path
import json, shutil, time
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow import engine,protocol,transport
from llm_graph_benchmark.workflow.preparation import read,sha
from llm_graph_benchmark.workflow.reporting import report
from restore_boundary_and import restore_boundary_and
r=Path('/home/likefallwind/code/llm-graph-benchmark/outputs/rl-book2-20260923/evaluation-c4-final')
assert not engine.active(r)
tasks=read(r/'tasks.json');failed={transport.digest(t['messages']):t for t in tasks if read(r/'results'/(t['id']+'.json'))['status']=='failed'}
candidates=[]
for d in (r/'api/requests').iterdir():
    task=failed.get(transport.digest(read(d/'request.json')['messages']))
    if task:
        for p in d.glob('attempt-*.json'):
            a=read(p);candidates.append((a['started_at'],str(p),task,a))
restored=[];done=set()
for _,path,t,a in sorted(candidates,key=lambda x:(x[0],x[1])):
    if t['id'] in done:continue
    try:
        raw=json.loads(a['raw_body']);transport.validate_response(raw)
        original=protocol._json(raw)
        patched,edits=restore_boundary_and(t['payload']['target']['description'],original)
        if not edits:continue
        wire={'choices':[{'message':{'content':json.dumps(patched,ensure_ascii=False)}}]}
        value=protocol.parse(wire,t)
    except (ValueError,KeyError,TypeError):continue
    audit={'rule':'Restore only verbatim omitted boundary and; earliest valid response, no label-based selection','source':path,'source_sha256':sha(Path(path)),'original':original,'rendered':patched,'edits':edits}
    transport.write(r/'rendering-recovery'/(t['id']+'.json'),audit)
    prior=r/'results'/(t['id']+'.json');shutil.copy2(prior,r/'rendering-recovery'/(t['id']+'-failed.json'))
    transport.write(prior,{'task_id':t['id'],'task_hash':canonical_hash(t),'status':'done','value':value,'value_hash':canonical_hash(value),'recovered_from':path,'recovery_audit':'rendering-recovery/'+t['id']+'.json','finished_at':time.time()})
    done.add(t['id']);restored.append(t['id'])
print(json.dumps({'restored':restored,'complete':report(r)['complete']}))
