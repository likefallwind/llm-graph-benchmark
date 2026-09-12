import json
from pathlib import Path
import time

import pytest
from common import TerminalProviderError
from recovery import validate_concept_response, strict_concept_batch, repair_reason_quotes, parse_quality


@pytest.mark.parametrize('content',['[',']','[]','{}','','概念, '])
def test_reject_fallback_and_empty_concept_terms(content):
    with pytest.raises(ValueError):
        validate_concept_response({'choices':[{'message':{'content':content}}]})


def test_strict_batch_preserves_order_and_record_shape():
    class Transport:
        def complete(self,message,*args,validator,**kwargs):
            time.sleep(.005 if message[0]['content']=='first' else 0)
            r={'choices':[{'message':{'content':message[0]['content']}}],'usage':{'total_tokens':2}}
            validator(r);return r
    result=strict_concept_batch(Transport(),[[{'content':'first'}],[{'content':'second'}]],return_text_only=False)
    assert result==[('first',{'total_tokens':2}),('second',{'total_tokens':2})]


def test_strict_batch_propagates_quota_failure_instead_of_fake_empty():
    class Transport:
        def complete(self,*args,**kwargs):raise TerminalProviderError('2067')
    with pytest.raises(TerminalProviderError):
        strict_concept_batch(Transport(),[[{'content':'x'}]],return_text_only=False)


def test_reason_quote_recovery_does_not_change_other_fields():
    text='{"label":"fail","edge_label":"fail","reason":"引用"编码器"支持原判定\\n第二行"}'
    repaired=json.loads(repair_reason_quotes(text))
    assert repaired=={'label':'fail','edge_label':'fail','reason':'引用"编码器"支持原判定\n第二行'}


@pytest.mark.parametrize('text',[
    '{"label":"fa"il","reason":"text"}',
    '{"label":"fail","reason":"引用"A"","label":"pass"}',
    '{"label":"pass","reason":"unterminated',
])
def test_reason_repair_rejects_non_reason_or_ambiguous_errors(text):
    with pytest.raises(ValueError):repair_reason_quotes(text)


def test_repaired_syntax_still_must_pass_original_semantic_validation(tmp_path):
    class Judge:
        def parse_verdict(self,content,task):
            row=json.loads(content)
            if row['label']!=row['edge_label']:raise ValueError('inconsistent axes')
            return row
    text='{"label":"pass","edge_label":"fail","reason":"引用"A""}'
    with pytest.raises(ValueError,match='inconsistent'):
        parse_quality(Judge(),text,{'task_id':'t'},tmp_path)
    assert not list(tmp_path.glob('*.json'))
