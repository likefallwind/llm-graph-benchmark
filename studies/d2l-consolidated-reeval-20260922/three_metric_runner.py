from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from collections import Counter,defaultdict
import sys,json,hashlib,time,fcntl,os,subprocess,shlex,copy,re
import transport

def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,v):transport.write(p,v)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(response,t):
 raw=response['choices'][0]['message']['content'].strip()
 if raw.startswith('```') and raw.endswith('```'):
  raw=raw.split('\n',1)[1].rsplit('```',1)[0].strip()
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
 (run/'REPORT.md').write_text('\n'.join(lines)+'\n');return s

def worker(run):
 manifest=rd(run/'manifest.json')
 for name,h in manifest['frozen_files'].items():
  if sha(run/name)!=h:raise ValueError('Frozen file changed: '+name)
 client=transport.Client(run/'api',run/'request-slots');tasks=rd(run/'tasks.json');terminal=False
 def one(t):
  r={'task_id':t['id'],'metric':t['metric'],'started_at':time.time()}
  try:
   if t.get('oversized'):
    r.update(status='unassessed_size');wr(run/'results'/(t['id']+'.json'),r);return r
   response=client.complete(t['messages'],max_tokens=t['max_tokens'],validator=lambda x:parse(x,t));r.update(status='done',value=parse(response,t))
  except transport.TerminalProviderError:r.update(status='terminal_provider_error')
  except transport.ContentRejected:r.update(status='skipped_input_moderation')
  except Exception as e:r.update(status='failed',error_type=type(e).__name__)
  r['finished_at']=time.time();wr(run/'results'/(t['id']+'.json'),r);return r
 for rpass in range(2):
  pending=[]
  for t in tasks:
   f=run/'results'/(t['id']+'.json')
   if not f.exists():pending.append(t)
   elif rpass and rd(f)['status']=='failed':
    dest=run/'technical-retries'/str(rpass)/f.name;dest.parent.mkdir(parents=True,exist_ok=True);f.rename(dest);pending.append(t)
  if not pending or terminal:break
  q=iter(pending)
  with ThreadPoolExecutor(max_workers=6) as pool:
   futures={}
   def fill():
    while len(futures)<6 and not terminal:
     t=next(q,None)
     if t is None:break
     futures[pool.submit(one,t)]=t['id']
   fill();count=0
   while futures:
    finished,_=wait(futures,return_when=FIRST_COMPLETED)
    for f in finished:
     futures.pop(f);r=f.result();terminal|=r['status']=='terminal_provider_error';count+=1
     wr(run/'progress.json',{'pass':rpass,'processed':count,'pending_at_pass_start':len(pending),'status':r['status'],'updated_at':time.time()});print(rpass,count,len(pending),r['status'],flush=True)
    if count%6==0:report(run)
    fill()
  report(run)
 return 0 if report(run)['complete'] else 3

def main():
 run=Path(__file__).parent;action=sys.argv[1]
 if action=='report':report(run);return 0
 if action=='launch':
  transport.load_secret()
  if (run/'launch.json').exists():raise RuntimeError('Already launched')
  name=run.name;env={k:os.environ[k] for k in ['HOME','PATH','LANG','LC_ALL','MINIMAX_API_KEY'] if k in os.environ};env.update(PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
  cmd=shlex.join([sys.executable,str(run/'runner.py'),'worker']);subprocess.run(['tmux','-L',name,'-f','/dev/null','new-session','-d','-s',name,'-c',str(run),cmd],env=env,check=True)
  info={'run':str(run),'started_at':time.time(),'model':'MiniMax-M3','max_concurrency':6};wr(run/'launch.json',info);print(json.dumps(info));return 0
 with (run/'.run.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  code=1
  with (run/'run.log').open('a',buffering=1) as log:
   sys.stdout=log;sys.stderr=log
   try:code=worker(run)
   finally:
    (run/'.exit').write_text(str(code)+'\n')
    if code==0:(run/'.finished').write_text(str(time.time())+'\n')
 return code
if __name__=='__main__':sys.exit(main())
