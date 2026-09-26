"""Explicit OpenAI-compatible Gateway transport profile; no judge changes."""
from pathlib import Path
from llm_graph_benchmark.workflow import transport,engine
ENDPOINT='http://127.0.0.1:8111/v1/chat/completions'
MODEL='minimax-m3'
SLOTS=Path('/home/likefallwind/code/llm-graph-benchmark/outputs/rl-baselines-20260923/gateway-request-slots')

def load_secret():
    for line in Path('/home/likefallwind/code/apigateway/.env').read_text().splitlines():
        if line.strip().startswith('GATEWAY_KEYS='):
            value=line.split('=',1)[1].strip().strip('\"\'').split(',')[0].strip()
            if value:return value
    raise RuntimeError('Gateway credential missing')

def validate_response(response):
    if not isinstance(response,dict):raise ValueError('Expected gateway object')
    if response.get('error'):raise ValueError('Gateway error response')
    base=response.get('base_resp')
    if base is not None:
        if not isinstance(base,dict) or 'status_code' not in base:raise ValueError('Invalid provider status')
        code=base['status_code']
        if code in transport.TERMINAL_CODES:raise transport.TerminalProviderError('Gateway provider code '+str(code))
        if code in transport.MODERATION_CODES:raise transport.ContentRejected({'provider_code':code})
        if code!=0:raise ValueError('Provider error')
    if str(response.get('model','')).lower()!=MODEL:raise ValueError('Unexpected gateway model')
    choices=response.get('choices')
    if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise ValueError('Non-stop gateway completion')
    content=choices[0].get('message',{}).get('content')
    if not isinstance(content,str) or not content.strip():raise ValueError('Empty gateway completion')
    return response

def install():
    # Explicit, frozen backend adapter. The original workflow parser/prompts stay identical.
    transport.ENDPOINT=ENDPOINT
    transport.MODEL=MODEL
    transport.load_secret=load_secret
    transport.validate_response=validate_response
    engine.slots_path=lambda:SLOTS

def unwrap_json_fence(response):
    """Remove only a whole JSON code fence; preserve all semantic fields."""
    import copy,json,re
    content=response['choices'][0]['message']['content']
    match=re.fullmatch(r'\s*```(?:json)?\s*\n?(.*?)\n?```\s*',content,flags=re.S)
    if not match:return response
    inner=match.group(1).strip()
    try:json.loads(inner)
    except ValueError:return response
    normalized=copy.deepcopy(response)
    normalized['choices'][0]['message']['content']=inner
    return normalized

class GatewayClient(transport.Client):
    def complete(self,messages,max_tokens=4096,validator=None):
        check=(lambda raw:validator(unwrap_json_fence(raw))) if validator else None
        raw=super().complete(messages,max_tokens=max_tokens,validator=check)
        return unwrap_json_fence(raw)
