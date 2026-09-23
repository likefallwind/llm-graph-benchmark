from pathlib import Path
R=Path('/home/likefallwind/code/llm-graph-benchmark');H=R/'studies/d2l-consolidated-reeval-20260922';s=(R/'outputs/d2l-baseline-original-rubric-m3-c6-20260922/runner.py').read_text(encoding='utf-8-sig');s=s.replace('import transport,judge_tasks,granularity','import transport')
a=s.index('def parse(');b=s.index('\ndef worker(',a)
s=s[:a]+'''def parse(response,t):
 raw=response['choices'][0]['message']['content'].strip()
 if raw.startswith('```') and raw.endswith('```'):
  raw=raw.split('\\n',1)[1].rsplit('```',1)[0].strip()
 v=json.loads(raw)
 if not isinstance(v,dict) or v.get('label') not in {'pass','fail','uncertain'}:raise ValueError('label')
 if not isinstance(v.get('reason'),str) or not v['reason'].strip():raise ValueError('reason')
 ids={x['id'] for x in t['payload']['evidence']};refs=v.get('evidence_ids')
 if not isinstance(refs,list) or any(not isinstance(x,str) or x not in ids for x in refs):raise ValueError('evidence ids')
 if v['label']=='pass' and not refs:raise ValueError('support reference required')
 return v

def report(run):
 tasks=rd(run/'tasks.json');key=rd(run/'private-key.json');old=rd(run/'previous-labels.json');groups=defaultdict(Counter);done=0;transitions=defaultdict(Counter);changes=[]
 for t in tasks:
  f=run/'results'/(t['id']+'.json');v=rd(f) if f.exists() else {'status':'pending'};sysname=key[t['id']]['system'];g=groups[(sysname,t['metric'])];g['total']+=1
  if v['status']=='done':
   l=v['value']['label'];g[l]+=1;done+=1;ov=old[t['id']];ol=ov.get('label') or {'yes':'pass','no':'fail','uncertain':'uncertain'}.get(ov.get('covered'))
   transitions[(sysname,t['metric'])][str(ol)+' -> '+l]+=1
   if ol!=l:changes.append({'id':t['id'],'system':sysname,'metric':t['metric'],'previous':ov,'current':v['value']})
  else:g[v['status']]+=1
 usage=transport.usage_summary(run/'api',run/'request-slots');s={'complete':done==len(tasks),'done':done,'total':len(tasks),'updated_at':time.time(),'groups':{sysname:{m:dict(c) for (ss,m),c in groups.items() if ss==sysname} for sysname in ['ours','graphrag','autoschemakg','kggen']},'usage':usage,'transitions':{ss+':'+m:dict(c) for (ss,m),c in transitions.items()}};wr(run/'summary.json',s);wr(run/'changed-judgments.json',changes)
 names=['我们的方法','GraphRAG','AutoSchemaKG','KGGen'];systems=['ours','graphrag','autoschemakg','kggen'];metrics=[('entity_typing','实体类型兼容正确率'),('entity_definition_grounding','实体描述完整支持率'),('fact_recovery','48探针完整事实覆盖')]
 lines=['# 三项修复后的统一重评','','状态：'+('已完成' if s['complete'] else '未完成')+f'；{done}/{len(tasks)} 项。MiniMax-M3；峰值并发 '+str(usage['peak_http'])+'。','','主表为通过/全部固定样本，不排除不确定或技术缺失。N/A表示没有原生可评字段。','','|指标|'+'|'.join(names)+'|','|---|---:|---:|---:|---:|']
 for m,title in metrics:
  cells=[]
  for sysname in systems:
   c=groups.get((sysname,m));cells.append(f"{c['pass']}/{c['total']}（{c['pass']/c['total']:.1%}）" if c else 'N/A')
  lines.append('|'+ '|'.join([title]+cells)+'|')
 lines+=['','类型只检查类型，描述只检查描述，输入均包含全部原引用。覆盖只看完整图候选是否支持源事实的所有实质内容和必要条件；目标事实不能为候选补信息。样本与Top10候选均保持原样。','','|方法|指标|通过|不通过|不确定|缺失/待评|通过/明确判定|','|---|---|---:|---:|---:|---:|---:|']
 for sysname,name in zip(systems,names):
  for m,title in metrics:
   c=groups.get((sysname,m))
   if not c:continue
   p,f,u=c['pass'],c['fail'],c['uncertain'];n=p+f;rate=f'{p}/{n}（{p/n:.1%}）' if n else 'N/A';lines.append('|'+ '|'.join(map(str,[name,title,p,f,u,c['total']-p-f-u,rate]))+'|')
 lines+=['','新完整覆盖与旧宽口径核心覆盖含义不同，不能把分数变化直接归因于方法变化。类型仍衡量原生标签兼容性，不衡量粒度或类型完整性；各图样本并非配对事实。模型标签未经独立人工校准。全部历史标签、变更原因和原始响应保留；本轮不按分数调整提示或重试。']
 (run/'REPORT.md').write_text('\\n'.join(lines)+'\\n');return s
''' + s[b:]
s=s.replace("parse(x,t['metric'])","parse(x,t)").replace("parse(response,t['metric'])","parse(response,t)")
s=s.replace("  try:\n   response=client.complete", "  try:\n   if t.get('oversized'):\n    r.update(status='unassessed_size');wr(run/'results'/(t['id']+'.json'),r);return r\n   response=client.complete")
assert 'judge_tasks' not in s and 'granularity' not in s
(H/'three_metric_runner.py').write_text(s)
compile(s,'three_metric_runner.py','exec');print('runner prepared')
