from pathlib import Path
import json
p=Path("/home/likefallwind/code/llm-graph-benchmark/outputs/d2l-entity-two-metrics-m3-c6-20260922")
s=json.loads((p/"summary.json").read_text());assert s["complete"] and s["done"]==150 and s["usage"]["active_http"]==0 and s["usage"]["peak_http"]<=6
names={"ours":"我们的方法","graphrag":"GraphRAG","autoschemakg":"AutoSchemaKG"}
lines=["# 原30实体：类型与描述重评结果","","150/150完成。MiniMax-M3，实际HTTP峰值并发6，最终技术缺失0。保持原实体、类型、描述及来源文本不变，没有重构图，也没有补入全书其他证据。","","## 新计分方式","","每个实体先计算支持项/全部项，再对30个实体取平均。类型的项为原生标签，描述的项为裁判划分的实质性陈述。不确定留在分母。","","|方法|类型标签正确率（实体宏平均）|描述上下文支持率（实体宏平均）|","|---|---:|---:|"]
for k,n in names.items():
 g=s["groups"][k];a=g["entity_typing"]["macro_supported_rate"];d=g.get("entity_definition_grounding");b=f"{d['macro_supported_rate']:.1%}" if d else "N/A";lines.append(f"|{n}|{a:.1%}|{b}|")
lines+=["|KGGen|N/A|N/A|","","## 与旧整项通过率对照","","整项通过要求该实体所有标签或全部描述陈述通过；这是统计单位一致的对照，但裁判由整项判断变为逐项判断，并非同一提示词的严格重复实验。","","|方法|指标|旧整项通过|新整项通过|新失败|新不确定|","|---|---|---:|---:|---:|---:|"]
for k,n in names.items():
 for m,c in s["groups"][k].items():
  title="实体类型" if m=="entity_typing" else "实体描述";a=c["previous_whole"].get("pass",0);b=c["whole"].get("pass",0)
  lines.append(f"|{n}|{title}|{a}/30（{a/30:.1%}）|{b}/30（{b/30:.1%}）|{c['whole'].get('fail',0)}|{c['whole'].get('uncertain',0)}|")
lines+=["","## 每个实体最具体的受支持类型","","|方法|L1泛类|L2一般类别|L3具体类别|没有通过的类型|","|---|---:|---:|---:|---:|"]
for k,n in names.items():
 c=s["groups"][k]["entity_typing"]["finest_supported_type"];lines.append("|"+n+"|"+"|".join(str(c.get(z,0))+"/30" for z in ["L1","L2","L3","none"])+"|")
lines+=["","## 来源核对","","我们的原生entity_observations与evidence两张表的来源编号并集，与提交和评测完全相同（60个任务，30个实体）；不存在本轮评测漏取已标注来源编号的问题。这不意味着实体标注覆盖了生成时的全部输入，或覆盖了描述的所有内容。原文公式/上下文不在标注片段中的问题仍保留，不用模型自己的quote替代原文。","","## 结果仍需谨慎解释：实际发现的裁判问题","","1. GraphRAG的SUBSEC_BERT_INPUT_REP原描述仅为“讨论BERT输入表示的小节编号”。新裁判拆分时额外加入“输入表示的构成与特殊词元”等内容，并要求具体章节编号，再据此扣分。新增内容不是原描述中的断言，这个失败判定不能直接采信。","2. 我们的CUDA核心描述从失败改为通过，但“每个核心都能处理向量运算”是否由来源中的乘加运算支持仍有争议，不能把此次通过当作人工确认。","3. GraphRAG的CONCEPT/CITATION边界仍存在解释差异；例如“复制一半数据”被以不构成独立概念为由判错，混入实体建模质量判断。","4. 支持率变化既包括计分方式改变，也包括裁判语义判断波动。新主分数不能直接与旧整项率计算提升。没有按预期排名人工修改任何标签。","","完整任务、提示词、原响应和新旧变化已保留。首批外层列表及未转义引号问题仅作格式修复，复用最早可解析回答；评分规则未改。格式修复与中断记录在format-fix目录，原始HTTP记录在api目录。"]
(p/"RESULTS.zh.md").write_text("\n".join(lines)+"\n")
print("Verified 150/150; wrote RESULTS.zh.md")

