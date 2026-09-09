import json
import pytest
from llm_graph_benchmark.verdict_recovery import recover_reason_quotes


def verdict(label='pass'):
    return dict(evaluated_triple=dict(subject='甲', predicate='识别', object='词'),
                edge_label=label, description_label='pass', condition_label='pass', label=label,
                reason='来源说 "Alexa" 是示例。')


def malformed(row):
    return json.dumps(row, ensure_ascii=False).replace('\\"Alexa\\"', '"Alexa"')


@pytest.mark.parametrize('label', ['pass', 'fail', 'uncertain'])
def test_repairs_only_reason_quotes_without_selecting_a_label(label):
    row = verdict(label)
    corrected, note = recover_reason_quotes('```json\n' + malformed(row) + '\n```')
    assert json.loads(corrected) == row
    assert note['inserted_escape_characters'] == 2


def test_preserves_escaped_quotes_backslashes_and_newlines():
    row = verdict()
    row['reason'] += '\n路径 C:\\data；已转义 "another"'
    corrected, _ = recover_reason_quotes(malformed(row))
    assert json.loads(corrected) == row


@pytest.mark.parametrize('change', [
    lambda text: text[:-1],
    lambda text: text.replace('"edge_label": "pass",', ''),
    lambda text: text.replace('"edge_label": "pass"', '"edge_label": pass'),
    lambda text: text.replace('"subject": "甲"', '"subject": "坏"引号"'),
    lambda text: text.replace('"label": "pass"', '"label": "pass", "label": "fail"'),
    lambda text: text[:-1] + ', "label": "fail"}',
    lambda text: text.replace('示例。', '示例。 {"label":"pass"}'),
    lambda text: text.replace('示例。', '示例。\\q'),
])
def test_refuses_truncation_missing_fields_and_non_reason_corruption(change):
    with pytest.raises(ValueError):
        recover_reason_quotes(change(malformed(verdict())))


def test_does_not_repair_valid_response_or_api_error():
    for text in [json.dumps(verdict()), '{"error": "unavailable"}']:
        with pytest.raises(ValueError):
            recover_reason_quotes(text)
