from pathlib import Path
import json,hashlib,collections,datetime
root=Path('/home/likefallwind/code/llm-graph-benchmark')
old=root/'outputs/d2l-reliability-m3-c6-exploratory-20260920T132325Z'
new=root/'outputs/d2l-assertion-ledger-v25-20260922-recovery02'
gran=root/'outputs/d2l-granularity-m3-c6-20260922T030615Z'
out=root/'outputs/d2l-metrics-comparison-20260922';out.mkdir(exist_ok=True)
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fmt(n,d):return f'{n/d:.1%}（{n}/{d}）'
order=['ours','graphrag','autoschemakg','kggen'];names={'ours':'我们的方法','graphrag':'GraphRAG','autoschemakg':'AutoSchemaKG','kggen':'KGGen'}
o=rd(old/'summary.json');n=rd(new/'summary.json');g=rd(gran/'summary.json')
assert n['complete'] and (new/'.exit').read_text().strip()=='0'
key=rd(new/'private-key.json');gkey=rd(gran/'private-key.json');tasks=rd(new/'tasks.json');layers=collections.defaultdict(collections.Counter);correct=collections.defaultdict(collections.Counter)
for t in tasks:
 i=t['id'];s=key[i]['system'];assert all(key[i][k]==gkey[i][k] for k in ['system','item_id'])
 r=rd(new/'results'/(i+'.json'));assert r['status']=='done'
 f=gran/'results'/(i+'.json');gr=rd(f) if f.exists() else {'status':'pending'};layer=gr['value']['label'] if gr['status']=='done' else 'unassessed'
 layers[s][layer]+=1
 if r['value']['label']=='correct':correct[s][layer]+=1
for s in order:
 assert sum(layers[s].values())==200 and sum(correct[s].values())==n['systems'][s]['correct']
rows=[]
for title,kind,metric,label in [('实体所指正确率〔旧〕','entity','correctness','correct'),('实体引用支持率〔旧〕','entity','evidence','supported'),('完整断言确认正确率〔新〕',None,None,None),('断言引用支持率〔旧〕','assertion','evidence','supported')]:
 cells=[]
 for s in order:
  if kind: a=o['systems'][s][kind];cells.append(fmt(a[metric][label],a['selected']))
  else:cells.append(fmt(n['systems'][s]['correct'],200))
 rows.append('|'+ '|'.join([title]+cells)+'|')
text=['# D2L 四种方法指标对比（2026-09-22）','','完整断言最新重评已完成800/800；其余指标保留原评测版本。所有比例保留预定样本作分母，不删除不确定项或技术缺失项。','',
'## 主要质量指标','','|指标|我们的方法|GraphRAG|AutoSchemaKG|KGGen|','|---|---:|---:|---:|---:|']+rows
text+=['','实体所指正确率检查实体名称在原文中的指代；引用支持率检查系统原提交的引用是否支持输出。完整断言确认正确率检查参与者、关系及方向、描述中的全部实质命题、适用范围和肯否定是否得到原文支持。',
'','〔旧〕实体和引用结果未按本次新协议重评；旧裁判曾未通过反向关系开发检查，这些分数是历史探索性参考，不能当作已验证的准确率。实体正确性技术缺失：我们0、GraphRAG 2、AutoSchemaKG 1、KGGen 3；实体引用支持技术缺失：AutoSchemaKG 1，其余0；断言引用支持无技术缺失。',
'','新完整断言判定与旧引用支持判定使用不同协议和参考范围，不能用二者的差值解释引用效率。','',
'## 新完整断言判定分布','','|方法|确认正确|明确错误|证据不足或歧义|技术缺失|','|---|---:|---:|---:|---:|']
for s in order:
 a=n['systems'][s];text.append('|'+ '|'.join([names[s]]+[f"{a.get(k,0)}（{a.get(k,0)/200:.1%}）" for k in ['correct','incorrect','uncertain','unassessed']])+'|')
text+=['','## 关系表达粒度','','L1：只有泛关联；L2：粗粒度关系；L3：具体关系。判定对象是谓词加关系描述的完整表达，不以谓词种类数量衡量质量。','',
'|方法|L1 泛关联|L2 粗粒度|L3 具体关系|粒度未判定|','|---|---:|---:|---:|---:|']
for s in order:text.append('|'+ '|'.join([names[s]]+[fmt(layers[s][k],200) for k in ['L1','L2','L3','unassessed']])+'|')
text+=['','GraphRAG 的关系描述可以包含具体语义，因此通用 related_to 标签不意味着完整关系表达必属 L1。该表有24条粒度技术缺失，尚未补评；不能把未判定项当成粗粒度。','',
'## 粒度与正确性联合观察','','|方法|L3内完整断言确认正确率|既为L3且确认正确 / 全部200条|','|---|---:|---:|']
for s in order:text.append('|'+ '|'.join([names[s],fmt(correct[s]['L3'],layers[s]['L3']),fmt(correct[s]['L3'],200)])+'|')
text+=['','这里的正确性全部使用本次新标签，不再使用粒度旧报告附带的历史正确率。联合比例是已确认的具体且正确断言占样本的比例，不是召回率；24条粒度缺失可能改变它。L3内不同方法抽到的事实难度也未配对，不据此单独归因于方法优劣。','',
'## 历史覆盖探针（辅助参考）','','|方法|已恢复 / 48探针|未恢复|不确定|','|---|---:|---:|---:|']
coverage={'ours':(44,3,1),'graphrag':(48,0,0),'autoschemakg':(45,3,0),'kggen':(37,10,1)}
for s in order:
 a,b,c=coverage[s];text.append('|'+ '|'.join([names[s],fmt(a,48),str(b),str(c)])+'|')
text+=['','覆盖结果沿用旧报告，不是全书召回率，不与本轮正确性拼接计算F1。',
'','## 比较范围与来源','','AutoSchemaKG 是此前认可的语义边子集，保留既定适配过滤，不代表其完整系统。所有结果来自D2L这一份语料及既有输出；模型评分尚未经过独立人工验证，已发现的边界判定仍需复核。这里不合成总分，也不宣称统计显著排名。','']
for title,p in [('完整断言新重评',new/'COMPARISON.md'),('实体与引用历史评测',old/'REPORT.md'),('关系粒度原评测',gran/'REPORT.md')]:text.append(f'- {title}：{p}')
(out/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
metadata={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':{str(p):sha(p) for p in [new/'summary.json',old/'summary.json',gran/'summary.json',old/'legacy-coverage.json']},'systems':{s:{'new_assertion':n['systems'][s],'granularity_counts':dict(layers[s]),'new_correct_by_granularity':dict(correct[s]),'legacy_probe':coverage[s]} for s in order},'independent_validation':False}
(out/'data.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print((out/'REPORT.md').read_text())
