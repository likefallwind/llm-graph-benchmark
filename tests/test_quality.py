from __future__ import annotations

import copy
import json

import pytest

from llm_graph_benchmark.cli import main
from llm_graph_benchmark.quality import RULES, prepare_quality_tasks


def source():
    task = {"task_id": "old", "kind": "fact_recovery",
            "content": {"source_fact": "A improves B under C, at cost D.",
                        "candidate_graph_assertions": [{"text": "A improves B under C."}]},
            "source_evidence": [{"text": "A improves B under C, at cost D." + "x" * 2000}]}
    key = {"task_id": "old", "kind": "fact_recovery", "system_id": "private-system",
           "document_id": "d", "item_id": "p", "submission_hash": "sha256:x",
           "retriever": "bm25", "retriever_params": {"top_k": 10},
           "strata": {"complexity": "scoped"}}
    return task, key


def test_new_scoring_preserves_frozen_inputs_and_full_evidence():
    task, key = source()
    original = copy.deepcopy((task, key))
    output = prepare_quality_tasks([task], [key])
    assert {r['kind'] for r in output.tasks} == {'fact_recovery_strict_v1', 'fact_recovery_core_v1'}
    assert all(r['task_id'] != 'old' for r in output.tasks)
    assert all(r['source_evidence'] == task['source_evidence'] for r in output.tasks)
    assert all(r['content'] == task['content'] for r in output.tasks)
    assert 'private-system' not in json.dumps(output.tasks)
    assert all(r['strata'] == key['strata'] for r in output.key)
    assert (task, key) == original
    assert output == prepare_quality_tasks([task], [key])


def test_rubric_edit_changes_task_identity(monkeypatch):
    task, key = source()
    before = prepare_quality_tasks([task], [key])
    monkeypatch.setitem(RULES, 'fact_recovery_strict_v1', 'A different frozen rule')
    after = prepare_quality_tasks([task], [key])
    assert before.tasks[0]['task_id'] != after.tasks[0]['task_id']
    assert before.key[0]['rubric_sha256'] != after.key[0]['rubric_sha256']


def test_joint_quality_accepts_legacy_assertion_task():
    task, key = source()
    task['kind'] = key['kind'] = 'assertion_grounding'
    output = prepare_quality_tasks([task], [key])
    assert [r['kind'] for r in output.tasks] == ['assertion_quality_v1']


def test_assertion_without_cited_evidence_is_retained_for_abstention():
    task, key = source()
    task['kind'] = key['kind'] = 'assertion_grounding'
    task['source_evidence'] = []
    output = prepare_quality_tasks([task], [key])
    assert len(output.tasks) == 1
    assert output.tasks[0]['source_evidence'] == []


def test_fact_preparation_refuses_unknown_retrieval_budget():
    task, key = source()
    del key['retriever_params']
    with pytest.raises(ValueError, match='retriever_params'):
        prepare_quality_tasks([task], [key])


@pytest.mark.integration
def test_quality_cli_protects_history_and_requires_fresh_output(tmp_path):
    task, key = source()
    (tmp_path/'tasks.jsonl').write_text(json.dumps(task)+'\n')
    (tmp_path/'key.jsonl').write_text(json.dumps(key)+'\n')
    args = ['quality-tasks', '--tasks', str(tmp_path/'tasks.jsonl'), '--key', str(tmp_path/'key.jsonl'),
            '--tasks-out', str(tmp_path/'new-tasks.jsonl'), '--key-out', str(tmp_path/'new-key.jsonl')]
    assert main(args) == 0
    assert main(args) == 2
    assert json.loads((tmp_path/'tasks.jsonl').read_text()) == task
