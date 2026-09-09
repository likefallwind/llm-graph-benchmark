import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('analysis',Path(__file__).parents[1]/'studies/d2l-quality-v22-20260908/analyze.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)

def test_review_keeps_disagreement_and_uncertain_in_denominator():
    ref=[dict(task_id=str(i),label=l,reason='local') for i,l in enumerate(['pass','fail','uncertain','pass'])]
    got=[dict(task_id=str(i),label=l,reason='model') for i,l in enumerate(['fail','pass','uncertain','pass'])]
    report=analysis.compare_review(ref,got)
    assert report['count']==4 and report['matched']==2 and report['agreement']==.5
    assert report['minimax_pass_codex_fail']==1 and report['minimax_fail_codex_pass']==1
    assert len(report['disagreements'])==2
    assert report['transitions']['uncertain->uncertain']==1

def test_review_rejects_missing_error_and_duplicate_votes():
    ref=[dict(task_id='a',label='pass',reason='ref')]
    with pytest.raises(ValueError,match='incomplete'):analysis.compare_review(ref,[])
    with pytest.raises(ValueError,match='incomplete'):analysis.compare_review(ref,[dict(task_id='a',label='error')])
    good=[dict(task_id='a',label='pass',reason='ok')]
    with pytest.raises(ValueError,match='duplicate API'):analysis.compare_review(ref,good*2)
    with pytest.raises(ValueError,match='duplicate review'):analysis.compare_review(ref*2,good)


def test_audit_requires_successful_same_model_response(tmp_path):
    import json
    response=dict(model='MiniMax-M3',base_resp={'status_code':0},choices=[{'finish_reason':'stop'}])
    path=tmp_path/'r.json';path.write_text(json.dumps(response))
    row=dict(attempts=[{'status':'success','response_file':'r.json'}])
    assert analysis.audit_response(row,tmp_path,'MiniMax-M3')=='MiniMax-M3'
    with pytest.raises(ValueError,match='model'):analysis.audit_response(row,tmp_path,'other')
    response['base_resp']['status_code']=2062;path.write_text(json.dumps(response))
    with pytest.raises(ValueError,match='provider error'):analysis.audit_response(row,tmp_path,'MiniMax-M3')
    response['base_resp']['status_code']=0;response['choices'][0]['finish_reason']='length';path.write_text(json.dumps(response))
    with pytest.raises(ValueError,match='truncated'):analysis.audit_response(row,tmp_path,'MiniMax-M3')


def test_audit_rejects_missing_success_or_response_path_escape(tmp_path):
    with pytest.raises(ValueError,match='successful'):analysis.audit_response({'attempts':[]},tmp_path,'m')
    row=dict(attempts=[{'status':'success','response_file':'../other.json'}])
    with pytest.raises(ValueError,match='outside'):analysis.audit_response(row,tmp_path,'m')


def test_local_recovery_uses_first_valid_response_and_retains_history(tmp_path):
    import json
    judge_spec=importlib.util.spec_from_file_location('frozen_test_judge',Path(__file__).parents[1]/'studies/d2l-quality-protocol-20260907/judge.py')
    judge=importlib.util.module_from_spec(judge_spec);judge_spec.loader.exec_module(judge)
    task=dict(task_id='a',kind='assertion_quality_v2_2',content=dict(subject='甲',predicate='识别',object='词'))
    attempts=[]
    for i,label in enumerate(['fail','pass'],1):
        verdict=dict(evaluated_triple=task['content'],edge_label=label,description_label='pass',condition_label='pass',label=label,reason='占位')
        content=json.dumps(verdict,ensure_ascii=False).replace('占位','来源中 "示例"')
        path=tmp_path/f'{i}.json'
        path.write_text(json.dumps(dict(model='MiniMax-M3',choices=[dict(finish_reason='stop',message=dict(content=content))])))
        attempts.append(dict(attempt=i,status='error',response_file=path.name))
    row=dict(task_id='a',label='error',attempts=attempts)
    recovered=analysis.recover_failed_row(row,task,tmp_path,judge.parse_verdict)
    assert recovered['label']=='fail' and recovered['syntax_recovery']['original_attempt']==1
    assert recovered['attempts'][:-1]==attempts and row['label']=='error'
    assert recovered['attempts'][-1]['operation']=='local_syntax_recovery'
    assert 'usage' not in recovered['attempts'][-1]
    task['content']['predicate']='其他关系'
    with pytest.raises(ValueError,match='no safely recoverable'):
        analysis.recover_failed_row(row,task,tmp_path,judge.parse_verdict)
    with pytest.raises(ValueError,match='only failed'):
        analysis.recover_failed_row(recovered,task,tmp_path,judge.parse_verdict)
