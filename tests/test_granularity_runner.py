import importlib.util
import json
from pathlib import Path
import pytest

p=Path(__file__).resolve().parents[1]/'studies/d2l-granularity-20260922/evaluate.py'
spec=importlib.util.spec_from_file_location('granularity_study',p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_public_input_isolation():
    old={'id':'x','payload':{'target':{'subject':'A','predicate':'related_to','object':'B',
        'description':'A抑制B','system':'SECRET_METHOD'},'submitted_sources':['SECRET_SOURCE'],
        'reference_context':['SECRET_CONTEXT']},'expected':'SECRET_LABEL'}
    req=json.dumps(m.messages(m.public_task(old),m.PROMPT),ensure_ascii=False)
    assert 'A抑制B' in req
    assert 'SECRET_' not in req
    assert '"id"' not in req

def test_strata_preserve_uncertain_and_missing():
    tasks=[{'id':str(i)} for i in range(5)]
    labels=[('done','correct'),('done','incorrect'),('done','uncertain'),('failed',None),('done','correct')]
    key={str(i):{'historical_correctness':{'status':s,'value':{'label':l}}} for i,(s,l) in enumerate(labels)}
    results={str(i):{'status':'done','value':{'label':'L3'}} for i in range(4)}
    g=m.group_metrics(tasks,key,results); d=g['layers']['L3']
    assert g['unassessed']==1 and d['fraction_all']==.8
    assert d['correct_rate_layer_all']==.25 and d['correct_rate_decided']==.5
    assert d['uncertain']==d['unassessed']==1
    assert g['layers']['L1']['correct_rate_decided'] is None
    assert g['layers']['L1']['wilson_decided'] is None

@pytest.mark.parametrize('v',[dict(label='L4',reason='x'),dict(label='L1',reason=''),
    dict(label='L1',reason='x',system='ours'),['L1']])
def test_invalid_response_rejected(v):
    with pytest.raises(ValueError):
        m.parse({'choices':[{'message':{'content':json.dumps(v)}}]})

def test_specific_false_claim_stays_specific():
    cases={t['id']:t for t in m.checks()}
    assert cases['dev_false-specific']['expected']=='L3'
    assert cases['dev_specific-description']['expected']=='L3'
    assert cases['dev_unrelated-detail']['expected']=='L1'

