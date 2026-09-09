"""Freeze v2.2 using only previously authorized 1000 assertions and authored checks."""
import argparse,json,hashlib,random
from collections import defaultdict
from pathlib import Path
from llm_graph_benchmark.quality import prepare_quality_tasks
from llm_graph_benchmark.io import write_json,write_jsonl

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(repo,out):
    if out.exists():raise ValueError('fresh directory required')
    old=repo/'outputs/d2l-quality-v21-20260908'
    read=lambda p:[json.loads(x) for x in p.read_text().splitlines()]
    migrated={};hashes={}
    for prefix in ('','checks-'):
        tasks=read(old/(prefix+'tasks.jsonl'));keys=read(old/(prefix+'key.jsonl'));bykey={k['task_id']:k for k in keys}
        raw=[];rk=[]
        for t in tasks:
            k=bykey[t['task_id']];tid=k['source_task_id']
            raw.append(dict(t,task_id=tid,kind='assertion_grounding'))
            rk.append(dict(k,task_id=tid,kind='assertion_grounding',previous_v21_task_id=t['task_id']))
        legacy=prepare_quality_tasks(raw,rk,version='v2.1')
        if {t['task_id']:t for t in legacy.tasks}!={t['task_id']:t for t in tasks}:raise ValueError('previous version changed')
        migrated[prefix]=prepare_quality_tasks(raw,rk,version='v2.2')
        for name in ('tasks','key'):hashes[str(old/(prefix+name+'.jsonl'))]=sha(old/(prefix+name+'.jsonl'))
    # Blind review panel chosen only by IDs, excluding prior 95 development-review items and displayed examples.
    exclude={k['task_id'] for k in read(repo/'outputs/d2l-quality-v2-20260908/review-key.jsonl')}
    examples={'q_fdd99242f9f5014d85484247','q_dacf6e767d57b2ce45b68d2a','q_1fe0e22efb722b24b882d03e','q_60b73c2bf4781837dd51583d','q_409b5b2685836532d87335e3','q_bf4a68b34ed705abf19f9db0','q_20e724ee358eea1cc1236cdc','q_2c7c526fcee035581113b6ca'}
    groups=defaultdict(list)
    for k in migrated[''].key:
        if k['previous_v2_task_id'] not in exclude and k.get('previous_task_id') not in examples:groups[k['system_id']].append(k)
    selected=[]
    for system,rows in sorted(groups.items()):
        # Sort on previous IDs to preserve the already selected v2.1 blind panel.
        selected+=random.Random('v21-blind-existing:'+system).sample(sorted(rows,key=lambda x:x['previous_v21_task_id']),5)
    selected.sort(key=lambda x:x['previous_v21_task_id'])
    tasks={t['task_id']:t for t in migrated[''].tasks}
    out.mkdir(parents=True)
    for prefix,output in migrated.items():
        write_jsonl(out/(prefix+'tasks.jsonl'),output.tasks);write_jsonl(out/(prefix+'key.jsonl'),output.key)
    write_jsonl(out/'review-tasks.jsonl',[tasks[k['task_id']] for k in selected]);write_jsonl(out/'review-key.jsonl',selected)
    manifest=dict(version='v2.2',status='frozen-before-api-judgments',assertions=1000,checks=34,blind_review=25,
       rubric_sha256=migrated[''].tasks[0]['rubric_sha256'],inputs_sha256=hashes,
       changes='Exact input triple echo checked by code; three semantic axes and deterministic joint label; v2.1 support boundary unchanged.',
       checks_gate='34/34 expected labels; if gate fails, do not silently modify successful judgments or declare calibration passed.',
       review_design='5/system from previously authorized 1000; exclude 95 development-review items and displayed examples. Codex labels before viewing MiniMax output. Same corpus; not human gold or independent protocol design.',
       data_scope='Only already-authorized 1000 historical assertions plus synthetic checks sent to official MiniMax. Newly drawn 25 natural assertions in v2.1 remain local and are not sent.',
       completion='Complete all 1000 same-model judgments and report pilot agreement/disagreements. Publish descriptive measured results with calibration limits; do not claim a new standard or SOTA.',
       artifacts_sha256={p.name:sha(p) for p in out.glob('*.jsonl')})
    write_json(out/'manifest.json',manifest);print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.repo,a.out)
