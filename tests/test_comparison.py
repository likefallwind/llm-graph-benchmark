import pytest

from llm_graph_benchmark.comparison import compare_paired


KIND = 'fact_recovery_strict_v1'


def fixture_rows():
    keys, judgments = [], []
    # 9 wins, 3 losses, 36 ties reproduce the audit's paired significance case.
    for i in range(48):
        for system in ('a', 'b'):
            tid = f'{system}-{i}'
            keys.append(dict(task_id=tid, system_id=system, kind=KIND,
                             document_id='doc', item_id=f'p{i}',
                             rubric_sha256='rubric', comparison_context=f'context{i}'))
            label = 'pass' if (i < 9 and system == 'a') or (9 <= i < 12 and system == 'b') or i >= 12 else 'fail'
            judgments.append(dict(task_id=tid, judge_id='j', label=label))
    return keys, judgments


def compare(keys, votes):
    return compare_paired(keys, votes, left='a', right='b', kind=KIND, judge_id='j')


def test_comparison_uses_discordant_pairs_not_independent_intervals():
    keys, votes = fixture_rows()
    result = compare(keys, votes)
    assert result['left_only_pass'] == 9
    assert result['right_only_pass'] == 3
    assert result['exact_mcnemar_p'] == pytest.approx(0.14599609375)
    assert result['pass_rate_difference'] == pytest.approx(6/48)


@pytest.mark.parametrize('mutation', ['missing', 'error', 'other_judge'])
def test_incomplete_comparison_never_emits_significance(mutation):
    keys, votes = fixture_rows()
    if mutation == 'missing':
        votes.pop()
    elif mutation == 'error':
        votes[-1]['label'] = 'error'
    else:
        votes[-1]['judge_id'] = 'different-family'
    result = compare(keys, votes)
    assert result['status'] == 'incomplete'
    assert result['exact_mcnemar_p'] is None


@pytest.mark.parametrize('field', ['comparison_context', 'rubric_sha256', 'item_id'])
def test_different_source_budget_protocol_or_probe_set_is_rejected(field):
    keys, votes = fixture_rows()
    keys[-1][field] = 'changed'
    with pytest.raises(ValueError):
        compare(keys, votes)


def test_uncertain_is_not_silently_dropped_and_duplicates_are_rejected():
    keys, votes = fixture_rows()
    votes[0]['label'] = 'uncertain'
    result = compare(keys, votes)
    assert result['left_only_pass'] == 8
    assert result['transitions']['uncertain->fail'] == 1
    with pytest.raises(ValueError, match='duplicate judgment'):
        compare(keys, votes + [votes[0]])
