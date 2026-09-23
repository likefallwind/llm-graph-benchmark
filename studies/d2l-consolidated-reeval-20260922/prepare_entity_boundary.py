from pathlib import Path
import json,shutil,hashlib,sys
R=Path("/home/likefallwind/code/llm-graph-benchmark");old=R/"outputs/d2l-entity-two-metrics-m3-c6-20260922";run=R/"outputs/d2l-entity-boundary-m3-c6-20260923";run.mkdir()
rd=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
prompts=rd(old/"prompts.json")
prompts["types"]+="兼容的上位类别允许通过；只检查类型归属，不评价实体是否值得建模或是否足够独立。类别含义有歧义而无法判断时保留uncertain。"
prompts["description"]="检查target.description的上下文支持程度。按自然语义分成可判断的片段，text必须依原顺序直接摘录原描述的连续文字，不改写、不添加、不重复，覆盖全文（分隔标点可省略）。结合完整描述理解各片段，不把修饰语误当额外断言。返回claims:[{text,label,reason,evidence_ids}]。只评描述，不评类型。没有可核验内容的残缺或空泛描述也返回一项并判fail。"
tasks=rd(old/"tasks.json");assert len(tasks)==150
for t in tasks:
 rule=prompts["types" if t["metric"]=="entity_typing" else "description"]
 t["messages"]=[{"role":"system","content":prompts["shared"]+rule},{"role":"user","content":json.dumps(t["payload"],ensure_ascii=False)}]
assert all(t["payload"]==o["payload"] for t,o in zip(tasks,rd(old/"tasks.json")))
wr(run/"tasks.json",tasks);wr(run/"prompts.json",prompts);wr(run/"previous-labels.json",{t["id"]:rd(old/"results"/(t["id"]+".json"))["value"] for t in tasks})
for f in ["private-key.json","source-audit.json","transport.py","base_runner.py"]:shutil.copy2(old/f,run/f)
shutil.copy2(old/"summary.json",run/"previous-summary.json")
runner=(old/"runner.py").read_text()
needle=' labels=[x["label"] for x in rows];'
guard=''' if not typing:
  source=t["payload"]["target"]["description"];cursor=0;separators=" ，,。；;\\t\\r\\n"
  for row in rows:
   text=row["text"].strip()
   if not text:raise ValueError("Empty source span")
   start=source.find(text,cursor)
   if start<0 or source[cursor:start].strip(separators):raise ValueError("Added or omitted description content")
   cursor=start+len(text)
  if source[cursor:].strip(separators):raise ValueError("Incomplete description coverage")
'''
assert needle in runner;runner=runner.replace(needle,guard+needle)
runner=runner.replace('if v["label"]!=old[tid]["label"]:', 'if v!=old[tid]:')
runner=runner.replace('沿用全部原引用，未从全书补证据。新主分数与旧整项通过率口径不同。','沿用全部原引用，未从全书补证据。描述片段须原样覆盖全文。旧结果为上一轮逐项评测。')
(run/"runner.py").write_text(runner)
sys.path.insert(0,str(run));import runner as rr
# Verify source-span protection independently of model labels.
task={"metric":"entity_definition_grounding","payload":{"target":{"description":"甲是工具，用于计算。"},"evidence":[{"id":"P1","text":"甲是计算工具"}]}}
def response(texts):return {"choices":[{"message":{"content":json.dumps({"claims":[{"text":x,"label":"pass","reason":"支持","evidence_ids":["P1"]} for x in texts]})}}]}
rr.parse(response(["甲是工具","用于计算"]),task)
for texts in [["甲是强大的工具","用于计算"],["甲是工具"],["用于计算","甲是工具"]]:
 try:rr.parse(response(texts),task)
 except ValueError:pass
 else:raise AssertionError("Source guard failed")
audit=[]
for t in rd(old/"tasks.json"):
 if t["metric"]!="entity_definition_grounding":continue
 v=rd(old/"results"/(t["id"]+".json"))["value"]
 audit.append({"id":t["id"],"name":t["payload"]["target"]["name"],"description":t["payload"]["target"]["description"],"previous_claims":[x["text"] for x in v["claims"]]})
wr(run/"previous-description-audit.json",audit)
(run/"PROTOCOL.md").write_text("""# 原30实体的裁判边界修正
原150项：类型90项（三方法各30），描述60项（我们和GraphRAG各30）。实体、字段和全部证据文本与上一轮完全相同，不补全书，不扩样。
只修改两处：类型允许兼容上位类别，不评价实体是否值得建模；描述按原文连续片段引用，程序检查按顺序覆盖全文且无增写，仅允许省略分隔标点，结合完整描述理解各片段。保留最具体正确类型粒度统计。
评分仍为每实体内部支持比例再宏平均，同时保留整项通过。描述分段边界仍可能不同，所以分数变动不能全部归因于语义修正。
MiniMax-M3温度0，HTTP最大并发6含重试；有效语义判定不按得分重跑。所有格式或来源覆盖失败保留原始响应。结构检查通过不等于语义判断都正确。
已检查旧60个描述的拆分，保存previous-description-audit.json；不将任何具体案例或预期排名写入提示。
""")
wr(run/"manifest.json",{"model":"MiniMax-M3","workers":6,"total":150,"frozen_files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}})
rr.report(run)
print(json.dumps({"run":str(run),"tasks":150,"source_guard_checks":4},ensure_ascii=False))

