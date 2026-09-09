"""Freeze v2.1, new natural samples, and separately identified rule checks."""
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json,random
from pathlib import Path
from llm_graph_benchmark.quality import prepare_quality_tasks
from llm_graph_benchmark.bundle import BenchmarkBundle,SubmissionBundle
from llm_graph_benchmark.io import write_json,write_jsonl
from llm_graph_benchmark.sampling import _task_id


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def content(a,entities):
    return dict(subject=entities[a['subject_id']]['name'],predicate=a['predicate'],object=entities[a['object_id']]['name'],
                text=a['text'],scope=a.get('scope',''),polarity=a.get('polarity','positive'))
def signature(c): return hashlib.sha256(json.dumps(c,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def prepare(repo,out):
    if out.exists(): raise ValueError('fresh output required')
    previous=repo/'outputs/d2l-quality-v2-20260908'
    read=lambda p:[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    oldtasks=read(previous/'tasks.jsonl');oldkeys=read(previous/'key.jsonl');keys={x['task_id']:x for x in oldkeys}
    inputs={str(previous/'tasks.jsonl'):sha(previous/'tasks.jsonl'),str(previous/'key.jsonl'):sha(previous/'key.jsonl')}
    raw=[];rawkeys=[]
    for t in oldtasks:
        k=keys[t['task_id']];tid=k['source_task_id']
        raw.append(dict(t,task_id=tid,kind='assertion_grounding'))
        rawkeys.append(dict(k,task_id=tid,kind='assertion_grounding',previous_v2_task_id=t['task_id']))
    output=prepare_quality_tasks(raw,rawkeys,version='v2.1')
    spec=importlib.util.spec_from_file_location('oldchecks',repo/'studies/d2l-quality-v2-20260908/calibration.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    cases=copy.deepcopy(mod.cases())
    for c in cases:
        if c['category']=='ambiguous_reference':
            c['previous_expected_label']=c['expected_label'];c['expected_label']='fail'
    extras=[
      ('清单记载箱甲或箱乙装有试剂，但无法确定是哪一箱。','箱甲','装有','试剂','箱甲装有试剂。','fail'),
      ('清单记载箱甲或箱乙装有试剂，但无法确定是哪一箱。','箱甲或箱乙之一','装有','试剂','箱甲或箱乙之一装有试剂，具体哪箱未知。','pass'),
      ('文档只记录模块甲的名称，并未记载模块甲与模块乙的任何关系。','模块甲','依赖','模块乙','模块甲依赖模块乙。','fail'),
      ('日志明确记录程序甲先结束，程序乙随后开始。','程序甲结束','先于','程序乙开始','程序甲结束先于程序乙开始。','pass'),
      ('','模块甲','包含','模块乙','模块甲包含模块乙。','uncertain'),
      ('记录明确写道：实验甲测得温度为十五度。','实验甲','测得温度','十五度','实验甲测得温度为十五度。','pass'),
      ('记录明确写道：实验甲测得温度为十五度。','实验甲','测得温度','二十度','实验甲测得温度为二十度。','fail'),
      ('记录列出方案甲和方案乙，并明确表示尚未确定采用哪一个。','最终方案','尚未确定为','方案甲或方案乙','尚未确定最终采用方案甲还是方案乙。','pass')]
    for i,(src,s,p,o,text,label) in enumerate(extras):
        cases.append(dict(case_id=f'boundary-{i+1:02d}',category='new_support_boundary',source=src,
          content=dict(subject=s,predicate=p,object=o,text=text,scope='',polarity='positive'),expected_label=label))
    ct=[];ck=[]
    for c in cases:
        ct.append(dict(task_id=c['case_id'],kind='assertion_grounding',content=c['content'],source_evidence=[{'text':c['source']}] if c['source'] else []))
        ck.append(dict(task_id=c['case_id'],kind='assertion_grounding',system_id='synthetic-rule-checks',document_id='authored',item_id=c['case_id'],submission_hash=signature(c),
            expected_label=c['expected_label'],category=c['category'],previous_expected_label=c.get('previous_expected_label')))
    checks=prepare_quality_tasks(ct,ck,version='v2.1')
    # New natural assertions are sampled after freezing the rubric, before reading their content or API labels.
    benchmark_path=repo/'outputs/d2l-full1105-vnext-20260826/benchmark.json'
    bench=BenchmarkBundle.load(benchmark_path);inputs[str(benchmark_path)]=sha(benchmark_path)
    for name in ('documents_file','fact_probes_file','rubric_file'):
        p=benchmark_path.parent/bench.manifest[name];inputs[str(p)]=sha(p)
    base=repo/'outputs/d2l-fullbook-open-baselines-20260826/runs'
    paths=[repo/'outputs/d2l-full1105-vnext-20260826/submission.json']+[base/x/y for x,y in [
      ('kggen-minimax-m3-official-full1105','submission.json'),('kggen-minimax-m3-official-full1105-exactdedup','submission.json'),
      ('graphrag-fast-full1105','submission.json'),('autoschemakg-minimax-m3-official-full1105','submission-semantic.json')]]
    excluded={(k['system_id'],k['document_id'],k['item_id']) for k in oldkeys}
    seen_texts={signature(t['content']) for t in oldtasks}
    ht=[];hk=[];population={}
    for path in paths:
        sub=SubmissionBundle.load(path);inputs[str(path)]=sha(path)
        sid=sub.system_id
        candidates=[]
        for doc in sub.payload['documents']:
            did=doc['document_id'];entities={e['id']:e for e in doc['entities']}
            for a in doc['assertions']:
                c=content(a,entities)
                if (sid,did,a['id']) not in excluded and signature(c) not in seen_texts:
                    candidates.append((did,a,c))
        candidates.sort(key=lambda x:(x[0],x[1]['id']))
        population[sid]=len(candidates)
        for did,a,c in random.Random('v21-natural-20260908:'+sid).sample(candidates,5):
            tid=_task_id(20260908,sub.submission_hash,'assertion_grounding',did,a['id'])
            ht.append(dict(task_id=tid,kind='assertion_grounding',content=c,
                 source_evidence=[dict(unit=bench.unit_by_document[did][ref['unit_id']],submitted_ref=ref) for ref in a.get('evidence',[])]))
            hk.append(dict(task_id=tid,kind='assertion_grounding',system_id=sid,document_id=did,item_id=a['id'],submission_hash=sub.submission_hash,
                 selection_population=len(candidates),selection_probability=5/len(candidates)))
    if len(population)!=5: raise ValueError('system ID collision')
    holdout=prepare_quality_tasks(ht,hk,version='v2.1')
    out.mkdir(parents=True)
    for name,rows in [('tasks',output.tasks),('key',output.key),('checks-tasks',checks.tasks),('checks-key',checks.key),('natural-tasks',holdout.tasks),('natural-key',holdout.key)]:
        write_jsonl(out/(name+'.jsonl'),rows)
    manifest=dict(status='frozen-before-new-judgments',version='v2.1',assertion_tasks=len(output.tasks),rule_checks=len(checks.tasks),natural_pilot=len(holdout.tasks),
       natural_population=population,rubric_sha256=output.tasks[0]['rubric_sha256'],inputs_sha256=inputs,
       rule_change='Readable source without support is fail; absent/unreadable evidence is uncertain. Prior v2 case26 expectation retained in original artifact, revised only in v2.1.',
       gate='Require 34/34 rule checks. Freeze separate Codex natural-pilot labels before viewing MiniMax labels, then report agreement and disagreements; descriptive full rerun, not a human-calibrated confirmatory claim.',
       reviewer_limit='Codex also authored the rubric; separate model judgment is not independent protocol design or human gold. 5/system is a pilot, not precise calibration.',
       full_scoring='1000 frozen assertions, all systems same official MiniMax-M3 settings; auxiliary recovery v1 unchanged.',
       artifacts_sha256={p.name:sha(p) for p in out.glob('*.jsonl')})
    write_json(out/'manifest.json',manifest);print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();prepare(a.repo,a.out)
