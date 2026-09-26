"""Migrate the frozen RL run after the sentence-period parser bug fix, offline."""
from pathlib import Path
import json
import shutil
import time
from llm_graph_benchmark.bundle import canonical_hash
from llm_graph_benchmark.workflow import engine, protocol, transport
from llm_graph_benchmark.workflow.preparation import read, sha, code_hashes, verify
from llm_graph_benchmark.workflow.reporting import report

root=Path(__file__).resolve().parents[2]
out=root/'outputs/rl-book2-20260923'
old=out/'evaluation-reviewed-v1'
new=out/'evaluation-reviewed-v1-periodfix'
assert not engine.active(old), 'Old run still active'
assert not new.exists(), 'Never overwrite a migrated run'
m=read(old/'manifest.json')
for name,h in m['frozen_files'].items():
    assert sha(old/name)==h, name
current=code_hashes()
assert set(current)==set(m['code_hashes'])
assert [k for k in current if current[k]!=m['code_hashes'][k]]==['workflow/protocol.py']
tasks=read(old/'tasks.json')
new.mkdir()
for name in m['frozen_files']:
    shutil.copy2(old/name,new/name)
shutil.copy2(old/'manifest.json',new/'parent-manifest.json')
m.update(code_hashes=current, parser_patch='description-sentence-period-v1',
         parent_run=str(old), parent_manifest_sha256=sha(old/'manifest.json'), migrated_at=time.time())
transport.write(new/'manifest.json',m)
(new/'results').mkdir()
missing={};copied=[]
for t in tasks:
    result=read(old/'results'/(t['id']+'.json'))
    assert result['task_hash']==canonical_hash(t)
    if result['status']=='done':
        assert result['value_hash']==canonical_hash(result['value'])
        shutil.copy2(old/'results'/(t['id']+'.json'),new/'results'/(t['id']+'.json'))
        copied.append(t['id'])
    else:
        assert t['metric']=='entity_description'
        missing[t['id']]=t
lookup={transport.digest(t['messages']):t for t in missing.values()}
candidates=[]
for d in (old/'api/requests').iterdir():
    request=read(d/'request.json');task=lookup.get(transport.digest(request['messages']))
    if not task: continue
    assert request['model']==m['model'] and request['max_tokens']==task['max_tokens']
    for path in d.glob('attempt-*.json'):
        a=read(path)
        candidates.append((a['started_at'],str(path),task,a))
restored=[]
for _,path,t,a in sorted(candidates,key=lambda row:(row[0],row[1])):
    if t['id'] not in missing: continue
    try:
        assert a['http_status']==200
        raw=json.loads(a['raw_body']);transport.validate_response(raw)
        value=protocol.parse(raw,t)
    except (ValueError,TypeError,KeyError,AssertionError): continue
    record={'task_id':t['id'],'task_hash':canonical_hash(t),'status':'done',
            'value':value,'value_hash':canonical_hash(value),
            'started_at':a['started_at'],'finished_at':a.get('request_finished_at'),
            'recovered_from':path,'recovered_source_sha256':sha(Path(path)),
            'parser_patch':'description-sentence-period-v1'}
    transport.write(new/'results'/(t['id']+'.json'),record)
    restored.append({'task_id':t['id'],'attempt':path,'sha256':sha(Path(path))})
    del missing[t['id']]
audit={'rule':'Preserve all successful results byte-for-byte. For failed cases select earliest historical response passing patched parser, regardless of semantic labels.',
       'parent':str(old),'copied_successful':len(copied),'recovered':restored,
       'pending':sorted(missing),'new_api_calls':0}
transport.write(new/'parser-recovery-audit.json',audit)
verify(new);report(new)
print(json.dumps({'run':str(new),'copied':len(copied),'recovered':len(restored),'pending':len(missing)}))
