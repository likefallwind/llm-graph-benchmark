from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from collections import Counter,defaultdict
import sys,json,hashlib,time,fcntl,os,subprocess,shlex,copy,re
import transport,judge_tasks,granularity

def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,v):transport.write(p,v)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(response,metric):
 if metric=='granularity':
  response=copy.deepcopy(response);raw=response['choices'][0]['message']['content'].strip();response['choices'][0]['message']['content']=re.sub(r'^```(?:json)?\s*|\s*```$','',raw);return granularity.parse(response)
 return judge_tasks.parse_verdict(response['choices'][0]['message']['content'])

def report(run):
 tasks=rd(run/'tasks.json');key=rd(run/'private-key.json');groups=defaultdict(Counter); done=0
 for t in tasks:
  f=run/'results'/(t['id']+'.json');v=rd(f) if f.exists() else {'status':'pending'};g=groups[(key[t['id']]['system'],t['metric'])];g['total']+=1
  if v['status']=='done':g[v['value']['label']]+=1;done+=1
  else:g[v['status']]+=1
 for v in rd(run/'preserved-ours.json'):groups[('ours',v['metric'])][v['label']]+=1;groups[('ours',v['metric'])]['total']+=1
 usage=transport.usage_summary(run/'api',run/'request-slots');s={'complete':done==len(tasks),'done':done,'total':len(tasks),'updated_at':time.time(),'groups':{system:{m:dict(c) for (ss,m),c in groups.items() if ss==system} for system in ['ours','graphrag','autoschemakg','kggen']},'usage':usage};wr(run/'summary.json',s)
 names=['我们的方法（保留）','GraphRAG（修正）','AutoSchemaKG（修正）','KGGen（修正）'];systems=['ours','graphrag','autoschemakg','kggen']
 lines=['# 原通用裁判下的基线修正补测','','状态：'+('完成' if s['complete'] else '运行中或有技术缺失')+f'；已完成 {done}/{len(tasks)} 项（包含复用的粒度恢复）。MiniMax-M3；HTTP峰值并发 '+str(usage['peak_http'])+'。','','每格：通过/明确判定数（比例）；另附 pass/fail/uncertain/技术缺失或待评。未提供字段记N/A。我们的方法保留原M3判定，不重新评。','','|指标|'+'|'.join(names)+'|','|---|---:|---:|---:|---:|']
 metrics=[('entity_typing','实体类型'),('entity_definition_grounding','实体定义/描述'),('alias_identity','别名同一性'),('identity_split','实体拆分'),('book_qa','Book QA')]
 for m,title in metrics:
  cells=[]
  for sysname in systems:
   c=groups.get((sysname,m))
   if not c:cells.append('N/A');continue
   p,f,u=c['pass'],c['fail'],c['uncertain'];missing=c['total']-p-f-u;dec=p+f
   cells.append((f'{p}/{dec}（{p/dec:.1%}）' if dec else '暂无明确判定')+f'；{p}/{f}/{u}/{missing}')
  lines.append('|'+ '|'.join([title]+cells)+'|')
 lines+=['','原提示词和任务展示方式未改。主比例沿用历史排除uncertain的分母；全样本确认比例可由pass/total核对，完整计数见summary.json。未完成前不以临时分母比较排名。','','历史展示限制也保留：普通证据最多1200字符，身份拆分原脚本仅展示双方描述等信息、未传原文证据；QA每候选最多500字符并展示参考来源。因此这些是同一历史裁判口径的输出，不是新的独立准确率验证。没有添加案例规则或按方法排名调整提示。']
 gran=rd(run/'granularity-preserved.json');gran.update({t['id']:rd(run/'results'/(t['id']+'.json')) for t in tasks if t['metric']=='granularity' and (run/'results'/(t['id']+'.json')).exists()});gkey=rd(Path('/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-granularity-m3-c6-20260922T030615Z/private-key.json'));gc=defaultdict(Counter)
 for i,k in gkey.items():
  v=gran.get(i,{});gc[k['system']][v.get('value',{}).get('label','unassessed') if v.get('status')=='done' else 'unassessed']+=1
 lines+=['','## 原粒度任务恢复','','|粒度|'+'|'.join(names)+'|','|---|---:|---:|---:|---:|']
 for l in ['L1','L2','L3','uncertain','unassessed']:lines.append('|'+ '|'.join([l]+[str(gc[x][l])+'/200' for x in systems])+'|')
 lines+=['','完整断言800条、当前正确产物的实体及引用指标、48探针覆盖、图规模、million tokens构图消耗全部保留，见[原汇总](../d2l-metrics-comparison-20260922/ALL_METRICS.md)。']
 (run/'REPORT.md').write_text('\n'.join(lines)+'\n');wr(run/'granularity-summary.json',dict(gc));return s

def worker(run):
 manifest=rd(run/'manifest.json')
 for name,h in manifest['frozen_files'].items():
  if sha(run/name)!=h:raise ValueError('Frozen file changed: '+name)
 client=transport.Client(run/'api',run/'request-slots');tasks=rd(run/'tasks.json');terminal=False
 def one(t):
  r={'task_id':t['id'],'metric':t['metric'],'started_at':time.time()}
  try:
   response=client.complete(t['messages'],max_tokens=t['max_tokens'],validator=lambda x:parse(x,t['metric']));r.update(status='done',value=parse(response,t['metric']))
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
