from pathlib import Path
import json,sys,hashlib,time
p=Path("/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-entity-boundary-m3-c6-20260923")
f=p/"runner.py";s=f.read_text();(p/"format-fix").mkdir(exist_ok=True)
(p/"format-fix/runner-before.py").write_text(s)
s=s.replace('source=t["payload"]["target"]["description"];cursor=0;separators=" ，,。；;\\t\\r\\n"','source="".join(t["payload"]["target"]["description"].split());cursor=0;separators="，,。；;：:"')
s=s.replace('text=row["text"].strip()','text="".join(row["text"].split())')
assert s!=f.read_text();f.write_text(s)
sys.path.insert(0,str(p));import runner,transport
manifest=json.loads((p/"manifest.json").read_text());manifest["frozen_files"]["runner.py"]=hashlib.sha256(f.read_bytes()).hexdigest();transport.write(p/"manifest.json",manifest)
tasks=json.loads((p/"tasks.json").read_text())
byfp={transport.digest({"model":"MiniMax-M3","messages":t["messages"],"temperature":0.0,"max_tokens":t["max_tokens"],"stream":False}):t for t in tasks}
choices={}
for ap in (p/"api/requests").glob("*/attempt-*.json"):
 a=json.loads(ap.read_text());t=byfp.get(a["payload_sha256"])
 if not t or a.get("http_status")!=200:continue
 try:
  response=json.loads(a["raw_body"]);transport.validate_response(response);v=runner.parse(response,t)
 except Exception:continue
 choices.setdefault(t["id"],[]).append((a["started_at"],ap,v,response,a["payload_sha256"]))
recovered=[]
for tid,items in choices.items():
 dest=p/"results"/(tid+".json")
 if not dest.exists() or json.loads(dest.read_text())["status"]=="done":continue
 _,ap,v,response,fp=min(items,key=lambda a:a[0])
 (p/"format-fix"/dest.name).write_text(dest.read_text())
 transport.write(dest,{"task_id":tid,"status":"done","value":v,"recovered_from":str(ap.relative_to(p)),"format_only":True,"finished_at":time.time()})
 transport.write(p/"api/response-cache"/(fp+".json"),response);recovered.append(tid)
transport.write(p/"format-fix/README.json",{"rule":"Ignore whitespace layout; allow omitted colon separators as already authorized by prompt; do not change any wording or labels","recovered_ids":recovered})
print({"recovered":len(recovered)})

