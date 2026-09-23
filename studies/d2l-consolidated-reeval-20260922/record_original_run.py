from pathlib import Path
import json
R=Path('/home/likefallwind/code/llm-graph-benchmark');H=R/'studies/d2l-consolidated-reeval-20260922';run=R/'outputs/d2l-baseline-original-rubric-m3-c6-20260922'
(H/'RUN.md').write_text('# 当前补测\n\n已启动：'+str(run)+'\n\n按用户最后确认，仅使用原通用裁判对正确复现的三个基线补测。原提示词、任务展示、随机种子、30条抽样、24题和Top10检索、统计分母保持历史设置。无原生字段记N/A。\n\n282个基线任务；原24个粒度失败已复用8个恢复结果，剩16个待补。我们的方法144个既有M3判定原样保留，未安排重评。最新800个完整断言判断及其它已经基于正确产物完成的结果也保留。\n\n模型MiniMax-M3；所有调用及重试共用6个请求槽。不根据方法得分改规则或重试。新报告：'+str(run/'REPORT.md')+'\n\n此前 expanded / baseline-only 细则版本不执行，保留仅用于审计；GENERAL_RUBRIC_DRAFT.md也未启用。\n')
p=R/'outputs/d2l-metrics-comparison-20260922/CONSOLIDATED_PROTOCOL.md';s=p.read_text();note='> 最终执行（2026-09-22）：已依用户要求恢复原通用裁判，只替换修正后的三个基线产物补测。282个基线任务及16条剩余粒度恢复正在运行。此前“四方法统一重评”和新增细则方案均不执行。当前报告：../d2l-baseline-original-rubric-m3-c6-20260922/REPORT.md。\n\n';p.write_text(s.replace('# 评估指标收敛版\n\n','# 评估指标收敛版\n\n'+note,1))
for f in ['progress.json','.exit','request-slots/http-progress.json']:
 p=run/f
 if p.exists():
  if f.endswith('http-progress.json'):
   v=json.loads(p.read_text());print(f,{k:v.get(k) for k in ['active_http','peak_http','http_attempts']})
  else:print(f,p.read_text()[:1000])
