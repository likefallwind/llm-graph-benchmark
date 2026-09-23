from pathlib import Path
import json,hashlib,random,shutil,sys,time
R=Path("/home/likefallwind/code/llm-graph-benchmark");old=R/"outputs/d2l-entity-boundary-m3-c6-20260923";run=R/"outputs/d2l-entity100-m3-c6-20260923"
sys.path.insert(0,str(R/"src"))
from llm_graph_benchmark.bundle import SubmissionBundle,BenchmarkBundle
from llm_graph_benchmark.sampling import _task_id
rd=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert rd(old/"summary.json")["complete"]
# Produce the completed 30-entity granularity table before expanding the sample.
s30=rd(old/"summary.json");names={"ours":"我们的方法","graphrag":"GraphRAG","autoschemakg":"AutoSchemaKG"}
lines=["# 30实体类型粒度细分","","只对正确类型统计粒度；每实体取最具体的正确类型。L1泛类，L2一般功能/领域类别，L3进一步区分功能/性质的具体类别。没有正确类型单列。正确率与粒度分开，不因类型宽泛而扣正确率。","","|方法|仅L1泛类|最高L2|最高L3|无正确类型|正确且L2/L3覆盖|正确且L3覆盖|","|---|---:|---:|---:|---:|---:|---:|"]
for k,n in names.items():
 c=s30["groups"][k]["entity_typing"]["finest_supported_type"]
 cells=[f"{c.get(z,0)}/30（{c.get(z,0)/30:.1%}）" for z in ["L1","L2","L3","none"]]
 cells+=[f"{(c.get('L2',0)+c.get('L3',0))/30:.1%}",f"{c.get('L3',0)/30:.1%}"]
 lines.append("|"+n+"|"+"|".join(cells)+"|")
lines+=["","复用本轮原始裁判，不新增调用或改标签。粒度本身仍是模型判断，不宣称独立金标准。"]
(old/"TYPE_GRANULARITY_30.md").write_text("\n".join(lines)+"\n")
run.mkdir(exist_ok=True);assert not (run/'tasks.json').exists()
b=BenchmarkBundle.load(R/"outputs/d2l-full1105-vnext-20260826/benchmark.json");units=b.unit_by_document
base=R/"outputs/d2l-baseline-correction-m3-c6-20260909-172849"
paths={"ours":R/"outputs/d2l-full1105-vnext-20260826/submission.json","graphrag":base/"graphrag/submission.json","autoschemakg":base/"autoschemakg/evaluation/semantic-submission.json","kggen":base/"kggen/submission.json"}
ot={t["id"]:t for t in rd(old/"tasks.json")};ok=rd(old/"private-key.json");prompts=rd(old/"prompts.json")
tasks=[];key={};sampling={};exclusions=[];reused=0;inputs={}
for system,path in paths.items():
 sub=SubmissionBundle.load(path);subhash=sub.submission_hash;inputs[str(path)]=sha(path);docs=sub.payload["documents"];assert len(docs)==1
 d=docs[0];did=d["document_id"];entities=d["entities"]
 has_types=any(e.get("types") for e in entities);has_desc=any(e.get("definition") and e.get("metadata",{}).get("definition_available") is not False for e in entities)
 if not has_types and not has_desc:
  sampling[system]={"native_types":False,"native_description":False,"sampled":0,"reason":"No native fields for either metric"};continue
 previous=[]
 for e in entities:
  if any(_task_id(20260820,subhash,m,did,str(e["id"])) in ot for m in ["entity_typing","entity_definition_grounding"]):previous.append(e)
 assert len(previous)==30,(system,len(previous))
 oldids={str(e["id"]) for e in previous};remaining=sorted((e for e in entities if str(e["id"]) not in oldids),key=lambda e:str(e["id"]))
 rng=random.Random(f"20260923:{subhash}:entity100-extension");added=rng.sample(remaining,70);selected=previous+added;assert len({str(e["id"]) for e in selected})==100
 sampling[system]={"sampled":100,"population":len(entities),"native_types":has_types,"native_description":has_desc,"preserved_ids":sorted(oldids),"added_ids":[str(e["id"]) for e in added],"field_counts":{}}
 for e in selected:
  for m in ["entity_typing","entity_definition_grounding"]:
   available=bool(e.get("types")) if m=="entity_typing" else bool(e.get("definition")) and e.get("metadata",{}).get("definition_available") is not False
   if not available:
    exclusions.append({"system":system,"entity_id":str(e["id"]),"metric":m,"reason":"native field absent"});continue
   tid=_task_id(20260820,subhash,m,did,str(e["id"]))
   target={"name":e["name"],"types":e["types"]} if m=="entity_typing" else {"name":e["name"],"description":e["definition"]}
   evidence=[];seen=set()
   for ref in e.get("evidence",[]):
    uid=str(ref["unit_id"])
    if uid not in seen:evidence.append({"id":uid,"text":units[did][uid]["text"]});seen.add(uid)
   payload={"target":target,"evidence":evidence}
   if tid in ot:
    assert ot[tid]["payload"]==payload,(system,tid)
    t=ot[tid];v=rd(old/"results"/(tid+".json"));assert v["status"]=="done"
    wr(run/"results"/(tid+".json"),{**v,"reused_from":str(old/"results"/(tid+".json")),"source_sha256":sha(old/"results"/(tid+".json"))});reused+=1
   else:
    rule=prompts["types" if m=="entity_typing" else "description"];messages=[{"role":"system","content":prompts["shared"]+rule},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]
    size=len(json.dumps(messages,ensure_ascii=False).encode());t={"id":tid,"metric":m,"payload":payload,"messages":messages,"max_tokens":8192,"input_bytes":size,"oversized":size>350000}
   tasks.append(t);key[tid]={"system":system,"metric":m,"entity_id":str(e["id"]),"document_id":did,"preserved":str(e["id"]) in oldids}
   sampling[system]["field_counts"][m]=sampling[system]["field_counts"].get(m,0)+1
