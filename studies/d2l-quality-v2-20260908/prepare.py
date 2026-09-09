"""Freeze unchanged historical samples under assertion-quality v2, offline."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import random

from calibration import cases
from llm_graph_benchmark.io import write_json,write_jsonl
from llm_graph_benchmark.quality import prepare_quality_tasks


def prepare(previous, out):
    if out.exists(): raise ValueError('use a fresh output directory')
    inputs={}
    def read(name):
        p=previous/name
        inputs[name]=hashlib.sha256(p.read_bytes()).hexdigest()
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    old_tasks=read('tasks.jsonl'); old_keys=read('key.jsonl'); old_judgments=read('judgments.jsonl')
    by_key={r['task_id']:r for r in old_keys}
    if len(by_key)!=len(old_keys) or {x['task_id'] for x in old_tasks}!=set(by_key):
        raise ValueError('invalid previous task/key identity')
    tasks,keys,old_ids=[],[],{}
    for t in old_tasks:
        if t['kind']!='assertion_quality_v1': continue
        key=by_key[t['task_id']]; original=key['source_task_id']
        old_ids[original]=t['task_id']
        tasks.append(dict(t,task_id=original,kind='assertion_grounding'))
        keys.append(dict(key,task_id=original,kind='assertion_grounding'))
    legacy=prepare_quality_tasks(tasks,keys)
    old_by_id={x['task_id']:x for x in old_tasks}
    if any(t!=old_by_id.get(t['task_id']) for t in legacy.tasks):
        raise ValueError('v1 content or identity changed; refuse migration')
    output=prepare_quality_tasks(tasks,keys,version='v2')
    counts=Counter(x['system_id'] for x in output.key)
    if len(counts)!=5 or set(counts.values())!={200}: raise ValueError('expected five frozen 200-assertion samples')
    new_keys=[dict(x,previous_task_id=old_ids[x['source_task_id']]) for x in output.key]
    c_tasks,c_keys=[],[]
    for c in cases():
        tid=c['case_id']
        c_tasks.append(dict(task_id=tid,kind='assertion_grounding',content=c['content'],
                            source_evidence=[{'text':c['source']}] if c['source'] else []))
        c_keys.append(dict(task_id=tid,kind='assertion_grounding',system_id='synthetic-rule-checks',
             document_id='authored-checks',submission_hash='sha256:'+hashlib.sha256(json.dumps(c,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
             item_id=tid,expected_label=c['expected_label'],category=c['category']))
    checks=prepare_quality_tasks(c_tasks,c_keys,version='v2')
    # Existing samples are development material, NOT an independent holdout.
    judgments={}
    for j in old_judgments:
        if j['task_id'] in judgments: raise ValueError('previous judgments must have unique task IDs')
        judgments[j['task_id']]=j
    groups=defaultdict(list)
    for key in new_keys:
        label=judgments.get(key['previous_task_id'],{}).get('label','missing')
        groups[key['system_id'],label].append(key)
    review=[]
    for (system,label),rows in sorted(groups.items()):
        rows=sorted(rows,key=lambda x:x['task_id'])
        seed=hashlib.sha256(f'20260908|{system}|{label}'.encode()).digest()
        selected=random.Random(seed).sample(rows,min(8,len(rows)))
        for key in selected:
            review.append(dict(key,previous_label=label,stratum_population=len(rows),stratum_sample=len(selected),
                 inclusion_probability=len(selected)/len(rows),inverse_probability_weight=len(rows)/len(selected)))
    selected_ids={k['task_id'] for k in review}
    out.mkdir(parents=True)
    for name,data in [('tasks',output.tasks),('key',new_keys),('checks-tasks',checks.tasks),('checks-key',checks.key),
                      ('review-tasks',[x for x in output.tasks if x['task_id'] in selected_ids]),('review-key',review)]:
        write_jsonl(out/(name+'.jsonl'),data)
    manifest=dict(status='prepared-not-judged',model_calls=0,assertion_tasks=len(output.tasks),
        counts=dict(counts),rule_checks=len(checks.tasks),development_review_tasks=len(review),
        previous_run=str(previous.resolve()),previous_inputs_sha256=inputs,
        assertion_rubric_sha256=output.tasks[0]['rubric_sha256'],
        auxiliary_recovery='Existing v1 tasks and judgments unchanged; not rescheduled or renamed.',
        review_design='Up to 8 per system x historical label; inverse-probability weights in private key. Development diagnostic only, not independent holdout.',
        expected_labels='Assistant-authored synthetic rule checks, not independent human gold. Never send private key to judge.',
        gate=dict(rule_checks='pending',independent_heldout_review='pending',formal_rerun_ready=False),
        baseline_scope=json.loads((previous/'manifest.json').read_text())['baseline_scope'])
    manifest['artifacts_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.jsonl')}
    write_json(out/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--previous',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.previous,args.out),ensure_ascii=False,indent=2))
