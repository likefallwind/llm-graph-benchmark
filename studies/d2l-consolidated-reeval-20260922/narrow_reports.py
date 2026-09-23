from pathlib import Path
import json,hashlib
R=Path('/home/likefallwind/code/llm-graph-benchmark'); run=R/'outputs/d2l-baseline-only-m3-c6-20260922'
p=run/'finalize.py';s=p.read_text();s=s.replace("[('entity_correctness','实体所指正确率'),('entity_evidence','实体引用支持率'),('assertion_evidence','完整断言引用支持率'),('entity_typing'", "[('entity_typing'")
s=s.replace("if not g:cells.append('N/A（无可评输出/候选）');continue", "if not g:cells.append('保留历史结果，本轮未评' if s=='ours' else 'N/A（无可评输出/候选）');continue")
s=s.replace('# 收敛后的统一指标结果','# 基线复现修正补测结果')
s=s.replace('其余新任务完成状态：','本轮基线补测及粒度恢复完成状态：')
s=s.replace("'样本分母保留未确认与技术缺失。", "'我们的方法原有结果不重评，参见 ../d2l-metrics-comparison-20260922/ALL_METRICS.md。新补测使用逐项证据裁判，和历史规则、上下文及 decided 分母不同，不把两者当作同版校准后的直接排名。已用正确产物测过的实体正确率、实体引用和断言引用保留旧值及旧裁判限制。样本分母保留未确认与技术缺失。")
p.write_text(s)
m=json.loads((run/'manifest.json').read_text());m['frozen_files']['finalize.py']=hashlib.sha256(p.read_bytes()).hexdigest();(run/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
study=R/'studies/d2l-consolidated-reeval-20260922';(study/'LATEST_RUN.txt').write_text(str(run)+'\n')
p=R/'outputs/d2l-metrics-comparison-20260922/CONSOLIDATED_PROTOCOL.md';s=p.read_text();notice='> 2026-09-22 用户收窄范围：下文“四方法统一重评”计划已被替代。本轮只补测复现修正后三个基线尚未更新的类型、描述、身份、Book QA；我们的方法及已用正确产物完成的指标保留，粒度只补24条失败。执行清单以 ../d2l-baseline-only-m3-c6-20260922/SCOPE.json 为准。新旧裁判版本差异另列，不因此自动扩大重评。\n\n';p.write_text(s.replace('# 评估指标收敛版\n\n','# 评估指标收敛版\n\n'+notice,1))
print('scope and reports updated')
