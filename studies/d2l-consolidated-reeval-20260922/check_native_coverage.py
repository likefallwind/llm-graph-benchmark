from pathlib import Path
import json,collections,sys
R=Path('/home/likefallwind/code/llm-graph-benchmark');P=R/'outputs/d2l-baseline-correction-m3-c6-20260909-172849/graphrag';rd=lambda p:json.loads(p.read_text());inp=rd(P/'evaluation/inputs.json');sub=rd(P/'submission.json');docs={d['document_id']:d for d in sub['documents']};maps={i:({e['id']:e for e in d['entities']},{a['id']:a for a in d['assertions']}) for i,d in docs.items()};ret={v['probe_id']:v for v in inp['retrieval']};keys={v['task_id']:v for v in inp['fact_key']};verified=0;labels=collections.Counter();issues=[]
for t in inp['fact_tasks']:
 k=keys[t['task_id']];em,am=maps[k['document_id']];rr=ret[k['item_id']];cs=t['content']['candidate_graph_assertions'];assert len(cs)==10
 for c,aid in zip(cs,rr['assertion_ids']):
  a=am[aid];expected={'subject':em[a['subject_id']]['name'],'predicate':a['predicate'],'object':em[a['object_id']]['name'],'text':a['text'],'scope':a.get('scope',''),'polarity':a.get('polarity','positive')};assert c==expected;verified+=1
 v=rd(P/'evaluation/results'/(t['task_id']+'.json'))['value'];labels[v['covered']]+=1
 if any(w in v['reason'] for w in ['缺失','未显式','缺少','未覆盖','未提及条件','未提及代价']):issues.append({'id':t['task_id'],'fact':t['content']['source_fact'],'reason':v['reason']})
print(json.dumps({'verified_native_candidates':verified,'unique_probe_ids':len({k['item_id'] for k in keys.values()}),'labels':labels,'explicit_omission_reasons':issues},ensure_ascii=False))
B=R/'outputs/d2l-baseline-original-rubric-m3-c6-20260922';sys.path.insert(0,str(B));import review_tasks
ot={t['task_id']:t for t in [json.loads(x) for x in (R/'outputs/d2l-full1105-vnext-20260826/evaluation/all-tasks.jsonl').read_text().splitlines()]}
for i in ['t_b9d5a3cfe47577c8301c','t_2dc203d2b99890d327d0']:print('OUR DEFINITION INPUT',review_tasks.render_task(ot[i]))
