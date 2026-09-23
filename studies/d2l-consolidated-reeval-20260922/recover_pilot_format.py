from pathlib import Path
import sys,json,shutil,time,collections
r=Path('/home/likefallwind/code/llm-graph-benchmark');study=r/'studies/d2l-consolidated-reeval-20260922';src=r/'outputs/d2l-consolidated-m3-c6-20260922-v4';dst=r/'outputs/d2l-consolidated-m3-c6-20260922-v5';sys.path.insert(0,str(study));import evaluate as e
assert (src/'.pilot.exit').read_text().strip()=='3' and not dst.exists()
shutil.copytree(src,dst,ignore=shutil.ignore_patterns('.check.*','.pilot.*','check-launch.json','pilot-launch.json','check.log','pilot.log','request-slots','.run.lock','progress.json','development-report.json','summary.json','REPORT.md'))
shutil.copy2(study/'evaluate.py',dst/'evaluate.py');requests={};recovered={};preserved={}
for q in (src/'api/requests').glob('*/request.json'):
 req=e.rd(q);k=json.dumps(req['messages'],ensure_ascii=False,sort_keys=True)
 for f in q.parent.glob('attempt-*.json'):
  a=e.rd(f);requests.setdefault(k,[]).append((a.get('request_started_at',a.get('started_at',0)),f,a))
for t in e.rd(dst/'pilot.json'):
 f=dst/'results'/(t['id']+'.json');v=e.rd(f)
 if v['status']=='done':preserved[f.name]=e.sha(f);continue
 assert v['status']=='failed';archive=dst/'prior-pilot-failures'/f.name;archive.parent.mkdir(exist_ok=True);f.replace(archive)
 if t['metric']=='assertion_evidence':continue
 msgs=e.granularity.messages(t['original_task'],e.granularity.PROMPT) if t['metric']=='granularity' else e.messages(t)
 for _,origin,a in sorted(requests.get(json.dumps(msgs,ensure_ascii=False,sort_keys=True),[]),key=lambda x:x[0]):
  try:
   raw=json.loads(a['raw_body']);e.transport.validate_response(raw);value=e.parse_granularity(raw) if t['metric']=='granularity' else e.parse(raw,t)
  except Exception:continue
  e.wr(f,{'task_id':t['id'],'metric':t['metric'],'status':'done','value':value,'finished_at':time.time(),'recovered_from':str(origin),'source_sha256':e.sha(origin),'policy':'Earliest valid response under explicit echo-format validation; no semantic-label selection'})
  recovered[t['id']]={'source':str(origin),'sha256':e.sha(origin),'label':value['label'],'verified_target_fields':value.get('verified_target_fields')};break
policy='''\n输出格式v5：保留原始回显值；单字段实体目标可接受与name逐字相同的字符串。QA的评分命题是固定参考答案各segment，允许与reference_answer逐字相同的字符串回显，并明确记录仅验证了reference_answer（不伪称回显了question）；原问题始终保留在请求中。带question的对象若改写问题仍拒绝。允许target对象附带与输入完全相同的segments副本。内容、否定或目标实体的改写仍拒绝。粒度仅剥离JSON围栏，标签规则不变。新规则只改变技术可解析性，原有效判定全部保留，原失败和原始响应保留，按最早有效响应离线恢复。\n'''
(dst/'PROTOCOL.md').write_text((dst/'PROTOCOL.md').read_text()+policy);e.wr(dst/'pilot-format-recovery.json',{'parent_run':str(src),'records':recovered,'preserved_valid_results_sha256':preserved,'semantic_prompt_unchanged':True,'task_inputs_unchanged':e.sha(dst/'tasks.json')==e.sha(src/'tasks.json'),'normalization_policy':policy})
shutil.copy2(Path(__file__),dst/'recover_pilot_format.py');m=e.rd(src/'manifest.json');m['protocol']='consolidated-reeval-v5-format';m['frozen_files']={str(f.relative_to(dst)):e.sha(f) for f in dst.rglob('*') if f.is_file() and f.name!='manifest.json' and not any(part in {'api','results','ledgers','source-shards','granularity-preserved','prior-granularity-failures','prior-development-failures','prior-pilot-failures','technical-retries'} for part in f.relative_to(dst).parts)};e.wr(dst/'manifest.json',m)
missing=[t['id'] for t in e.rd(dst/'pilot.json') if not (dst/'results'/(t['id']+'.json')).exists()];print(json.dumps({'run':str(dst),'preserved_pilot':len(preserved),'recovered':len(recovered),'pending':missing},ensure_ascii=False))
