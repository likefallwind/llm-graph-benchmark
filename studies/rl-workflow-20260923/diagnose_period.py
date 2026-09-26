import json, collections, inspect
from pathlib import Path
from llm_graph_benchmark.workflow import protocol, transport
r=Path('outputs/rl-book2-20260923/evaluation-reviewed-v1')
tasks=json.loads((r/'tasks.json').read_text()); failed={t['id']:t for t in tasks if json.loads((r/'results'/(t['id']+'.json')).read_text()).get('status')=='failed'}
byhash={transport.digest(t['messages']):t for t in failed.values()}
namespace=dict(vars(protocol)); code=inspect.getsource(protocol.parse).replace('separators = "，,。；;：:、"','separators = "，,。；;：:、."'); exec(code,namespace)
counts=collections.Counter(); recovered=set(); examples={}; http=collections.Counter()
for d in sorted((r/'api/requests').iterdir()):
    req=json.loads((d/'request.json').read_text());t=byhash.get(transport.digest(req['messages']))
    if not t: continue
    for p in sorted(d.glob('attempt-*.json')):
        a=json.loads(p.read_text());http[str(a.get('http_status'))]+=1
        try:
            raw=json.loads(a.get('raw_body','{}'));transport.validate_response(raw);namespace['parse'](raw,t)
            cause='passes_with_english_period';recovered.add(t['id'])
        except Exception as e: cause=type(e).__name__+': '+str(e)
        counts[cause]+=1
        if cause=='ValueError: Non-stop completion':examples.setdefault('finish_reasons',[]).append(raw.get('choices',[{}])[0].get('finish_reason'))
result={'note':'Offline diagnostic only. No scores or frozen code modified. Dot allowance is a candidate fix, not final parser migration.', 'remaining_tasks':len(failed),'http_status_counts':dict(http),'replay_attempt_counts':dict(counts),'tasks_with_valid_response_if_period_allowed':len(recovered),'recoverable_task_ids':sorted(recovered),'still_unresolved_task_ids':sorted(set(failed)-recovered),**examples}
Path('outputs/rl-book2-20260923/failure-period-diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
