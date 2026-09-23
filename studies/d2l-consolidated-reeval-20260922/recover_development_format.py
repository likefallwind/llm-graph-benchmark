from pathlib import Path
import sys,json,shutil,hashlib,time
r=Path('/home/likefallwind/code/llm-graph-benchmark');study=r/'studies/d2l-consolidated-reeval-20260922';src=r/'outputs/d2l-consolidated-m3-c6-20260922-v2';dst=r/'outputs/d2l-consolidated-m3-c6-20260922-v3';sys.path.insert(0,str(study));import evaluate as ev
assert (src/'.check.exit').read_text().strip()=='2' and not dst.exists()
shutil.copytree(src,dst,ignore=shutil.ignore_patterns('.check.*','check-launch.json','check.log','request-slots','.run.lock','progress.json','development-report.json','summary.json','REPORT.md'))
shutil.copy2(study/'evaluate.py',dst/'evaluate.py')
records={};attempts={}
for q in (src/'api/requests').glob('*/request.json'):
 req=ev.rd(q);msgkey=json.dumps(req['messages'],ensure_ascii=False,sort_keys=True)
 for f in q.parent.glob('attempt-*.json'):
  a=ev.rd(f);attempts.setdefault(msgkey,[]).append((a.get('request_started_at',a.get('started_at',0)),f,a))
for t in ev.rd(dst/'development.json'):
 f=dst/'results'/(t['id']+'.json')
 if not f.exists() or ev.rd(f)['status']=='done':continue
 archive=dst/'prior-development-failures'/f.name;archive.parent.mkdir(exist_ok=True);f.replace(archive)
 if t['metric'] in ['assertion_evidence','granularity']:continue
 msgkey=json.dumps(ev.messages(t),ensure_ascii=False,sort_keys=True)
 for _,origin,a in sorted(attempts.get(msgkey,[]),key=lambda x:x[0]):
  try:
   raw=json.loads(a['raw_body']);ev.transport.validate_response(raw);value=ev.parse(raw,t)
  except Exception:continue
  ev.wr(f,{'task_id':t['id'],'metric':t['metric'],'status':'done','value':value,'finished_at':time.time(),'recovered_from':str(origin),'source_sha256':ev.sha(origin),'policy':'earliest syntactically valid response under format-only normalization; no expected-label filtering'})
  records[t['id']]={'source':str(origin),'sha256':ev.sha(origin),'label':value['label']};break
manifest=ev.rd(src/'manifest.json');manifest['protocol']='consolidated-reeval-v3-format';ev.wr(dst/'development-recovery.json',{'parent_run':str(src),'format_only':['strip JSON markdown fences','decode target_copy JSON string only when exact object matches'],'records':records,'existing_semantic_labels_preserved':True})
protocol=(dst/'PROTOCOL.md').read_text()+'\n格式修正v3：只剥离JSON代码围栏；target_copy若为JSON编码字符串，仅在严格JSON解码后与原target对象完全相同才接受。自由改写/省字段仍拒绝。v2开发失败保留；离线按时间顺序选择最早可解析响应，不按预期标签筛选。\n';(dst/'PROTOCOL.md').write_text(protocol);(study/'PROTOCOL.md').write_text(protocol)
shutil.copy2(Path(__file__),dst/'recover_development_format.py')
manifest['frozen_files']={str(f.relative_to(dst)):ev.sha(f) for f in dst.rglob('*') if f.is_file() and f.name!='manifest.json' and not any(part in {'api','results','granularity-preserved','prior-granularity-failures','prior-development-failures'} for part in f.relative_to(dst).parts)}
ev.wr(dst/'manifest.json',manifest)
missing=[];mismatch=[]
for t in ev.rd(dst/'development.json'):
 f=dst/'results'/(t['id']+'.json')
 if not f.exists():missing.append(t['id'])
 elif ev.rd(f).get('value',{}).get('label')!=t['expected']:mismatch.append((t['id'],t['expected'],ev.rd(f).get('value',{}).get('label')))
print(json.dumps({'run':str(dst),'locally_recovered':len(records),'pending':missing,'semantic_mismatches':mismatch},ensure_ascii=False))
