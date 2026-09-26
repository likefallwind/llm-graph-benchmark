import json, collections
from pathlib import Path
from llm_graph_benchmark.workflow import protocol, transport, engine
r=Path('outputs/rl-book2-20260923/evaluation-reviewed-v1')
tasks=json.loads((r/'tasks.json').read_text())
failed={t['id']:t for t in tasks if json.loads((r/'results'/ (t['id']+'.json')).read_text()).get('status')=='failed'}
byhash={transport.digest(t['messages']):t for t in failed.values()}
counts=collections.Counter(); examples=[]; per=collections.defaultdict(collections.Counter)
for d in sorted((r/'api/requests').iterdir()):
    request=json.loads((d/'request.json').read_text()); matched=byhash.get(transport.digest(request['messages']))
    for p in sorted(d.glob('attempt-*.json')):
        a=json.loads(p.read_text()); t=matched
        if not t: continue
        try:
            raw=json.loads(a.get('raw_body','{}')); transport.validate_response(raw); protocol.parse(raw,t)
            cause='valid'
        except Exception as e: cause=type(e).__name__+': '+str(e)
        counts[cause]+=1;per[t['id']][cause]+=1
        if len(examples)<8 and 'description' in cause:
            val=protocol._json(raw); source=''.join(t['payload']['target']['description'].split());cursor=0
            for row in val.get('claims',[]):
                txt=''.join(row.get('text','').split()); start=source.find(txt,cursor)
                if start<0 or source[cursor:start].strip('，,。；;：:、'):
                    examples.append({'task':t['id'],'http':a.get('http_status'),'cause':cause,'expected_at_cursor':source[cursor:cursor+250],'returned':txt[:250],'start':start,'gap':source[cursor:start][:120] if start>=0 else None});break
                cursor=start+len(txt)
            else:
                examples.append({'task':t['id'],'cause':cause,'remaining':source[cursor:][:250]})
report={'state':engine.status(r),'failed_tasks':len(failed),'attempt_causes':dict(counts),'per_task':{k:dict(v) for k,v in per.items()},'examples':examples}
Path('outputs/rl-book2-20260923/failure-diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='per_task'},ensure_ascii=False,indent=2))

