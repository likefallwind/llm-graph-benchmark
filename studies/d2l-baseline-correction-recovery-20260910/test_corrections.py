import json
from concurrent.futures import ThreadPoolExecutor
import threading
import time

import pytest
from common import checkpoint, map_kggen_relations, openai_shape, parallel, read, request_slot, validate_response, TerminalProviderError


def test_concurrent_call_cap_including_separate_open_handles(tmp_path):
    active=peak=0
    lock=threading.Lock()
    def call(_):
        nonlocal active,peak
        with request_slot(tmp_path,6):
            with lock:
                active+=1;peak=max(peak,active)
            time.sleep(.025)
            with lock:active-=1
    with ThreadPoolExecutor(max_workers=30) as pool:
        list(pool.map(call,range(60)))
    assert 1 < peak <= 6
    assert active==0


def test_failed_checkpoint_retries_but_success_and_empty_output_are_frozen(tmp_path):
    calls=[]
    def call():
        calls.append(1)
        if len(calls)==1:raise ValueError('parse failure')
        return []
    path=tmp_path/'chunk.json'
    assert checkpoint(path,{'chunk':1},call)==[]
    assert checkpoint(path,{'chunk':1},call)==[]
    assert len(calls)==2
    assert len(list((tmp_path/'failures').glob('*.json')))==1
    with pytest.raises(ValueError,match='changed'):
        checkpoint(path,{'chunk':2},call)


def test_changed_predicate_carries_only_its_original_triples_evidence():
    raw=[dict(subject='A',predicate='uses',object='B',evidence_unit_ids=['P1']),
         dict(subject='A',predicate='contains',object='B',evidence_unit_ids=['P2'])]
    graph=dict(entities=['A','B'],edges=['employs','contains'],
               relations=[['A','employs','B'],['A','contains','B']],
               edge_clusters={'employs':['uses']})
    triples,lineage=map_kggen_relations(raw,graph)
    result={r['predicate']:r['evidence_unit_ids'] for r in triples}
    assert result=={'contains':['P2'],'employs':['P1']}
    assert len(lineage)==2


def test_lineage_rejects_unexplained_upstream_triples():
    with pytest.raises(ValueError,match='lineage'):
        map_kggen_relations([],dict(entities=['A','B'],edges=['r'],relations=[['A','r','B']]))


@pytest.mark.parametrize('mutation',[
    {'model':'another-model'}, {'base_resp':{'status_code':1008}},
    {'choices':[{'finish_reason':'length','message':{'content':'partial'}}]},
    {'choices':[{'finish_reason':'stop','message':{'content':''}}]},
])
def test_reject_wrong_model_provider_errors_and_truncation(mutation):
    value={'model':'MiniMax-M3','choices':[{'finish_reason':'stop','message':{'content':'[]'}}]}
    value.update(mutation)
    with pytest.raises((ValueError,TerminalProviderError)):validate_response(value)


def test_accept_valid_empty_extraction_response():
    value={'model':'MiniMax-M3','choices':[{'finish_reason':'stop','message':{'content':'[]'}}]}
    assert validate_response(value)==value


def test_minimax_envelope_adapter_does_not_change_answer_or_usage():
    raw=dict(model='MiniMax-M3',service_tier='standard',usage={'total_tokens':5},
             choices=[{'finish_reason':'stop','message':{'role':'assistant','content':'[]'}}])
    result=openai_shape(raw)
    assert 'service_tier' not in result
    assert result['choices']==raw['choices']
    assert result['usage']==raw['usage']
    assert raw['service_tier']=='standard'


def test_failure_does_not_launch_whole_corpus():
    calls=[]
    def invoke(i):
        calls.append(i)
        if i==0:raise RuntimeError('failure')
        time.sleep(.01)
        return i
    with pytest.raises(RuntimeError):list(parallel(invoke,range(1000)))
    assert len(calls)<=6
