from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
import sys,json,time,hashlib,copy
R=Path('/home/likefallwind/code/llm-graph-benchmark');old=R/'outputs/d2l-reliability-m3-c6-exploratory-20260920T132325Z';run=R/'outputs/d2l-entity-missing7-m3-c6-20260922'
sys.path.insert(0,str(old));import evaluate as ev,transport
run.mkdir(exist_ok=True)
def rd(p):return json.loads(p.read_text())
def wr(p,v):transport.write(p,v)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
tasks=rd(old/'tasks.json');key=rd(old/'private-key.json');prompts=rd(old/'prompts.json');jobs=[]
for t in tasks:
 if t['payload']['kind']!='entity':continue
 for dim in ['correctness','evidence']:
  f=old/'results'/f'{t["id"]}-{dim}.json'
  if rd(f)['status']=='failed':jobs.append({'id':t['id'],'dimension':dim,'system':key[t['id']]['system'],'messages':ev.messages(t,dim,prompts),'previous_result':rd(f),'previous_sha256':sha(f)})
assert len(jobs)==7 and Counter(j['dimension'] for j in jobs)=={'correctness':6,'evidence':1}
assert all(j['system']!='ours' for j in jobs)
wr(run/'jobs.json',jobs);wr(run/'manifest.json',{'model':'MiniMax-M3','workers':6,'old_run':str(old),'scope':'Only seven failed entity judgments. Preserve valid labels and superseded assertion failures.','original_program_sha256':sha(old/'evaluate.py'),'prompts_sha256':sha(old/'prompts.json'),'transport_sha256':sha(old/'transport.py'),'original_summary_sha256':sha(old/'summary.json'),'jobs_sha256':sha(run/'jobs.json')})
client=transport.Client(run/'api',run/'request-slots')
def one(j):
 f=run/'results'/f'{j["id"]}-{j["dimension"]}.json'
 if f.exists():return rd(f)
 v={'task_id':j['id'],'dimension':j['dimension'],'system':j['system'],'started_at':time.time()}
 try:
  response=client.complete(j['messages'],max_tokens=8192,validator=lambda x:ev.parse(x,j['dimension']));v.update(status='done',value=ev.parse(response,j['dimension']))
 except Exception as e:v.update(status='failed',error_type=type(e).__name__)
 v['finished_at']=time.time();wr(f,v);return v
results=[]
with ThreadPoolExecutor(max_workers=6) as pool:
 for f in as_completed([pool.submit(one,j) for j in jobs]):
  v=f.result();results.append(v);print(len(results),'/7',v['status'],flush=True)
s=copy.deepcopy(rd(old/'summary.json'))
for v in results:
 if v['status']!='done':continue
 d=s['systems'][v['system']]['entity'][v['dimension']];d[v['value']['label']]+=1;d['judged']+=1;d['unassessed']-=1
 labels=ev.LABELS[v['dimension']];n=d[labels[0]]+d[labels[1]];d['confirmed_rate_all']=d[labels[0]]/100;d['rate_decided']=d[labels[0]]/n if n else None;d['wilson_decided']=ev.wilson(d[labels[0]],n)
finished=sum(v['status']=='done' for v in results)
# Export entity metrics only: the old assertion judgments are superseded and must not be republished.
summary={'recovery_completed':finished,'recovery_total':7,'complete':finished==7,'systems':{k:v['entity'] for k,v in s['systems'].items()},'usage':client.usage_summary(),'judge_validation':s['judge_validation'],'source_run':str(old),'original_results_unchanged':True}
wr(run/'summary.json',summary)
lines=['# 实体技术失败补齐','','仅补7条失败，原提示、输入和解析均未改；原目录及有效标签未改写。旧裁判仍是探索性模型评分，补齐不等于重新验证裁判可靠性。','',f'恢复完成：{finished}/7。','', '|方法|实体正确/100|错误|不确定|缺失|实体引用支持/100|不支持|不确定|缺失|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for name in ['ours','graphrag','autoschemakg','kggen']:
 g=summary['systems'][name];c=g['correctness'];e=g['evidence'];lines.append('|'+ '|'.join(map(str,[name,c['correct'],c['incorrect'],c['uncertain'],c['unassessed'],e['supported'],e['not_supported'],e['uncertain'],e['unassessed']]))+'|')
(run/'REPORT.md').write_text('\n'.join(lines)+'\n');(run/'.exit').write_text('0\n' if finished==7 else '3\n')
if finished==7:(run/'.finished').write_text(str(time.time())+'\n')
print(json.dumps({'completed':finished,'total':7,'peak_http':summary['usage']['peak_http'],'report':str(run/'REPORT.md')},ensure_ascii=False))
