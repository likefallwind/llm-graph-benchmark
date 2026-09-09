from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import pytest
from llm_graph_benchmark.quality import prepare_quality_tasks
from llm_graph_benchmark.cli import main

ROOT=Path(__file__).parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
calibration=module('v2_checks','studies/d2l-quality-v2-20260908/calibration.py')
judge=module('v2_runner','studies/d2l-quality-protocol-20260907/judge.py')


def inputs():
    task=dict(task_id='old',kind='assertion_grounding',content=dict(subject='A',predicate='支持',object='B',text='A支持B'),source_evidence=[{'text':'A支持B和C'}])
    key=dict(task_id='old',kind='assertion_grounding',system_id='hidden',document_id='d',item_id='i',submission_hash='s')
    return task,key


def test_versions_preserve_inputs_and_retrieval_identity():
    task,key=inputs();snapshot=copy.deepcopy((task,key))
    old=prepare_quality_tasks([task],[key]);new=prepare_quality_tasks([task],[key],version='v2')
    assert old.tasks[0]['task_id']!=new.tasks[0]['task_id']
    assert new.tasks[0]['kind']=='assertion_quality_v2'
    assert new.tasks[0]['content']==old.tasks[0]['content']
    assert new.tasks[0]['source_evidence']==old.tasks[0]['source_evidence']
    assert 'hidden' not in json.dumps(new.tasks)
    assert (task,key)==snapshot
    task.update(kind='fact_recovery',content=dict(source_fact='A',candidate_graph_assertions=[]))
    key.update(kind='fact_recovery',retriever='bm25',retriever_params={'top_k':10})
    assert prepare_quality_tasks([task],[key])==prepare_quality_tasks([task],[key],version='v2')
    with pytest.raises(ValueError,match='version'): prepare_quality_tasks([task],[key],version='v3')


def test_v2_cli_requires_explicit_version_and_separates_cache(tmp_path):
    task,key=inputs()
    for name,row in [('t',task),('k',key)]: (tmp_path/name).write_text(json.dumps(row)+'\n')
    args=['quality-tasks','--tasks',str(tmp_path/'t'),'--key',str(tmp_path/'k'),'--version','v2',
          '--tasks-out',str(tmp_path/'new-t'),'--key-out',str(tmp_path/'new-k')]
    assert main(args)==0
    assert json.loads((tmp_path/'new-t').read_text())['kind']=='assertion_quality_v2'
    assert main(args)==2


def test_check_gate_never_treats_errors_missing_or_wrong_judge_as_pass():
    keys=[{'task_id':str(i),'expected_label':label,'category':'test'} for i,label in enumerate(['pass','fail','uncertain'])]
    rows=[{'task_id':k['task_id'],'judge_id':'j','label':k['expected_label']} for k in keys]
    report=calibration.assess(keys,rows,'j')
    assert report['rule_check_gate']=='pass' and not report['formal_rerun_ready']
    assert calibration.assess(keys,rows,'other')['missing']==3
    assert calibration.assess(keys,rows[:-1],'j')['rule_check_gate']=='not_passed'
    rows[1]['label']='error'
    assert calibration.assess(keys,rows,'j')['status']=='incomplete'
    rows[1]['label']='pass'
    assert calibration.assess(keys,rows,'j')['rule_check_gate']=='not_passed'
    with pytest.raises(ValueError,match='duplicate'): calibration.assess(keys,rows+rows[:1],'j')


def test_assertion_only_runner_two_systems_skips_inapplicable_paired_tests(tmp_path,monkeypatch):
    import argparse
    tasks=[];keys=[]
    for system in ['a','b']:
        t,k=inputs();t['task_id']=k['task_id']=system;k['system_id']=system
        tasks.append(t);keys.append(k)
    output=prepare_quality_tasks(tasks,keys,version='v2')
    for name,rows in [('tasks',output.tasks),('key',output.key)]:
        (tmp_path/name).write_text(''.join(json.dumps(x)+'\n' for x in rows))
    args=argparse.Namespace(tasks=tmp_path/'tasks',key=tmp_path/'key',out=tmp_path/'out',workers=4,retries=1,
        max_tokens=8192,model='MiniMax-M3',judge_id='quality-v2-test',seed=1,timeout=1)
    monkeypatch.setenv('MINIMAX_API_KEY','dummy')
    calls=[]
    def call(*args):
        calls.append(1);return {'label':'pass','reason':'fixture'}
    monkeypatch.setattr(judge,'call',call)
    assert judge.run(args)==0
    assert json.loads((args.out/'paired-comparisons.json').read_text())==[]
    assert judge.run(args)==0 and len(calls)==2


def test_v21_keeps_v2_and_v1_reproducible_and_separates_new_labels():
    task,key=inputs()
    snapshots={v:prepare_quality_tasks([task],[key],version=v) for v in ('v1','v2')}
    new=prepare_quality_tasks([task],[key],version='v2.1')
    assert new.tasks[0]['kind']=='assertion_quality_v2_1'
    assert len({new.tasks[0]['task_id'],*(o.tasks[0]['task_id'] for o in snapshots.values())})==3
    for version,old in snapshots.items():
        assert prepare_quality_tasks([task],[key],version=version)==old
    assert new.tasks[0]['content']==snapshots['v2'].tasks[0]['content']
    assert new.tasks[0]['source_evidence']==snapshots['v2'].tasks[0]['source_evidence']


def test_v22_verdict_checks_actual_predicate_and_derives_joint_quality():
    task,key=inputs();task=prepare_quality_tasks([task],[key],version='v2.2').tasks[0]
    triple={k:task['content'][k] for k in ('subject','predicate','object')}
    row=dict(evaluated_triple=triple,edge_label='fail',description_label='pass',condition_label='pass',label='fail',reason='edge not supported')
    assert judge.parse_verdict(json.dumps(row),task)['label']=='fail'
    row['label']='pass'
    with pytest.raises(ValueError,match='inconsistent'):judge.parse_verdict(json.dumps(row),task)
    row['label']='fail';row['evaluated_triple']=dict(triple,predicate='misread predicate')
    with pytest.raises(ValueError,match='immutable'):judge.parse_verdict(json.dumps(row),task)
    row['evaluated_triple']=triple;del row['condition_label']
    with pytest.raises(ValueError,match='axis'):judge.parse_verdict(json.dumps(row),task)