assert reused==150
random.Random(20260923).shuffle(tasks)
for n,v in [("tasks.json",tasks),("private-key.json",key),("sampling.json",sampling),("excluded-fields.json",exclusions),("prompts.json",prompts),("previous-summary.json",s30)]:wr(run/n,v)
for f in ["transport.py","base_runner.py"]:shutil.copy2(old/f,run/f)
src=(old/"runner.py").read_text();prefix=src[:src.index("def report(run):")]
report=r'''
def report(run):
 tasks=rd(run/"tasks.json");keys=rd(run/"private-key.json");sampling=rd(run/"sampling.json");groups={};done=0;reused=0;details=[]
 for system in ["ours","graphrag","autoschemakg"]:
  groups[system]={}
  for metric in ["entity_typing","entity_definition_grounding"]:
   ts=[t for t in tasks if keys[t["id"]]["system"]==system and t["metric"]==metric]
   if not ts:continue
   c=Counter(total=len(ts),sampled=100,field_absent=100-len(ts));whole=Counter();atoms=Counter();levels=Counter();labellevels=Counter();rates=[];rate_old=[];rate_added=[]
   for t in ts:
    f=run/"results"/(t["id"]+".json")
    if not f.exists():c["pending"]+=1;continue
    r=rd(f);c[r["status"]]+=1
    if r["status"]!="done":continue
    done+=1;reused+=bool(r.get("reused_from"));v=r["value"];whole[v["label"]]+=1
    rows=v["items" if metric=="entity_typing" else "claims"];ac=Counter(x["label"] for x in rows);atoms.update(ac);rate=ac["pass"]/len(rows);rates.append(rate)
    (rate_old if keys[t["id"]]["preserved"] else rate_added).append(rate)
    if metric=="entity_typing":
     levels[max((x["level"] for x in rows if x["label"]=="pass"),default="none")]+=1
     labellevels.update(x["level"] for x in rows if x["label"]=="pass")
    details.append({"id":t["id"],**keys[t["id"]],"name":t["payload"]["target"]["name"],"score":rate,"value":v})
   groups[system][metric]={**c,"macro_supported_rate":statistics.mean(rates) if rates else None,"preserved30_rate":statistics.mean(rate_old) if rate_old else None,"added70_rate":statistics.mean(rate_added) if rate_added else None,"whole":dict(whole),"atomic":dict(atoms),"finest_supported_type":dict(levels),"supported_label_levels":dict(labellevels)}
 usage=b.transport.usage_summary(run/"api",run/"request-slots")
 summary={"complete":done==len(tasks),"done":done,"total":len(tasks),"reused":reused,"new_done":done-reused,"new_total":len(tasks)-150,"groups":groups,"sampling":sampling,"usage":usage,"updated_at":time.time()}
 b.wr(run/"summary.json",summary);b.wr(run/"case-results.json",details)
 names={"ours":"我们的方法","graphrag":"GraphRAG","autoschemakg":"AutoSchemaKG"}
 lines=["# 100实体：类型正确性、类型粒度与描述支持","",f"状态：{'完成' if summary['complete'] else '运行中'}；有效结果 {done}/{len(tasks)}，复用 {reused}，新增完成 {done-reused}/{len(tasks)-150}。MiniMax-M3；本轮实测HTTP峰值并发 {usage['peak_http']}。","","原30实体与判定保留，固定随机种子从其余实体抽取70个。无原生字段不送评，单列字段覆盖。主分数为每实体内部支持比例的平均，不确定留在分母；技术失败不混入语义分数，缺失时分数标为临时。","","|方法|指标|有效结果/可评样本|字段覆盖|当前支持率|原30|新增70|","|---|---|---:|---:|---:|---:|---:|"]
 def pct(x):return f"{x:.1%}" if x is not None else "N/A"
 for s,gs in groups.items():
  for m,c in gs.items():
   title="类型标签正确率" if m=="entity_typing" else "描述上下文支持率"
   lines.append(f"|{names[s]}|{title}|{c.get('done',0)}/{c['total']}|{c['total']}/100|{pct(c['macro_supported_rate'])}|{pct(c['preserved30_rate'])}|{pct(c['added70_rate'])}|")
 lines+=["","AutoSchemaKG无原生描述、KGGen无原生类型与描述，对应指标N/A。","","## 类型粒度细分","","L1泛类；L2一般功能或领域类别；L3进一步区分功能或性质的具体类别。按每实体最具体的正确类型分组。失败类型不获得粒度信用。","","|方法|仅L1|最高L2|最高L3|无通过类型|无类型字段|待评/技术缺失|","|---|---:|---:|---:|---:|---:|---:|"]
 for s,gs in groups.items():
  c=gs["entity_typing"];l=c["finest_supported_type"]
  lines.append("|"+names[s]+"|"+"|".join(str(l.get(z,0)) for z in ["L1","L2","L3","none"])+f"|{c['field_absent']}|{c['total']-c.get('done',0)}|")
 lines+=["","|方法|正确且L2/L3覆盖（全部100实体）|正确且L3覆盖（全部100实体）|","|---|---:|---:|"]
 for s,gs in groups.items():
  c=gs["entity_typing"];l=c["finest_supported_type"];suffix="（临时下界）" if c.get("done",0)!=c["total"] else ""
  lines.append(f"|{names[s]}|{(l.get('L2',0)+l.get('L3',0))/100:.1%}{suffix}|{l.get('L3',0)/100:.1%}{suffix}|")
 lines+=["","## 正确类型标签内部的粒度构成","","此表以所有通过的标签为分母，多标签实体权重更大，只作补充；主表始终按实体统计。","","|方法|通过标签数|L1|L2|L3|","|---|---:|---:|---:|---:|"]
 for s,gs in groups.items():
  l=gs["entity_typing"]["supported_label_levels"];n=sum(l.values())
  lines.append("|"+names[s]+"|"+str(n)+"|"+"|".join(f"{l.get(z,0)}/{n}" for z in ["L1","L2","L3"])+"|")
 lines+=["","描述原文覆盖检查只阻止增写/漏字，不能保证裁判语义理解正确。类型粒度也属于自动判断。各方法为各自输出的随机样本，不是同名实体配对实验。无效响应仅作有限技术重试，不按排名改提示或标签。summary.json保留pass/fail/uncertain、技术状态和整项判定；case-results.json包含全部个案。"]
 (run/"REPORT.md").write_text("\n".join(lines)+"\n");return summary
b.parse=parse;b.report=report
if __name__=="__main__":sys.exit(b.main())
'''
(run/"runner.py").write_text(prefix+report);compile(prefix+report,"runner.py","exec")
(run/"PROTOCOL.md").write_text("""# 100实体扩展协议
先复用已完成30实体的类型粒度评测，汇总TYPE_GRANULARITY_30.md；之后每个可评方法保留原30实体，从余下实体按固定种子随机抽70，不参考判定或得分，不按字段是否缺失替换样本。
类型正确率和描述支持率仍为实体宏平均；类型粒度报告每实体最具体正确类型L1/L2/L3分布、正确且L2/L3覆盖、正确且L3覆盖，另附通过标签的粒度分布。不设计加权总分，不奖励错误细粒度标签。
沿用上一轮完全相同提示、模型、证据读取及原文片段检查。150个旧结果原样复用；只请求新增可评项。缺少原生字段单列N/A或覆盖率，不伪造字段，不补全书证据。
MiniMax-M3温度0，总HTTP并发6包括重试。后台完成后自动生成REPORT.md与summary.json；技术失败不当作语义失败。原30与新增70分别报告，避免掩盖抽样变化。
""")
wr(run/"manifest.json",{"model":"MiniMax-M3","workers":6,"seed_extension":20260923,"original_seed":20260820,"total":len(tasks),"reused":reused,"new":len(tasks)-reused,"input_hashes":inputs,"frozen_files":{p.name:sha(p) for p in run.iterdir() if p.is_file()}})
sys.path.insert(0,str(run));import runner;runner.report(run)
(R/"studies/d2l-consolidated-reeval-20260922/LATEST_RUN.txt").write_text(str(run)+"\n")
print(json.dumps({"run":str(run),"total":len(tasks),"reused":reused,"new":len(tasks)-reused,"fields":{k:v.get("field_counts") for k,v in sampling.items()}},ensure_ascii=False))

