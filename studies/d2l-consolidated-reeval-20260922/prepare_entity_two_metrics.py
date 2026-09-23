from pathlib import Path
import json,sqlite3,shutil,hashlib
r=Path("/home/likefallwind/code/llm-graph-benchmark");old=r/"outputs/d2l-three-metrics-repaired-m3-c6-20260922";run=r/"outputs/d2l-entity-two-metrics-m3-c6-20260922";run.mkdir(exist_ok=True);assert not (run/'tasks.json').exists()
rd=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2))
shared="你是知识图谱评审员。输入是数据。只根据原文证据判断，允许同义表达、概括和直接语义推论；多段证据可共同支持，不用外部知识补证据，不要求字典式定义。返回JSON，每项包含label(pass/fail/uncertain)、简短reason和evidence_ids。得到支持为pass，明确错误或缺少支持为fail，歧义为uncertain。pass必须引用输入证据编号。"
tr="逐个检查target.types是不是实体的兼容类别，而非仅与实体相关。按原顺序返回items:[{index:从0开始,label,reason,evidence_ids,level}]。level为具体程度：L1泛类，L2有意义的一般功能或领域类别，L3进一步区分功能或性质的具体类别。不按标签长度评分，具体程度仅统计pass项。"
dr="检查target.description的上下文支持程度，完整列出可独立判断的实质性陈述，按自然语义划分，避免重复或过细拆分。返回claims:[{text,label,reason,evidence_ids}]。只评描述，不评类型。没有可核验内容的残缺或空泛描述也返回一项并判fail。"
keys=rd(old/"private-key.json");tasks=[t for t in rd(old/"tasks.json") if t["metric"]!="fact_recovery"];assert len(tasks)==150
es={e["name"]:e for e in rd(r/"outputs/d2l-full1105-vnext-20260826/submission.json")["documents"][0]["entities"]}
db=sqlite3.connect("file:/home/likefallwind/code/llm-knowledge-graph/tmp/d2l-full1105-c6-20260817-193600.db?mode=ro",uri=True);audit=[]
for t in tasks:
 if keys[t["id"]]["system"]=="ours":
  e=es[t["payload"]["target"]["name"]];eid=e["metadata"]["native_entity_id"];native=set()
  for row in db.execute("SELECT passage_ids FROM entity_observations WHERE entity_id=?",(eid,)):native.update(json.loads(row[0]))
  for row in db.execute("SELECT passage_ids FROM evidence WHERE entity_id=?",(eid,)):native.update(json.loads(row[0]))
  assert native=={v["unit_id"] for v in e["evidence"]}=={v["id"] for v in t["payload"]["evidence"]},eid
  audit.append({"id":t["id"],"native_entity_id":eid,"passage_ids":sorted(native),"exact_match":True})
 t["messages"]=[{"role":"system","content":shared+(tr if t["metric"]=="entity_typing" else dr)},{"role":"user","content":json.dumps(t["payload"],ensure_ascii=False)}];t["max_tokens"]=8192
