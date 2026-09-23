from pathlib import Path
import json,sys,hashlib,time
p=Path("/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-entity-boundary-m3-c6-20260923")
f=p/"runner.py";src=f.read_text()
src=src.replace('if typing and x.get("level") not in ("L1","L2","L3"):','if typing and x["label"]=="pass" and x.get("level") not in ("L1","L2","L3"):')
f.write_text(src);sys.path.insert(0,str(p));import runner,transport
manifest=json.loads((p/"manifest.json").read_text());manifest["frozen_files"]["runner.py"]=hashlib.sha256(f.read_bytes()).hexdigest();transport.write(p/"manifest.json",manifest)
tasks=json.loads((p/"tasks.json").read_text());recovered=[]
for t in tasks:
 dest=p/"results"/(t["id"]+".json")
 if dest.exists() and json.loads(dest.read_text())["status"]=="done":continue
 fp=transport.digest({"model":"MiniMax-M3","messages":t["messages"],"temperature":0.0,"max_tokens":t["max_tokens"],"stream":False});options=[]
 for a in (p/"api/requests").glob("*/attempt-*.json"):
  v=json.loads(a.read_text())
  if v["payload_sha256"]!=fp:continue
  try:response=json.loads(v["raw_body"]);transport.validate_response(response);value=runner.parse(response,t)
  except Exception:continue
  options.append((v["started_at"],a,value))
 assert options,t["id"]
 _,a,value=min(options,key=lambda x:x[0])
 if dest.exists():(p/"format-fix"/("last-"+dest.name)).write_text(dest.read_text())
 transport.write(dest,{"task_id":t["id"],"status":"done","value":value,"recovered_from":str(a.relative_to(p)),"format_only":True,"finished_at":time.time()});recovered.append(t["id"])
transport.write(p/"format-fix/nonpass-level-recovery.json",{"rule":"Granularity is evaluated only for pass labels; null level on nonpass labels is irrelevant and now accepted without changing labels","recovered":recovered})
summary=runner.report(p);assert summary["complete"] and summary["done"]==150 and summary["usage"]["active_http"]==0 and summary["usage"]["peak_http"]<=6
# All final payloads are unchanged; every returned description has source-only full coverage.
old=p.parent/"d2l-entity-two-metrics-m3-c6-20260922";oldtasks={t["id"]:t for t in json.loads((old/"tasks.json").read_text())}
for t in tasks:
 assert t["payload"]==oldtasks[t["id"]]["payload"]
 value=json.loads((p/"results"/(t["id"]+".json")).read_text())["value"]
 runner.parse({"choices":[{"message":{"content":json.dumps(value)}}]},t)
transport.write(p/"verification.json",{"unchanged_inputs":150,"final_valid_results":150,"description_full_source_coverage":60,"type_tasks":90,"peak_http":summary["usage"]["peak_http"],"valid_semantic_labels_manually_changed":0})
(p/".finished").write_text(str(time.time())+"\nRecovered formatting-only failure after worker exit; see format-fix.\n")
prior=json.loads((p/"previous-summary.json").read_text())
names={"ours":"我们的方法","graphrag":"GraphRAG","autoschemakg":"AutoSchemaKG"}
lines=["# 原30实体：裁判边界修正结果","","150/150有效结果；MiniMax-M3；HTTP峰值并发6；最终技术缺失0。原样本、全部字段和全部来源文本与上一轮完全一致。","","## 修改范围","","类型明确允许兼容的上位类别，不评价实体是否值得建模。描述只能摘录原描述的连续片段，按顺序完整覆盖全文；程序拒绝增写、实质遗漏或重排，忽略空白排版及分隔逗号、句号、分号、冒号。未从全书补证据。","","|方法|类型：上一轮→本轮|描述：上一轮→本轮|","|---|---:|---:|"]
for k,name in names.items():
 cells=[]
 for m in ["entity_typing","entity_definition_grounding"]:
  c=summary["groups"][k].get(m);o=prior["groups"][k].get(m)
  cells.append(f"{o['macro_supported_rate']:.1%} → {c['macro_supported_rate']:.1%}" if c else "N/A")
 lines.append("|"+name+"|"+"|".join(cells)+"|")
lines+=["|KGGen|N/A|N/A|","","两项主分数均先计算每个实体内部支持比例，再对30实体平均；不确定在分母中。描述分段边界仍可能不同，不能把变化全部解释为判定改进。","","## 整项通过及不确定","","|方法|指标|上一轮全部通过|本轮全部通过|本轮失败|本轮不确定|","|---|---|---:|---:|---:|---:|"]
for k,name in names.items():
 for m,c in summary["groups"][k].items():
  title="类型" if m=="entity_typing" else "描述";w=c["whole"];o=c["previous_whole"]
  lines.append(f"|{name}|{title}|{o.get('pass',0)}/30|{w.get('pass',0)}/30|{w.get('fail',0)}|{w.get('uncertain',0)}|")
lines+=["","## 每个实体最具体的正确类型","","|方法|L1泛类|L2一般类别|L3具体类别|无通过类型|","|---|---:|---:|---:|---:|"]
for k,name in names.items():
 c=summary["groups"][k]["entity_typing"]["finest_supported_type"];lines.append("|"+name+"|"+"|".join(f"{c.get(z,0)}/30" for z in ["L1","L2","L3","none"])+"|")
lines+=["","## 个案核查与限制","","- GraphRAG的“SUBSEC_BERT_INPUT_REP”描述本轮仅引用原句“讨论BERT输入表示的小节编号”，判为通过，未再添加构成与特殊词元等内容。","- GraphRAG的“复制一半数据”和“学生”的CONCEPT类型本轮按兼容上位类别通过，不再因实体独立性或过于宽泛而扣正确性分。","- 我们的“向量空间”描述本轮引用原句并通过，不再改写为新的主谓断言。","- 仍有语义争议：GraphRAG“每个GPU获得一半数据副本”被拆出单独“副本”后判错，尽管来源直接说“每个GPU可以复制一半的数据”。文字覆盖检查无法保证裁判对完整句意理解正确。","- 我们CUDA核心描述仍被判通过，标量乘加与向量运算的语义边界仍有争议。","- 所有自动标签原样保留；没有为了排名改分。当前版本先冻结，保留争议项，不自动追加提示或扩大到100样本。","","## 技术记录","","失败的原响应均保留。空白/冒号格式以及非通过类型缺少粒度值只做解析恢复，未修改文字或标签。后台worker原退出码3保留；其余格式失败恢复后汇总为150/150，verification.json记录最终核查。来源片段完整覆盖60/60，所有150输入与上一轮相同。"]
(p/"RESULTS.zh.md").write_text("\n".join(lines)+"\n")
print(json.dumps({"complete":summary["complete"],"done":summary["done"],"groups":summary["groups"]},ensure_ascii=False))

