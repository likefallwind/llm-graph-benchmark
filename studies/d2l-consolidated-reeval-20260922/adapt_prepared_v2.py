from pathlib import Path
import json,shutil,hashlib,random,collections
r=Path('/home/likefallwind/code/llm-graph-benchmark');study=r/'studies/d2l-consolidated-reeval-20260922';src=r/'outputs/d2l-consolidated-m3-c6-20260922-v1';dst=r/'outputs/d2l-consolidated-m3-c6-20260922-v2'
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not dst.exists();assert not (src/'api').exists();shutil.copytree(src,dst)
meta=rd(src/'manifest.json');oldkey=rd(src/'private-key.json');oldtasks=rd(src/'tasks.json');audit=rd(r/'outputs/d2l-metrics-comparison-20260922/field-availability-audit.json')['submissions'];em={s:{e['id']:e for d in rd(Path(a['path']))['documents'] for e in d['entities']} for s,a in audit.items()}
us=json.loads((r/'outputs/d2l-full1105-vnext-20260826/documents.jsonl').read_text().splitlines()[0])['units'];pos={u['unit_id']:i for i,u in enumerate(us)};newkey={};mapping={};tasks=[]
for t in oldtasks:
 oldid=t['id'];k=oldkey[oldid]
 if t['metric'] in ['identity_split','alias_identity']:
  s=k['system'];item=k['item_id'];ids=item.split(':split:') if t['metric']=='identity_split' else [item.split(':alias:')[0]];refs={v['unit_id'] for i in ids for v in em[s][i].get('evidence',[])}
  selected=sorted({j for ref in refs for j in range(max(0,pos[ref]-1),min(len(us),pos[ref]+2))});t['payload']['sources']=[{'id':us[j]['unit_id'],'text':us[j]['text']} for j in selected]
  if t['metric']=='identity_split':
   for role in ['left','right']:t['payload']['candidate_context'][role+'_source_ids']=t['payload']['target'][role].pop('source_ids')
  t['requires_source_shards']=len(json.dumps(t,ensure_ascii=False).encode())>350000;t['oversized']=False
  t.pop('id');newid='r_'+hashlib.sha256(json.dumps([20260922,s,item,k['doc_id'],t],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:28];t['id']=newid
 else:newid=oldid
 newkey[newid]=k;mapping[oldid]=newid;tasks.append(t)
assert len(tasks)==2789 and not any(t['oversized'] for t in tasks)
pilot=[]
for s in audit:
 for m in sorted({t['metric'] for t in tasks if newkey[t['id']]['system']==s}):
  candidates=sorted([t for t in tasks if newkey[t['id']]['system']==s and t['metric']==m],key=lambda t:t['id']);pilot+=random.Random('pilot:'+s+':'+m).sample(candidates,min(2,len(candidates)))
# Exercise one long-source case as part of the pilot rather than hiding it until the full run.
long=sorted([t for t in tasks if t.get('requires_source_shards')],key=lambda t:t['id'])
if long and long[0]['id'] not in {t['id'] for t in pilot}:pilot.append(long[0])
wr(dst/'tasks.json',tasks);wr(dst/'private-key.json',newkey);wr(dst/'pilot.json',pilot)
for n in ['evaluate.py','driver.py','finalize.py']:shutil.copy2(study/n,dst/n)
protocol=(study/'PROTOCOL.md').read_text(encoding='utf-8-sig').replace('重评 v1','重评 v2').replace('实体正确性、类型、定义和身份用所引原文所属完整三级或更上级节上下文；','实体正确性、类型和定义用所引原文所属完整三级或更上级节上下文；身份使用全部原引用及每引用前后各一单元（全方法统一），不因通用节点涉及全书而把每一引用扩成整章；')
protocol+='\n身份任务超过350000 UTF8字节时，每个原文单元原样进入不超过300000字节的分段输入；每段扫描目标证据，最终裁判用所有分段选出的真实证据再核验目标。选择过程仍有模型偏差，全部分段输入、判断和选中证据留审计。源引用ID放candidate_context而非要求逐字复制的实体名称target，不改变实体或别名内容。\n'
(study/'PROTOCOL.md').write_text(protocol);(dst/'PROTOCOL.md').write_text(protocol);shutil.copy2(Path(__file__),dst/'adapt_prepared_v2.py')
wr(dst/'preparation-lineage.json',{'parent_prepared_run':str(src),'parent_tasks_sha256':sha(src/'tasks.json'),'API_calls_before_revision':0,'identity_policy':'all cited units plus one adjacent unit each side, uniformly for all methods; large evidence scans preserve every source unit','id_map':mapping,'sharded_ids':[t['id'] for t in long],'other_tasks_unchanged':sum(t['metric'] not in ['identity_split','alias_identity'] for t in tasks)})
meta.update(protocol='consolidated-reeval-v2',oversized=0,source_sharded_tasks=len(long),preparation='v1 prepare.py plus frozen adapt_prepared_v2.py, no API before revision')
meta['input_hashes'][str(r/'src/llm_graph_benchmark/retrieval.py')]=sha(r/'src/llm_graph_benchmark/retrieval.py');meta['input_hashes'][str(r/'src/llm_graph_benchmark/identity.py')]=sha(r/'src/llm_graph_benchmark/identity.py')
meta['frozen_files']={str(f.relative_to(dst)):sha(f) for f in dst.rglob('*') if f.is_file() and f.name!='manifest.json' and 'granularity-preserved' not in str(f) and 'prior-granularity-failures' not in str(f)}
wr(dst/'manifest.json',meta)
print(json.dumps({'run':str(dst),'tasks':len(tasks),'pilot':len(pilot),'sharded':len(long),'oversized':0,'sharded_by_system':dict(collections.Counter(newkey[t['id']]['system'] for t in long))}))
