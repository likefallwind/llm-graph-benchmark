from pathlib import Path
import json,collections
R=Path('/home/likefallwind/code/llm-graph-benchmark/outputs');out=R/'d2l-final-comparison-20260922';g=json.loads((R/'d2l-baseline-correction-m3-c6-20260909-172849/graphrag/submission.json').read_text());es=[e for d in g['documents'] for e in d['entities']];freq=collections.Counter(x for e in es for x in set(e.get('types',[])));examples=collections.defaultdict(list)
for e in es:
 for t in e.get('types',[]):
  if len(examples[t])<3:examples[t].append(e['name'])
p=R/'d2l-three-metrics-repaired-m3-c6-20260922';ts=json.loads((p/'tasks.json').read_text());key=json.loads((p/'private-key.json').read_text());sample=[{'id':t['id'],**t['payload']['target'],'judgment':json.loads((p/'results'/(t['id']+'.json')).read_text())['value']} for t in ts if t['metric']=='entity_typing' and key[t['id']]['system']=='graphrag'];sample.sort(key=lambda x:x['id'])
escape=lambda x:str(x).replace('|','\\|').replace('\n',' ')
lines=['# 当前GraphRAG实体类型清单','','节点11,407；原样去重类型标签1,058。按字符串统计，未合并CONCEPT/概念等同义、中英文或拼写变体；一个实体可有多个类型。','','本轮30个评测样本：','','|实体|提交类型|裁判标签|','|---|---|---|']
for e in sample:lines.append('|'+ '|'.join([escape(e['name']),escape('、'.join(e['types'])),e['judgment']['label']])+'|')
lines+=['','全部类型频次：','','|类型标签|包含此标签的实体数|实体示例|','|---|---:|---|']
for t,n in freq.most_common():lines.append('|'+ '|'.join([escape(t),str(n),escape('；'.join(examples[t]))])+'|')
(out/'GRAPHRAG_ENTITY_TYPES.md').write_text('\n'.join(lines)+'\n');(out/'graphrag-entity-types.json').write_text(json.dumps({'nodes':len(es),'raw_label_count':len(freq),'type_frequencies':dict(freq.most_common()),'sample':sample},ensure_ascii=False,indent=2)+'\n');print('Saved full type inventory and 30-sample table.');print('CONCEPT share:',round(freq['CONCEPT']/len(es)*100,2))
