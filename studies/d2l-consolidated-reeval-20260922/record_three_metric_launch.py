from pathlib import Path
import json
R=Path('/home/likefallwind/code/llm-graph-benchmark');p=R/'outputs/d2l-three-metrics-repaired-m3-c6-20260922';H=R/'studies/d2l-consolidated-reeval-20260922';(H/'LATEST_RUN.txt').write_text(str(p)+'\n');(H/'RUN.md').write_text('# 当前运行\n\n已授权并启动三项修复重评：类型90、描述60、48探针完整覆盖192，共342。四方法使用相同简短通用规则，旧样本及Top10保持不变，完整保留证据。MiniMax-M3，全部调用及重试并发上限6。\n\n'+str(p/'REPORT.md')+'\n\n此前其他指标结果保持原样，修复结果未完成前不替换旧分数。\n')
f=R/'outputs/d2l-final-comparison-20260922/REPORT.md';s=f.read_text();notice='> 已启动三项修复重评（342项）；完成前以下旧类型、描述和覆盖分数仍保留待复核标识。新结果见 [三项修复评测](../d2l-three-metrics-repaired-m3-c6-20260922/REPORT.md)。\n\n';s=s.replace('# 最终关注指标对照表（2026-09-22）\n\n','# 最终关注指标对照表（2026-09-22）\n\n'+notice,1);f.write_text(s)
for name in ['progress.json','request-slots/http-progress.json','.exit']:
 f=p/name
 if f.exists():
  if name.endswith('http-progress.json'):
   v=json.loads(f.read_text());print({k:v.get(k) for k in ['active_http','peak_http','http_attempts']})
  else:print(name,f.read_text()[:600])
