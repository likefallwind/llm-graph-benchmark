"""Strict concept transport and syntax-only judgment recovery, no semantic relabeling."""
import json
import re

from common import parallel, digest, write


def validate_concept_response(response):
    content=response['choices'][0]['message']['content']
    if not isinstance(content,str):raise ValueError('Concept answer must be text')
    terms=[term.strip() for term in content.split(',')]
    if not terms or any(not any(char.isalnum() for char in term) for term in terms):
        raise ValueError('Concept answer contains empty or punctuation-only terms')
    return response


def strict_concept_batch(transport,messages,return_text_only=True,**kwargs):
    """Preserve upstream prompts/order/answer splitting, but propagate all failures."""
    if not messages:return []
    batch=messages if isinstance(messages[0],list) else [messages]
    def invoke(item):
        index,message=item
        response=transport.complete(message,8192,cache=True,validator=validate_concept_response)
        content=response['choices'][0]['message']['content']
        value=content if return_text_only else (content,response.get('usage',{}))
        return index,value
    results=dict(parallel(invoke,enumerate(batch)))
    return [results[index] for index in range(len(batch))]


def repair_reason_quotes(content):
    """Escape only unescaped quotes/control characters in the LAST reason string.

    All JSON outside that value must already parse. Semantic keys/values remain byte
    identical; ambiguous field-like suffixes and other malformed fields are rejected.
    """
    text=re.sub(r'<think>.*?</think>','',content,flags=re.S).strip()
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text).strip()
    try:json.loads(text);return text
    except json.JSONDecodeError:pass
    starts=list(re.finditer(r'"reason"\s*:\s*"',text))
    end=re.search(r'"\s*}\s*$',text)
    if len(starts)!=1 or not end:raise ValueError('Unsupported judgment syntax error')
    start=starts[0].end();stop=end.start()
    if start>stop:raise ValueError('Invalid reason bounds')
    # Prove every field outside the reason remains a valid JSON object.
    shell=json.loads(text[:start]+text[stop:])
    if not isinstance(shell,dict) or shell.get('reason')!='':raise ValueError('Invalid reason shell')
    body=text[start:stop]
    if re.search(r'"\s*,\s*"[^"\n]+"\s*:',body):
        raise ValueError('Ambiguous JSON fields inside malformed reason')
    fixed=[];slashes=0
    for char in body:
        if char=='"' and slashes%2==0:fixed.append('\\"')
        elif ord(char)<32:fixed.append(json.dumps(char)[1:-1])
        else:fixed.append(char)
        slashes=slashes+1 if char=='\\' else 0
    repaired=text[:start]+''.join(fixed)+text[stop:]
    value=json.loads(repaired)
    if {k:v for k,v in value.items() if k!='reason'}!={k:v for k,v in shell.items() if k!='reason'}:
        raise ValueError('Repair changed semantic fields')
    return repaired


def parse_quality(judge,content,task,audit):
    try:return judge.parse_verdict(content,task)
    except json.JSONDecodeError:
        repaired=repair_reason_quotes(content)
        verdict=judge.parse_verdict(repaired,task)
        write(audit/(digest(content)+'.json'),dict(rule='escape only last reason string',
              original=content,repaired=repaired,task_id=task['task_id']))
        return verdict
