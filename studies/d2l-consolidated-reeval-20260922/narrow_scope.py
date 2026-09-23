from pathlib import Path
import json,hashlib,shutil,collections
R=Path('/home/likefallwind/code/llm-graph-benchmark'); src=R/'outputs/d2l-consolidated-m3-c6-20260922-v6'; dst=R/'outputs/d2l-baseline-only-m3-c6-20260922'
assert not dst.exists()
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','request-slots','.run.lock','development-report.json','summary.json','progress.json','REPORT.md','MAIN_RESULTS.md'))
tasks=rd(dst/'tasks.json');key=rd(dst/'private-key.json'); metrics={'entity_typing','entity_definition','alias_identity','identity_split','book_qa'}
keep=[t for t in tasks if (key[t['id']]['system']!='ours' and t['metric'] in metrics) or t['metric']=='granularity']; ids={t['id'] for t in keep}
wr(dst/'tasks.json',keep);wr(dst/'private-key.json',{i:key[i] for i in ids});wr(dst/'pilot.json',[t for t in rd(dst/'pilot.json') if t['id'] in ids]);dev=[t for t in rd(dst/'development.json') if t['metric'] in metrics|{'granularity'}];wr(dst/'development.json',dev)
allowed=ids|{t['id'] for t in dev}; retired=dst/'out-of-scope-diagnostics';retired.mkdir()
for f in (dst/'results').glob('*.json'):
 if f.stem not in allowed:f.rename(retired/f.name)
manifest=rd(dst/'manifest.json');manifest.update(protocol='baseline-correction-only-v1',scope='Only previously mis-reproduced baselines missing current-output measurements; preserve ours and already-corrected metrics; recover only 24 failed granularity items.',counts=dict(collections.Counter(t['metric'] for t in keep)),parent_run=str(src),oversized=sum(t.get('oversized',False) for t in keep))
manifest['frozen_files']={f:sha(dst/f) for f in manifest['frozen_files'] if (dst/f).exists() and not f.startswith('__pycache__/')}
wr(dst/'manifest.json',manifest)
scope={'user_scope':'只重评复现修正影响且尚未用正确产物评测的项目；没问题的不重评。','excluded_system':'ours (all existing valid metrics preserved)','baseline_metrics':sorted(metrics),'preserved_current_metrics':['entity_correctness','entity_evidence','assertion_evidence','full_assertion_correctness','48_probe_coverage','structure','construction_resources'],'granularity':'Only 24 previous technical failures, preserving 776 valid judgments','comparison_note':'Our historical type/description/identity/QA results are preserved with original rubric and decided denominator. New source-explicit evaluator differs; do not claim these are a single homogeneous newly calibrated comparison. Evaluator repairs are tracked separately from reproduction corrections.','tasks_by_system':dict(collections.Counter(key[t['id']]['system'] for t in keep)),'tasks':len(keep),'pilot':len(rd(dst/'pilot.json')),'development':len(dev),'old_overscoped_tasks':len(tasks),'removed_tasks':len(tasks)-len(keep)}
wr(dst/'SCOPE.json',scope)
(dst/'PROTOCOL.md').write_text('# 基线复现修正补测\n\n以 SCOPE.json 为本轮范围依据；替代父运行的四方法全量计划。只重评 GraphRAG、AutoSchemaKG、KGGen 的类型、实体描述、别名、拆分和 Book QA 中有原生字段/候选的项目。我们的方法全部既有有效结果保留，已在修正产物上完成的实体、引用、断言和覆盖也保留。粒度只补24条技术失败。\n\n新裁判使用逐项证据核验，和历史旧裁判的上下文、提示及分母不同。保留旧值但不假称同一评测版本，差异另行标明。本轮不为统一版本额外重评我们的方法。\n\nMiniMax-M3，全部调用与重试共用最多6个HTTP请求槽。开发检查及相关真实样本检查通过后开始。新指标的原生输出及样本保持冻结；不重构图，不按分数重试。完整规则保留在父运行 PROTOCOL.md 与本轮 evaluate.py。\n')
# Narrow report wording only; judge prompts and input data are unchanged.
p=dst/'evaluate.py';text=p.read_text();text=text.replace('# 收敛指标统一重评','# 基线复现修正补测').replace('最新完整断言正确率保持原结果，本轮只重评其他指标。','只补测修正后基线尚未更新的指标；我们的方法及已经使用正确产物评测的结果保留。');p.write_text(text)
manifest['frozen_files']['SCOPE.json']=sha(dst/'SCOPE.json')
for name in ['PROTOCOL.md','evaluate.py']:manifest['frozen_files'][name]=sha(dst/name)
wr(dst/'manifest.json',manifest)
print(json.dumps(scope,ensure_ascii=False))
