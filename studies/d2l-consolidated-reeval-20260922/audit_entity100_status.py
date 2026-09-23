from pathlib import Path
import json,sys,hashlib,time,statistics
P=Path("/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-entity100-m3-c6-20260923")
f=P/"runner.py";s=f.read_text();old=s
s=s.replace('separators="，,。；;：:"','separators="，,。；;：:、"');assert s!=old
(P/"format-recovery/runner-before-enumeration-separator.py").write_text(old);f.write_text(s)
sys.path.insert(0,str(P));import runner,transport
t=next(t for t in json.loads((P/"tasks.json").read_text()) if t["id"]=="t_ef0a652dac606246d659")
valid=[]
for req in (P/"api/requests").glob("*/request.json"):
 q=json.loads(req.read_text())
 if t["payload"]["target"]["description"] not in q["messages"][1]["content"]:continue
 for af in req.parent.glob("attempt-*.json"):
  a=json.loads(af.read_text())
  try:r=json.loads(a["raw_body"]);transport.validate_response(r);v=runner.parse(r,t)
  except Exception:continue
  valid.append((a["started_at"],af,v))
_,af,v=min(valid,key=lambda x:x[0]);dest=P/"results"/(t["id"]+".json")
transport.write(P/"format-recovery/last-missing-before.json",json.loads(dest.read_text()))
transport.write(dest,{"task_id":t["id"],"status":"done","value":v,"recovered_from":str(af.relative_to(P)),"format_only":True,"finished_at":time.time()})
transport.write(P/"format-recovery/enumeration-separator-fix.json",{"rule":"Permit omitted enumeration separator 、, consistent with the existing punctuation-omission rule; no words or labels changed","source":str(af.relative_to(P))})
manifest=json.loads((P/"manifest.json").read_text());manifest["frozen_files"]["runner.py"]=hashlib.sha256(f.read_bytes()).hexdigest();transport.write(P/"manifest.json",manifest)
summary=runner.report(P);assert summary["complete"] and summary["done"]==497
tasks=json.loads((P/"tasks.json").read_text());keys=json.loads((P/"private-key.json").read_text());verified={}
for system in ["ours","graphrag","autoschemakg"]:
 rates=[]
 for t in tasks:
  if keys[t["id"]]["system"]==system and t["metric"]=="entity_typing":
   v=json.loads((P/"results"/(t["id"]+".json")).read_text())["value"];a=v["items"]
   assert len(a)==len(t["payload"]["target"]["types"]) and [x["index"] for x in a]==list(range(len(a)))
   rates.append(sum(x["label"]=="pass" for x in a)/len(a))
 assert abs(statistics.mean(rates)-summary["groups"][system]["entity_typing"]["macro_supported_rate"])<1e-12
 verified[system]={"entities":len(rates),"recomputed_macro":statistics.mean(rates)}
for t in tasks:
 v=json.loads((P/"results"/(t["id"]+".json")).read_text())["value"]
 runner.parse({"choices":[{"message":{"content":json.dumps(v)}}]},t)
transport.write(P/"type-arithmetic-audit.json",{"verified":verified,"all_results_structurally_valid":497,"semantic_gold_validated":False})
(P/".finished").write_text(str(time.time())+"\nCompleted after formatting-only recovery.\n")
transport.write(P/"format-recovery-final.json",{"complete":True,"done":497,"recovered_last":str(af.relative_to(P))})
audit="""# 类型正确率核查
核查范围：独立重算三方法全部297个实体的类型得分、验证标签数量与索引；查看我们与GraphRAG所有非通过类型的裁判理由，并回查代表性争议案例的来源。未声称对全部通过标签做了独立人工金标准标注。

## 计算正确，自动裁判语义仍有错误
指标是每实体通过标签数/全部标签数，再对有类型字段的实体平均。不确定留在分母。我们97个有类型实体，另3个缺失；GraphRAG与AutoSchemaKG各100。独立复算分别84.9525%、87.9444%、83.8036%，与报告一致。不是全部标签合并后的微平均，也不是所有类型都对才通过。

## 明确发现的个案
- 我们“蒙特卡洛树搜索”输入标签顺序为[优化算法,搜索算法]，返回index0的pass理由实际解释搜索算法，index1的uncertain理由实际解释优化算法。索引本身合法，但语义错位。此案例总通过比例仍为1/2，不能据此改动总分；逐标签说明与粒度归属不可靠。
- GraphRAG“前向传播方法→OPERATION”被以“不是独立命名实体”判fail，尽管给出的代码有forward计算过程。这把实体准入判断混入了类型判断，理由不符合本项边界。
- 我们“nn.CrossEntropyLoss→平方误差损失”“BERT表示→model”“优化器→损失函数”等扣分有明确来源依据，不能把我们所有扣分归因于裁判问题。

## 结论
汇总公式没有计算错误，但自动判定并非全部可靠。类型结果和2.99个百分点的差距只能标为当前自动裁判结果，不能宣布独立验证的方法排名。所有原标签保留，未按预期排名人工修分，未新启动类型重评。

## 描述支持率
描述一直包含在同一轮评测。最后一项GoogLeNet因分隔顿号被原文检查器误拒，已从最早符合完整原文覆盖的原始回答恢复，无新API调用，无语义改写。现为我们100/100、GraphRAG100/100；完整结果见REPORT.md。结构校验正确不等于每条语义判定都正确。
"""
(P/"TYPE_AUDIT.md").write_text(audit)
report=P/"REPORT.md";report.write_text(report.read_text().replace("# 100实体：类型正确性、类型粒度与描述支持","# 100实体：类型正确性、类型粒度与描述支持\n\n注意：类型汇总已独立复算，但发现裁判理由错位及评价边界越界，结果为自动裁判值，不能视为人工金标准；见TYPE_AUDIT.md。",1))
print(json.dumps({"done":summary["done"],"description":{k:summary["groups"][k]["entity_definition_grounding"] for k in ["ours","graphrag"]}},ensure_ascii=False))

