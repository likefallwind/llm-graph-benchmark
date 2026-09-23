"""Regression checks for unsupported tails, target preservation and gating."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

PATH = Path(__file__).resolve().parents[1] / 'studies/d2l-assertion-audit-20260922/evaluate.py'

@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location('assertion_audit_test', PATH)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

@pytest.fixture
def task(runner):
    t = {'subject': 'A', 'predicate': '调用', 'object': 'B', 'description': 'A调用B。A运行速度翻倍。', 'scope': '', 'polarity': 'positive'}
    return {'id': 'q1', 'payload': {'target': t, 'segments': runner.segments(t), 'entity_context': {}, 'reference_context': [{'id': 'P1', 'text': 'A调用B，但运行速度没有变化。'}]}}


def response(task):
    ev = [{'id': 'P1', 'quote': 'A调用B'}]
    row = {'verdict': 'supported', 'evidence': ev, 'reason': 'test fixture'}
    return {'target_copy': copy.deepcopy(task['payload']['target']),
        'claims': [dict(copy.deepcopy(row), text=s['text'], segment_ids=[s['id']]) for s in task['payload']['segments']],
        'checks': {k: copy.deepcopy(row) for k in ('participants', 'relation_direction', 'conditions_polarity', 'field_consistency', 'claim_coverage')}}


def wire(value):
    return {'choices': [{'message': {'content': json.dumps(value, ensure_ascii=False)}}]}

@pytest.mark.parametrize('tail,expected', [('contradicted', 'incorrect'), ('not_established', 'uncertain'), ('ambiguous', 'uncertain')])
def test_correct_core_never_cancels_problematic_tail(runner, task, tail, expected):
    v = response(task); v['claims'][-1]['verdict'] = tail
    v['claims'][-1]['evidence'] = [{'id': 'P1', 'quote': '运行速度没有变化'}]
    v['label'] = 'correct'  # Model total must not override the program aggregation.
    assert runner.parse(wire(v), task)['label'] == expected


def test_explicit_field_conflict_not_repaired_by_supported_description(runner, task):
    v = response(task); v['checks']['field_consistency']['verdict'] = 'contradicted'
    assert runner.parse(wire(v), task)['label'] == 'incorrect'


def test_coverage_problem_is_review_not_automatic_factual_error(runner, task):
    v = response(task); v['checks']['claim_coverage']['verdict'] = 'contradicted'
    parsed = runner.parse(wire(v), task)
    assert parsed['label'] == 'uncertain' and parsed['requires_review']

@pytest.mark.parametrize('mutation', ['swapped-target', 'missing-tail', 'fake-quote', 'unknown-source', 'no-evidence', 'missing-check'])
def test_malformed_judgment_cannot_be_counted(runner, task, mutation):
    v = response(task)
    if mutation == 'swapped-target':
        v['target_copy']['subject'], v['target_copy']['object'] = v['target_copy']['object'], v['target_copy']['subject']
    elif mutation == 'missing-tail':
        v['claims'].pop()
    elif mutation == 'fake-quote':
        v['claims'][0]['evidence'][0]['quote'] = 'A运行速度翻倍'
    elif mutation == 'unknown-source':
        v['claims'][0]['evidence'][0]['id'] = 'not-provided'
    elif mutation == 'no-evidence':
        v['claims'][0]['evidence'] = []
    else:
        v['checks'].pop('participants')
    with pytest.raises(ValueError):
        runner.parse(wire(v), task)


def test_candidate_metadata_and_method_are_not_treated_as_source(runner, task):
    task['system'] = 'SECRET_METHOD'; task['expected'] = 'SECRET_EXPECTED'
    task['payload']['old_correctness'] = 'SECRET_OLD';task['payload']['submitted_sources'] = 'SECRET_EXTRA'
    task['payload']['entity_context'] = {'subject': {'name': 'A', 'definition': 'candidate definition'}}
    m = runner.messages(task, 'prompt')
    assert 'SECRET_' not in json.dumps(m)
    v = response(task); v['claims'][0]['evidence'][0] = {'id': 'P1', 'quote': 'candidate definition'}
    with pytest.raises(ValueError):
        runner.parse(wire(v), task)


def test_whole_section_preserves_imports_and_stops_at_next_section(runner):
    u = [{'unit_id': str(i), 'text': text} for i, text in enumerate(['# Book', '### First', 'from mxnet import np', '#### Block', 'np.zeros(2)', '### Next', 'different context'])]
    assert [x['id'] for x in runner.section_context(u, ['4'])] == ['1', '2', '3', '4']
    with pytest.raises(ValueError):
        runner.section_context(u, ['missing'])


def test_cached_development_failure_blocks_all_real_tasks(runner, task, tmp_path, monkeypatch):
    run = tmp_path; dev = copy.deepcopy(task); dev['id'] = 'dev-fail'; dev['expected'] = 'incorrect'
    files = {'tasks.json': [task], 'private-key.json': {'q1': {'system': 'hidden', 'old_correctness': {'status': 'done', 'value': {'label': 'correct'}}}}, 'development.json': [dev], 'prompts.json': {'correctness': runner.PROMPT}}
    for name, obj in files.items():
        runner.write(run / name, obj)
    runner.write(run / 'manifest.json', {'workers': 6, 'frozen_files': {name: runner.sha(run / name) for name in files}})
    runner.write(run / 'results/dev-fail.json', {'status': 'done', 'value': {'label': 'correct'}})
    def complete(*a, **k):
        raise AssertionError('Formal tasks must not be dispatched after failed checks')
    monkeypatch.setitem(sys.modules, 'transport', SimpleNamespace(REQUEST_CONCURRENCY=6, Client=lambda *a: SimpleNamespace(complete=complete)))
    assert runner.execute(run) == 2
    assert not (run / 'results/q1.json').exists()
    summary = runner.read(run / 'summary.json')
    assert summary['systems']['hidden']['unassessed'] == 1
    assert summary['development_passed'] is False


def test_development_pair_labels_are_equivalent_and_blinded(runner):
    spec = importlib.util.spec_from_file_location('audit_development_test', PATH.with_name('development.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cases = m.cases(); assert len(cases) == 33
    by_id = {x['id']: x for x in cases}
    for t in cases:
        if t['id'].endswith('-generic'):
            paired = by_id[t['id'].removesuffix('-generic') + '-typed']
            assert t['expected'] == paired['expected']
            assert t['payload']['target']['description'] == paired['payload']['target']['description']
        public = json.loads(runner.messages(t, 'prompt')[1]['content'])
        assert 'expected' not in public and 'id' not in public


def test_narrow_quote_recovery_preserves_meaning_and_records_repair(runner, task):
    v = response(task)
    v['claims'][0]['reason'] = '原文说"A调用B"，因此成立。'
    good = json.dumps(v, ensure_ascii=False)
    raw = good.replace('\\"A调用B\\"', '"A调用B"')
    # Construct the known provider formatting defect, with all semantics fixed.
    raw = good.replace(chr(92) + '"A调用B' + chr(92) + '"', '"A调用B"')
    result = runner.parse({'choices': [{'message': {'content': raw}}]}, task)
    assert result['claims'][0]['reason'] == v['claims'][0]['reason']
    assert result['format_repair'] == 'escaped_interior_quotes'
    assert runner.parse(wire(v), task)['format_repair'] is None


@pytest.mark.parametrize('raw', ['{"label":"correct"', '{"a":1 "b":2}', '{"a":"correct",}'])
def test_quote_recovery_does_not_invent_missing_structure(runner, raw):
    with pytest.raises(ValueError):
        runner.decode_ledger(raw)


def test_format_recovery_uses_first_valid_response_not_expected_label(runner, task, tmp_path):
    import shutil
    old, new = tmp_path / 'old', tmp_path / 'new'
    old.mkdir(); new.mkdir(); shutil.copy2(PATH, new / 'evaluate.py')
    t = copy.deepcopy(task); t['id'] = 'dev-fixture'; t['expected'] = 'incorrect'
    for folder in (old, new):
        for name, obj in [('prompts.json', {'correctness': runner.PROMPT}), ('development.json', [t]), ('tasks.json', [])]:
            runner.write(folder / name, obj)
    runner.write(old / 'development-report.json', {'passed': False})
    runner.write(old / 'results/dev-fixture.json', {'status': 'failed'})
    req = old / 'api/requests/r1'
    runner.write(req / 'request.json', {'messages': runner.messages(t, runner.PROMPT)})
    for index, label in enumerate(['supported', 'contradicted'], 1):
        value = response(t);value['claims'][-1]['verdict'] = label
        value['claims'][0]['reason'] = '原文说"A调用B"，因此成立。'
        raw = json.dumps(value, ensure_ascii=False).replace(chr(92) + '"A调用B' + chr(92) + '"', '"A调用B"')
        wire_value = {'choices': [{'message': {'content': raw}}]}
        runner.write(req / ('attempt-' + str(index) + '.json'), {'started_at': index, 'raw_body': json.dumps(wire_value)})
    spec = importlib.util.spec_from_file_location('audit_recovery_test', PATH.with_name('recover_format.py'))
    m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.recover(old, new)
    actual = runner.read(new / 'results/dev-fixture.json')
    assert actual['value']['label'] == 'correct'  # First answer, despite expected incorrect.
    assert actual['recovered_from'].endswith('attempt-1.json')
    assert runner.read(old / 'results/dev-fixture.json') == {'status': 'failed'}


def test_restore_only_final_outer_brace_with_complete_ledger(runner, task):
    v = response(task)
    raw = json.dumps(v, ensure_ascii=False)[:-1]
    result = runner.parse({'choices': [{'message': {'content': raw}}]}, task)
    assert result['format_repair'] == 'restored_outer_brace'
    assert result['claims'] == v['claims']
    incomplete = copy.deepcopy(v); incomplete['checks'].pop('participants')
    with pytest.raises(ValueError):
        runner.parse({'choices': [{'message': {'content': json.dumps(incomplete)[:-1]}}]}, task)


def test_source_id_reference_is_materialized_from_frozen_text(runner, task):
    v = response(task)
    for row in v['claims'] + list(v['checks'].values()):
        row['evidence'] = [{'id': 'P1'}]
    result = runner.parse(wire(v), task)
    for c in result['claims']:
        assert c['evidence'][0]['quote'] == task['payload']['reference_context'][0]['text']
        assert c['evidence'][0]['materialized_from_source'] is True
    v['claims'][0]['evidence'] = [{'id': 'UNKNOWN'}]
    with pytest.raises(ValueError):
        runner.parse(wire(v), task)

@pytest.fixture
def alignment():
    spec = importlib.util.spec_from_file_location('alignment_tests', PATH.with_name('alignment.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_alignment_call_is_blind_to_truth_and_source(runner, task, alignment):
    ledger = runner.parse(wire(response(task)), task)
    ledger['claims'][0]['reason'] = 'SECRET_REASON'
    ledger['claims'][0]['verdict'] = 'SECRET_LABEL'
    text = json.dumps(alignment.messages(task, ledger), ensure_ascii=False)
    assert 'SECRET_' not in text and 'reference_context' not in text


def test_phantom_clause_is_preserved_but_not_counted(runner, task, alignment):
    ledger = runner.parse(wire(response(task)), task)
    ledger['claims'].append({'text': 'A还保证零能耗', 'segment_ids': ['s1'], 'verdict': 'not_established', 'evidence': [], 'reason': 'No basis'})
    ledger['label'] = 'uncertain'
    a = {'claims': [{'index': i, 'status': 'asserted' if i < 3 else 'not_asserted', 'reason': 'fixture'} for i in range(4)], 'coverage': 'complete', 'reason': 'fixture'}
    v = alignment.combine(ledger, a)
    assert v['label'] == 'correct' and v['pre_alignment_label'] == 'uncertain'
    assert v['claims'][-1] == ledger['claims'][-1] and v['excluded_claim_indices'] == [3]


def test_real_bad_claim_still_fails_after_alignment(runner, task, alignment):
    v = response(task);v['claims'][-1]['verdict'] = 'contradicted'
    ledger = runner.parse(wire(v), task)
    a = {'claims': [{'index': i, 'status': 'asserted', 'reason': 'fixture'} for i in range(3)], 'coverage': 'complete', 'reason': 'fixture'}
    assert alignment.combine(ledger, a)['label'] == 'incorrect'


def test_ambiguous_or_incomplete_alignment_cannot_pass(runner, task, alignment):
    ledger = runner.parse(wire(response(task)), task)
    a = {'claims': [{'index': i, 'status': 'asserted', 'reason': 'fixture'} for i in range(3)], 'coverage': 'incomplete', 'reason': 'fixture'}
    assert alignment.combine(ledger, a)['label'] == 'uncertain'
    a['coverage'] = 'complete';a['claims'][0]['status'] = 'ambiguous'
    assert alignment.combine(ledger, a)['label'] == 'uncertain'


def test_alignment_cannot_omit_or_duplicate_indices(alignment):
    r = {'choices': [{'message': {'content': '<item>0|asserted|x</item><item>0|asserted|x</item><coverage>complete|x</coverage>'}}]}
    with pytest.raises(ValueError):alignment.parse(r, 2)


def test_mixed_explanation_can_support_but_not_disprove_target(runner, task, alignment):
    ledger = runner.parse(wire(response(task)), task)
    a = {'claims': [{'index': i, 'status': 'contains_target' if i == 2 else 'asserted', 'reason': 'fixture'} for i in range(3)], 'coverage': 'complete', 'reason': 'fixture'}
    assert alignment.combine(ledger, a)['label'] == 'correct'
    ledger['claims'][2]['verdict'] = 'contradicted'
    v = alignment.combine(ledger, a)
    assert v['label'] == 'uncertain'
    assert v['partial_unresolved_claim_indices'] == [2]
    assert v['claims'][2]['verdict'] == 'contradicted'  # Original vote remains intact.
