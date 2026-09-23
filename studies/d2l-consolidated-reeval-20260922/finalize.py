"""Join new metrics with preserved assertion correctness and repaired granularity."""
from pathlib import Path
import sys,collections
from evaluate import rd,wr,sha,summarize

def main(run):
 summary=summarize(run);manifest=rd(run/'manifest.json');old=Path(manifest['assertion_run']);gsrc=Path(manifest['granularity_run']);akey=rd(old/'private-key.json');tasks=rd(run/'tasks.json');key=rd(run/'private-key.json')
 for name,h in rd(run/'preserved-assertion-results.json').items():
  if sha(old/'results'/name)!=h:raise ValueError('Preserved assertion result changed')
 gran={}
 for f in (run/'granularity-preserved').glob('*.json'):gran[f.stem]=rd(f)
 for t in tasks:
  if t['metric']=='granularity':
   f=run/'results'/(t['id']+'.json');gran[key[t['id']]['original_id']]=rd(f) if f.exists() else {'status':'pending'}
 gc=collections.defaultdict(collections.Counter);joint=collections.defaultdict(collections.Counter)
 for t in rd(gsrc/'tasks.json'):
  i=t['id'];s=akey[i]['system'];r=gran[i];l=r.get('value',{}).get('label','unassessed') if r['status']=='done' else 'unassessed';gc[s][l]+=1
  if rd(old/'results'/(i+'.json'))['value']['label']=='correct':joint[s][l]+=1
 systems=['ours','graphrag','autoschemakg','kggen'];names=['我们的方法','GraphRAG','AutoSchemaKG','KGGen'];rows=[]
 for m,title in [('entity_correctness','实体所指正确率'),('entity_evidence','实体引用支持率'),('assertion_evidence','完整断言引用支持率'),('entity_typing','实体类型正确率'),('entity_definition','实体定义/描述证据支持率'),('alias_identity','别名同一性正确率'),('identity_split','实体拆分正确率'),('book_qa','图谱问答支持率')]:
  cells=[]
  for s in systems:
   g=summary['groups'].get(s,{}).get(m)
   if not g:cells.append('N/A（无可评输出/候选）');continue
   n=g['selected'];v=g.get('correct',0)+g.get('supported',0);missing=sum(v for k,v in g.items() if k.startswith('status_'));cells.append(f'{v}/{n} ({v/n:.1%})'+(f'；缺失{missing}' if missing else ''))
  rows.append([title]+cells)
 oldsummary=rd(old/'summary.json');rows.insert(2,['完整断言确认正确率（保留）']+[f"{oldsummary['systems'][s]['correct']}/200 ({oldsummary['systems'][s]['correct']/200:.1%})" for s in systems])
 for layer in ['L1','L2','L3','uncertain','unassessed']:rows.append(['关系粒度 '+layer]+[f'{gc[s][layer]}/200 ({gc[s][layer]/200:.1%})' for s in systems])
 rows.append(['具体且正确 / 全部200']+[f'{joint[s]["L3"]}/200 ({joint[s]["L3"]/200:.1%})' for s in systems])
 rows.append(['L3内完整断言确认正确率']+[f'{joint[s]["L3"]}/{gc[s]["L3"]} ({joint[s]["L3"]/gc[s]["L3"]:.1%})' if gc[s]['L3'] else 'N/A' for s in systems])
 cov=rd(Path(manifest['historical_reliability_run'])/'legacy-coverage.json')['systems'];rows.append(['历史48探针覆盖（未重评）']+[str(cov[s]['counts'].get('yes',0))+'/48' for s in systems])
 lines=['# 收敛后的统一指标结果','','模型评测；未经独立人工校准。完整断言正确性保留本日已完成判断，其余新任务完成状态：'+str(summary['complete'])+'。','', '|指标|'+'|'.join(names)+'|','|---|---:|---:|---:|---:|']
 for row in rows:lines.append('|'+ '|'.join(row)+'|')
 lines+=['','样本分母保留未确认与技术缺失。N/A表示未提供字段或没有可评对象，不是0%正确率。字段可用性见下表。实体类型/定义是在原100条样本中有字段者；别名是非平凡别名样本；身份拆分是表面碰撞候选样本；QA仅测统一检索候选的答案支持，不代表原生问答系统。','', '|方法|有类型/节点|有真实定义或描述/节点|有别名/节点|','|---|---:|---:|---:|']
 for s,name in zip(systems,names):
  a=summary['availability'][s];lines.append('|'+ '|'.join([name]+[f"{a[k]}/{a['nodes']}" for k in ['with_types','with_definition','with_aliases']])+'|')
 lines+=['','来源范围、代码与样本冻结哈希见manifest.json；所有请求和技术重试保留。历史结构与million-token构图统计见上一份指标收敛报告。']
 (run/'MAIN_RESULTS.md').write_text('\n'.join(lines)+'\n');wr(run/'joined-results.json',{'metrics':summary,'granularity':dict(gc),'correct_by_granularity':dict(joint),'assertion_correctness':oldsummary})
 review=[]
 for t in tasks:
  f=run/'results'/(t['id']+'.json')
  if f.exists():
   v=rd(f)
   if v['status']!='done' or v['value']['label'] not in {'correct','supported','L1','L2','L3'}:review.append({'id':t['id'],**key[t['id']],'result':v})
 wr(run/'review-items.json',review);print('Final report:',str(run/'MAIN_RESULTS.md'));return 0
if __name__=='__main__':sys.exit(main(Path(sys.argv[1])))
