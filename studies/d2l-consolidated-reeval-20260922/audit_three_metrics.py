from pathlib import Path
import json,collections,statistics,sys
R=Path('/home/likefallwind/code/llm-graph-benchmark');B=R/'outputs/d2l-baseline-original-rubric-m3-c6-20260922';sys.path.insert(0,str(B));import review_tasks
rd=lambda p:json.loads(p.read_text())
ts=rd(B/'tasks.json');key=rd(B/'private-key.json');ourts={t['task_id']:t for t in [json.loads(x) for x in (R/'outputs/d2l-full1105-vnext-20260826/evaluation/all-tasks.jsonl').read_text().splitlines()]};rows=[]
for t in ts:
 if key[t['id']]['system']=='graphrag' and t['metric'] in ['entity_typing','entity_definition_grounding']:rows.append(('graphrag',t['task'],rd(B/'results'/(t['id']+'.json'))['value']))
for v in rd(B/'preserved-ours.json'):
 if v['metric'] in ['entity_typing','entity_definition_grounding']:rows.append(('ours',ourts[v['task_id']],v))
for s in ['ours','graphrag']:
 rs=[(t,v) for ss,t,v in rows if ss==s and t['kind']=='entity_typing'];es=[t['content'] for t,v in rs];print('STATS',s,{'type_counts':dict(collections.Counter(x for e in es for x in e['types'])),'avg_types':statistics.mean(len(e['types']) for e in es),'description_length_median':statistics.median(len(e['definition']) for e in es),'evidence_truncated':sum(len(' | '.join(dict.fromkeys(str(x.get('unit',x).get('text','')).strip() for x in t.get('evidence',[]))))>1200 for t,v in rs)})
for s,t,v in rows:
 if t['kind']=='entity_definition_grounding' or (s=='ours' and v['label']!='pass'):
  print('CASE',json.dumps({'system':s,'id':t['task_id'],'metric':t['kind'],'name':t['content']['name'],'types':t['content']['types'],'definition':t['content']['definition'][:420],'label':v['label'],'reason':v['reason']},ensure_ascii=False))
p=R/'outputs/d2l-baseline-correction-m3-c6-20260909-172849/graphrag/evaluation';inp=rd(p/'inputs.json');print('COVERAGE KEYS',list(inp['fact_tasks'][0]),list(inp['fact_tasks'][0]['content']))
for t in inp['fact_tasks']:
 v=rd(p/'results'/(t['task_id']+'.json'));v=v.get('result',v);print('COVER',json.dumps({'id':t['task_id'],'fact':t['content']['source_fact'],'judgment':v},ensure_ascii=False)[:900])
