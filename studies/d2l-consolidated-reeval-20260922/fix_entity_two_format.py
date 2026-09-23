from pathlib import Path
import json,hashlib,shutil,sys,time
p=Path("/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-entity-two-metrics-m3-c6-20260922")
f=p/"runner.py";original=f.read_text();(p/"format-fix").mkdir(exist_ok=True);(p/"format-fix/runner-before.py").write_text(original)
old='v=json.loads(raw);typing=t["metric"]=="entity_typing";rows=v.get("items" if typing else "claims")'
new='''try:v=json.loads(raw)
 except json.JSONDecodeError:
  # Escape only unescaped interior quotation marks; do not alter semantic fields.
  chars=[];inside=False;escape=False
  for i,ch in enumerate(raw):
   if escape:chars.append(ch);escape=False;continue
   if ch==chr(92) and inside:chars.append(ch);escape=True;continue
   if ch==chr(34):
    if not inside:inside=True
    else:
     tail=raw[i+1:].lstrip()
     if not tail or tail[0] in ":,}]":inside=False
     else:chars.append(chr(92))
   chars.append(ch)
  v=json.loads("".join(chars))
 typing=t["metric"]=="entity_typing"
 if isinstance(v,list):v={"items" if typing else "claims":v}
 rows=v.get("items" if typing else "claims")'''
assert old in original
f.write_text(original.replace(old,new))
sys.path.insert(0,str(p));import runner,transport
tasks=json.loads((p/"tasks.json").read_text());taskmap={transport.digest({"model":"MiniMax-M3","messages":t["messages"],"temperature":0.0,"max_tokens":t["max_tokens"],"stream":False}):t for t in tasks}
candidates={}
for ap in (p/"api/requests").glob("*/attempt-*.json"):
 a=json.loads(ap.read_text());t=taskmap.get(a["payload_sha256"])
 if not t or a.get("http_status")!=200:continue
 try:
  response=json.loads(a["raw_body"]);transport.validate_response(response);v=runner.parse(response,t)
 except Exception:continue
 candidates.setdefault(t["id"],[]).append((a["started_at"],ap,v,response,a["payload_sha256"]))
for tid,values in candidates.items():
 _,ap,v,response,fp=min(values,key=lambda x:x[0]);dest=p/"results"/(tid+".json")
 if dest.exists():shutil.copy2(dest,p/"format-fix"/dest.name)
 transport.write(dest,{"task_id":tid,"status":"done","value":v,"recovered_from":str(ap.relative_to(p)),"format_only":True,"finished_at":time.time()})
 transport.write(p/"api/response-cache"/(fp+".json"),response)
for dest in (p/"results").glob("*.json"):
 if json.loads(dest.read_text()).get("status")!="done":dest.rename(p/"format-fix"/("failed-"+dest.name))
manifest=json.loads((p/"manifest.json").read_text());manifest["frozen_files"]["runner.py"]=hashlib.sha256(f.read_bytes()).hexdigest();transport.write(p/"manifest.json",manifest)
transport.write(p/"format-fix/README.json",{"change":"Accept equivalent outer list and escape interior quotes only; earliest structurally valid response per task; no prompt or label edits","recovered":len(candidates)})
print({"recovered":len(candidates),"pending":150-len(candidates)})
runner.report(p)