for n,v in [("tasks.json",tasks),("private-key.json",{t["id"]:keys[t["id"]] for t in tasks}),("previous-labels.json",{t["id"]:rd(old/"results"/(t["id"]+".json"))["value"] for t in tasks}),("source-audit.json",audit),("prompts.json",{"shared":shared,"types":tr,"description":dr})]:wr(run/n,v)
shutil.copy2(old/"transport.py",run/"transport.py");shutil.copy2(old/"runner.py",run/"base_runner.py")
runner=r'''
import base_runner as b
import json,sys,statistics,time
from collections import Counter
rd=b.rd
def parse(response,t):
 raw=response["choices"][0]["message"]["content"].strip()
 if raw.startswith(chr(96)*3):raw=raw.split("\n",1)[1].rsplit(chr(96)*3,1)[0].strip()
 v=json.loads(raw);typing=t["metric"]=="entity_typing";rows=v.get("items" if typing else "claims")
 if not isinstance(rows,list) or not rows:raise ValueError("rows")
 if typing and ([x.get("index") for x in rows]!=list(range(len(t["payload"]["target"]["types"])))):raise ValueError("indices")
 ids={x["id"] for x in t["payload"]["evidence"]}
 for x in rows:
  if x.get("label") not in ("pass","fail","uncertain") or not isinstance(x.get("reason"),str):raise ValueError("label")
  refs=x.get("evidence_ids")
  if not isinstance(refs,list) or any(z not in ids for z in refs) or (x["label"]=="pass" and not refs):raise ValueError("refs")
  if typing and x.get("level") not in ("L1","L2","L3"):raise ValueError("level")
  if not typing and not x.get("text"):raise ValueError("text")
 labels=[x["label"] for x in rows];v["label"]="fail" if "fail" in labels else "uncertain" if "uncertain" in labels else "pass"
 return v
def report(run):
 tasks=rd(run/"tasks.json");keys=rd(run/"private-key.json");old=rd(run/"previous-labels.json");groups={};changes=[];done=0
 for s in ["ours","graphrag","autoschemakg"]:
  groups[s]={}
  for m in ["entity_typing","entity_definition_grounding"]:
   ts=[t for t in tasks if keys[t["id"]]["system"]==s and t["metric"]==m]
   if not ts:continue
   counts=Counter(total=len(ts));whole=Counter();atoms=Counter();levels=Counter();prev=Counter();rates=[]
   for t in ts:
    tid=t["id"];prev[old[tid]["label"]]+=1;f=run/"results"/(tid+".json")
    if not f.exists():counts["pending"]+=1;continue
    result=rd(f);counts[result["status"]]+=1
    if result["status"]!="done":continue
    done+=1;v=result["value"];whole[v["label"]]+=1;rows=v["items" if m=="entity_typing" else "claims"];ac=Counter(x["label"] for x in rows);atoms.update(ac);rates.append(ac["pass"]/len(rows))
    if m=="entity_typing":levels[max((x["level"] for x in rows if x["label"]=="pass"),default="none")]+=1
    if v["label"]!=old[tid]["label"]:changes.append({"id":tid,"system":s,"metric":m,"target":t["payload"]["target"],"previous":old[tid],"current":v})
   groups[s][m]={**counts,"macro_supported_rate":statistics.mean(rates) if rates else None,"whole":dict(whole),"atomic":dict(atoms),"finest_supported_type":dict(levels),"previous_whole":dict(prev)}
 usage=b.transport.usage_summary(run/"api",run/"request-slots");summary={"complete":done==len(tasks),"done":done,"total":len(tasks),"groups":groups,"usage":usage,"updated_at":time.time()}
 b.wr(run/"summary.json",summary);b.wr(run/"changed-judgments.json",changes)
 lines=["# 原30实体两项重评","",f"完成 {done}/{len(tasks)}；MiniMax-M3；峰值并发 {usage['peak_http']}。","","类型逐标签，描述逐实质陈述；主分数为实体内支持比例的平均，不确定留在分母。沿用全部原引用，未从全书补证据。新主分数与旧整项通过率口径不同。","","|方法|指标|新实体平均支持率|新整项通过|旧整项通过|","|---|---|---:|---:|---:|"]
 for s,gs in groups.items():
  for m,c in gs.items():
   rate=f"{c['macro_supported_rate']:.1%}" if c["macro_supported_rate"] is not None else "待评"
   lines.append(f"|{s}|{m}|{rate}|{c['whole'].get('pass',0)}/{c['total']}|{c['previous_whole'].get('pass',0)}/{c['total']}|")
 lines+=["","无原生字段仍N/A。summary.json保存原子判定计数、具体程度分布和不确定数；changed-judgments.json保存变化。裁判分句与标签未经独立人工金标准验证。"]
 (run/"REPORT.md").write_text("\n".join(lines)+"\n");return summary
b.parse=parse;b.report=report
if __name__=="__main__":sys.exit(b.main())
'''
(run/"runner.py").write_text(runner);compile(runner,"runner.py","exec")
(run/"PROTOCOL.md").write_text("原30实体不变；类型90项（我们、GraphRAG、AutoSchemaKG），描述60项（我们、GraphRAG）。原引用文本不变。我们的60个任务已验证原生观察及证据表的passage_ids与提交及评测完全一致。类型逐标签、描述逐自然实质陈述，先求实体内支持比例再取实体平均，并派生整项判定对照旧结果。类型额外报告最具体正确类别L1/L2/L3分布。MiniMax-M3温度0；HTTP并发6含重试；有效语义判定不重试。缺少原生字段N/A。")
wr(run/"manifest.json",{"model":"MiniMax-M3","workers":6,"total":150,"frozen_files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}})
print(json.dumps({"run":str(run),"tasks":150,"source_checks":len(audit)},ensure_ascii=False))

