import copy,json
import pytest
from gateway_adapter import validate_response,unwrap_json_fence

def response(content='{"label":"fail","reason":"x"}'):
    return {'model':'minimax-m3','choices':[{'finish_reason':'stop','message':{'content':content}}]}

def test_gateway_envelope_and_fence():
    raw=response('```json\n{"label":"fail","reason":"x"}\n```')
    original=copy.deepcopy(raw)
    validate_response(raw)
    assert json.loads(unwrap_json_fence(raw)['choices'][0]['message']['content'])=={'label':'fail','reason':'x'}
    assert raw==original

@pytest.mark.parametrize('mutation',[
    {'model':'other-model'}, {'error':{'message':'rejected'}},
    {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},
    {'base_resp':{'status_code':1234}},
])
def test_invalid_gateway_response_rejected(mutation):
    raw=response();raw.update(mutation)
    with pytest.raises(ValueError):validate_response(raw)

def test_no_prose_or_invalid_json_repair():
    for text in ['Here is ```json\n{}\n```', '```json\n{broken}\n```']:
        raw=response(text);assert unwrap_json_fence(raw)==raw
