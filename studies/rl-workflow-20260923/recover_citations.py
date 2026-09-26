"""Repair benchmark citation rendering from frozen responses, without new API calls."""
from pathlib import Path
import importlib.util
import json
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("rl_pipeline", HERE/"run_pipeline.py")
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
jobs=p.read(p.OUT/"probe-jobs.json")
records=[]
for job in jobs:
 dest=p.GEN/"results"/(job["id"]+".json")
 old=p.read(dest)
 if old["status"]=="done":
  response=old["response"];value=p.parse(response,job);source=str(dest)
 else:
  candidates=[]
  for folder in (p.GEN/"api/requests").iterdir():
   request=p.read(folder/"request.json")
   task=json.loads(request["messages"][1]["content"])
   if task!=job:continue
   for f in folder.glob("attempt-*.json"):
    record=p.read(f)
    if record.get("http_status")!=200:continue
    try:
     raw=json.loads(record.get("raw_body","{}"))
     p.transport.validate_response(raw);v=p.parse(raw,job)
    except (ValueError,KeyError,TypeError):continue
    candidates.append((record["started_at"],f,raw,v))
  if not candidates:raise ValueError("No recoverable frozen response: "+job["id"])
  _,f,response,value=min(candidates,key=lambda x:x[0]);source=str(f)
 archive=p.GEN/"citation-rendering-original"/dest.name
 archive.parent.mkdir(exist_ok=True)
 if not archive.exists():shutil.copy2(dest,archive)
 p.transport.write(dest,{"id":job["id"],"input_hash":p.transport.digest({"job":job,"prompt":p.PROMPT}),
  "status":"done","value":value,"response":response,"citation_recovered_from":source})
 records.append({"id":job["id"],"previous_status":old["status"],"response_source":source,
                 "content_changed":False,"citation_policy":"Actual complete source units by verified IDs; generated quotations retained only as audit data"})
p.transport.write(p.GEN/"citation-recovery.json",{"new_api_calls":0,"records":records})
print(json.dumps({"done":len(records),"preserved_valid":sum(x["previous_status"]=="done" for x in records),
                  "recovered_without_api":sum(x["previous_status"]!="done" for x in records)}))

