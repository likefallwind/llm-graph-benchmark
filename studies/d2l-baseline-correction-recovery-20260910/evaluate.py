"""Frozen v2.2 quality and historical CaRB recall for corrected submissions."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util
import json
from pathlib import Path
import sys
import time

from common import BENCH, Client, checkpoint, freeze, read, sha, usage, write, parallel, benchmark_path, digest, validate_response
from recovery import parse_quality


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    return loaded


def run(run_dir,lock_root,prepare_only=False,sample_size=200,smoke=False):
    from llm_graph_benchmark.bundle import BenchmarkBundle, SubmissionBundle
    from llm_graph_benchmark.sampling import create_blind_sample
    from llm_graph_benchmark.quality import prepare_quality_tasks
    from llm_graph_benchmark.retrieval import retrieve_fact_probes
    from llm_graph_benchmark.probes import create_fact_probe_tasks
    from llm_graph_benchmark.validation import validate_submission
    from llm_graph_benchmark.metrics import submission_metrics

    out=run_dir/('evaluation-smoke' if smoke else 'evaluation');out.mkdir(parents=True,exist_ok=True)
    benchmark=BenchmarkBundle.load(benchmark_path())
    submission=SubmissionBundle.load(run_dir/'submission.json')
    validation=validate_submission(submission,benchmark)
    if not validation.ok:raise ValueError('invalid submission')
    # Native schema and event participation are kept in the full artifact. Sample actual
    # extracted relations, consistently with the previous AutoSchemaKG semantic track.
    if submission.payload['system']['id'].startswith('autoschemakg'):
        for document in submission.payload['documents']:
            document['assertions']=[a for a in document['assertions'] if a['predicate']!='is participated by']
        write(out/'semantic-submission.json',submission.payload)
        submission=SubmissionBundle.load(out/'semantic-submission.json')
    legacy=Path(__file__).parent/'frozen-evaluation'
    if not legacy.exists():
        legacy=BENCH/'studies/d2l-fullbook-open-baselines-20260826'
    sys.path.insert(0,str(legacy))
    carb=module('frozen_carb',legacy/'judge_carb.py')
    judge_path=legacy/'judge.py'
    if not judge_path.exists():judge_path=BENCH/'studies/d2l-quality-protocol-20260907/judge.py'
    judge=module('frozen_quality',judge_path)
    if (out/'inputs.json').exists():
        frozen=read(out/'inputs.json')
        if (frozen['submission_sha256']!=sha(run_dir/'submission.json') or
            frozen['quality_parser_sha256']!=sha(judge.__file__) or
            frozen['carb_parser_sha256']!=sha(carb.__file__) or
            frozen['scope']!=('integration-smoke' if smoke else 'full')):
            raise ValueError('Frozen evaluation inputs changed')
        quality_tasks=frozen['quality_tasks'];fact_tasks=frozen['fact_tasks']
    else:
        sample=create_blind_sample(benchmark,[submission],entities_per_document=30,
                                  assertions_per_document=sample_size,seed=20260820)
        quality=prepare_quality_tasks(sample.tasks,sample.key,version='v2.2')
        retrieval=retrieve_fact_probes(benchmark,[submission],top_k=10,k1=1.2,b=0.75)
        facts=create_fact_probe_tasks(benchmark,[submission],retrieval,probes_per_document=None,seed=20260820)
        quality_tasks=list(quality.tasks)[:1] if smoke else list(quality.tasks)
        fact_tasks=list(facts.tasks)[:1] if smoke else list(facts.tasks)
        freeze(out/'inputs.json',dict(submission_sha256=sha(run_dir/'submission.json'),
        scope='integration-smoke' if smoke else 'full',
        quality_tasks=quality_tasks,quality_key=list(quality.key),
        fact_tasks=fact_tasks,fact_key=list(facts.key),retrieval=retrieval,
        quality_parser_sha256=sha(judge.__file__),carb_parser_sha256=sha(carb.__file__),
        recall_note='Historical covered only; unsupported counts are not a precision metric.'))
    write(out/'structural-metrics.json',submission_metrics(submission))
    if prepare_only:return
    client=Client(out,lock_root)
    historical={}
    for request in (out/'requests').glob('*/request.json'):
        key=digest(read(request))
        for attempt in request.parent.glob('attempt-*.json'):
            record=read(attempt)
            if record.get('status')=='done' and record.get('raw_body'):
                historical.setdefault(key,[]).append((record['started_at'],attempt,record['raw_body']))
    for candidates in historical.values():candidates.sort(key=lambda row:row[0])
    tasks=[('quality',task) for task in quality_tasks]+[('recall',task) for task in fact_tasks]
    def score(kind,task):
        def invoke():
            if kind=='quality':
                messages=judge.request_body(task,'MiniMax-M3',8192)['messages']
            else:
                messages=[{'role':'system','content':carb.SYSTEM_PROMPT},
                          {'role':'user','content':carb.build_prompt(task)}]
            def parse(response):
                content=response['choices'][0]['message']['content']
                return (parse_quality(judge,content,task,out/'syntax-repairs') if kind=='quality' else
                        carb.parse_verdict(content,len(task['content']['candidate_graph_assertions'])))
            payload=dict(model='MiniMax-M3',messages=messages,temperature=0.0,max_tokens=8192,stream=False)
            # Earliest valid historical response; never choose by its semantic label.
            for stamp,path,body in historical.get(digest(payload),[]):
                try:verdict=parse(validate_response(json.loads(body)))
                except (ValueError,KeyError,TypeError):continue
                write(out/'historical-recovery'/(task['task_id']+'.json'),dict(source=str(path),sha256=sha(path)))
                break
            else:
                response=client.complete(messages,validator=parse)
                verdict=parse(response)
            return dict(task_id=task['task_id'],kind=kind,**verdict)
        return checkpoint(out/'results'/(task['task_id']+'.json'),dict(kind=kind,task=task),invoke)
    results=[]
    for result in parallel(lambda x:score(*x),tasks):
        results.append(result)
        write(out/'progress.json',dict(status='running',scored=len(results),total=len(tasks)))
    q=Counter(x['label'] for x in results if x['kind']=='quality')
    f=Counter(x['covered'] for x in results if x['kind']=='recall')
    (out/'judgments.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in sorted(results,key=lambda r:r['task_id'])))
    summary=dict(status='complete',scope='integration-smoke' if smoke else 'full',
                 system=submission.payload['system'],quality=dict(q),recall=dict(f),
                 quality_total=len(quality_tasks),recall_total=len(fact_tasks),usage=usage(out))
    write(out/'summary.json',summary)
    (out/'.finished').write_text(str(time.time())+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--lock-root',type=Path,required=True);p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--sample-size',type=int,default=200);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    run(a.run,a.lock_root,a.prepare_only,a.sample_size,a.smoke)
