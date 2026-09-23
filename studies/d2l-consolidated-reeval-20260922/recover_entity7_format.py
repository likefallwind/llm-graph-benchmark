from pathlib import Path
import json,re,hashlib,time
p=Path('/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-entity-missing7-m3-c6-20260922')
for j in json.loads((p/'jobs.json').read_text()):
 f=p/'results'/f'{j["id"]}-{j["dimension"]}.json';prior=json.loads(f.read_text())
 if prior['status']=='done':continue
 candidates=[]
 for request in (p/'api/requests').glob('*/request.json'):
  if json.loads(request.read_text())['messages']!=j['messages']:continue
  for a in request.parent.glob('attempt-*.json'):
   v=json.loads(a.read_text());b=json.loads(v.get('raw_body','{}'));c=b.get('choices',[{}])[0];raw=c.get('message',{}).get('content','');m=re.fullmatch(r'(correct|incorrect|uncertain)\s*<reason>(.+)</reason>',raw.strip(),re.S)
   if m and j['dimension']=='correctness' and b.get('base_resp',{}).get('status_code')==0 and c.get('finish_reason')=='stop':candidates.append((v['started_at'],a,raw,m.group(1),m.group(2)))
 assert candidates
 _,a,raw,label,reason=min(candidates,key=lambda x:x[0]);archive=p/'prior-failures'/f.name;archive.parent.mkdir(exist_ok=True);f.rename(archive)
 result={**prior,'status':'done','value':{'label':label,'reason':reason.strip()},'format_repair':'Original valid label lacked only <label> wrapper; no semantic relabeling. Earliest eligible response used.','raw_content':raw,'recovered_from':str(a),'response_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'recovered_at':time.time()};f.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('Recovered one missing-label-tag response locally, no API call.')
