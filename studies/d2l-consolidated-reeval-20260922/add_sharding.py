from pathlib import Path
p=Path('/home/likefallwind/code/llm-graph-benchmark/studies/d2l-consolidated-reeval-20260922/evaluate.py');s=p.read_text(encoding='utf-8-sig')
helper='''
def generic_judgment(client,t,run):
 if not t.get('requires_source_shards'):
  response=client.complete(messages(t),max_tokens=12288,validator=lambda a:parse(a,t));return parse(response,t)
 # Keep every source unit. Each shard is a local evidence scan, not a final semantic vote.
 sources=t['payload']['sources'];base=copy.deepcopy(t);base['payload']['sources']=[]
 base_size=len(json.dumps(base,ensure_ascii=False).encode());budget=300000-base_size
 if budget<10000:raise ValueError('Target too large for evidence sharding')
 shards=[];current=[];size=0
 for row in sources:
  n=len(json.dumps(row,ensure_ascii=False).encode())+2
  if n>budget:raise ValueError('Single source unit exceeds shard budget')
  if current and size+n>budget:shards.append(current);current=[];size=0
  current.append(row);size+=n
 if current:shards.append(current)
 selected=set();records=[]
 for i,rows in enumerate(shards):
  local=copy.deepcopy(base);local['payload']['sources']=rows
  local['payload']['candidate_context']['evidence_scan_note']='这是完整证据的一部分，仅判断本段能证明什么；缺少支持时如实记录，不假定其他分段内容。'
  f=run/'source-shards'/t['id']/(str(i)+'.json');input_hash=hashlib.sha256(json.dumps(local,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  if f.exists():
   saved=rd(f)
   if saved['input_sha256']!=input_hash:raise ValueError('Shard changed')
   value=saved['value']
  else:
   response=client.complete(messages(local),max_tokens=12288,validator=lambda a:parse(a,local));value=parse(response,local);wr(f,{'input_sha256':input_hash,'source_ids':[x['id'] for x in rows],'value':value})
  selected.update(x for item in value['items'] for x in item['evidence']);records.append(str(f.relative_to(run)))
 final=copy.deepcopy(base);final['payload']['sources']=[x for x in sources if x['id'] in selected]
 final['payload']['candidate_context']['evidence_scan_note']='原引用已逐段完整扫描。这里是各段选出的真实原文证据集合，含支持、反证与相关但不足的证据；不得把有证据条目当作支持结论，仍需核对目标。'
 if len(json.dumps(final,ensure_ascii=False).encode())>350000:raise ValueError('Selected evidence exceeds reduction budget')
 response=client.complete(messages(final),max_tokens=12288,validator=lambda a:parse(a,final));value=parse(response,final)
 value['source_sharding']={'source_units_scanned':len(sources),'shards':len(shards),'selected_source_units':len(final['payload']['sources']),'audit_records':records,'limitation':'Final review uses source units selected by all shard scans; evidence selection is model-dependent.'}
 return value

'''
s=s.replace('\ndef assertion_value(v):','\n'+helper+'def assertion_value(v):')
s=s.replace("response=client.complete(messages(t),max_tokens=12288,validator=lambda a:parse(a,t));r.update(status='done',value=parse(response,t))","r.update(status='done',value=generic_judgment(client,t,run))")
p.write_text(s)
