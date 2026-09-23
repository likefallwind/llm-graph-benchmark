from pathlib import Path
import sys,json,shutil,time
r=Path('/home/likefallwind/code/llm-graph-benchmark');study=r/'studies/d2l-consolidated-reeval-20260922';sys.path.insert(0,str(study));import evaluate as e
src=r/'outputs/d2l-consolidated-m3-c6-20260922-v5';dst=r/'outputs/d2l-consolidated-m3-c6-20260922-v6';assert not dst.exists();shutil.copytree(src,dst,ignore=shutil.ignore_patterns('.check.*','.pilot.*','check-launch.json','pilot-launch.json','check.log','pilot.log','request-slots','.run.lock','progress.json','development-report.json','summary.json','REPORT.md'))
shutil.copy2(study/'evaluate.py',dst/'evaluate.py')
archived=[];preserved={}
for f in (dst/'results').glob('*.json'):
 if e.rd(f).get('metric') in {'identity_split','alias_identity'}:
  target=dst/'prior-identity-judgments'/f.name;target.parent.mkdir(exist_ok=True);f.replace(target);archived.append(f.name)
 else:preserved[f.name]=e.sha(f)
if (dst/'source-shards').exists():(dst/'source-shards').rename(dst/'prior-identity-source-shards')
dev=e.rd(dst/'development.json')
def add(id,metric,target,source,expected):
 dev.append({'id':id,'metric':metric,'expected':expected,'payload':{'metric':metric,'target':target,'segments':[{'id':'s0','text':json.dumps(target,ensure_ascii=False)}],'sources':[{'id':'P0','text':source}],'candidate_context':{}}})
add('dev-split-abstraction','identity_split',{'left':{'name':'模型（抽象概念）'},'right':{'name':'tf.keras.Model（具体框架类）'}},'模型是抽象数学概念；tf.keras.Model是TensorFlow库中的具体基类，它提供模型构建接口。本文区分抽象概念和具体代码类。','correct')
add('dev-split-frameworks','identity_split',{'left':{'name':'A.nn.LSTM'},'right':{'name':'B.nn.LSTM'}},'A.nn.LSTM和B.nn.LSTM分别是不同框架的两个类。它们实现同一种数学模型，但不是同一个类。','correct')
add('dev-split-occurrences','identity_split',{'left':{'name':'2020年会议开幕'},'right':{'name':'2021年会议开幕'}},'该会议在2020年和2021年分别举行，两次开幕属于不同的事件发生实例。','correct')
add('dev-alias-abstraction','alias_identity',{'name':'模型（抽象概念）','alias':'tf.keras.Model（具体类）'},'模型是抽象数学概念，tf.keras.Model是具体框架基类；这里两者有实现关系，但并非同一个对象。','incorrect')
e.wr(dst/'development.json',dev);e.wr(dst/'identity-revision.json',{'parent_run':str(src),'all_affected_metrics':['alias_identity','identity_split'],'all_affected_tasks':sum(t['metric'] in {'alias_identity','identity_split'} for t in e.rd(dst/'tasks.json')),'archived_judgments':archived,'preserved_unaffected_results_sha256':preserved,'reason':'Uniformly distinguish referential identity from implementation, type-instance or framework similarity; do not turn a node citation error into proof of a duplicate. Keep event-instance distinctions. Entire affected dimensions are reassessed under the clarified rule, not selected labels.'})
protocol=(dst/'PROTOCOL.md').read_text()+'\n身份规则v6：增加相同功能不等于同一对象、明确框架与概念/实现层级、单节点引用错误不自动证明重复、事件实例差异四条明确要求。别名与拆分共573项全部用相同新增规则；先前13项真实身份小样本及原开发身份判断作为旧版保留，不混入新评分。其他维度提示和输入不变，有效标签保留。增加4个明确的身份开发题。\n';(dst/'PROTOCOL.md').write_text(protocol)
shutil.copy2(Path(__file__),dst/'prepare_identity_revision.py');m=e.rd(src/'manifest.json');m['protocol']='consolidated-reeval-v6';m['frozen_files']={str(f.relative_to(dst)):e.sha(f) for f in dst.rglob('*') if f.is_file() and f.name!='manifest.json' and not any(part in {'api','results','ledgers','source-shards','granularity-preserved','prior-granularity-failures','prior-development-failures','prior-pilot-failures','technical-retries','prior-identity-judgments','prior-identity-source-shards'} for part in f.relative_to(dst).parts)};e.wr(dst/'manifest.json',m)
print(json.dumps({'run':str(dst),'archived_identity_results':len(archived),'preserved_other_results':len(preserved),'development_cases':len(dev)}))
