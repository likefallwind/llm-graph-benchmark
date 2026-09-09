from __future__ import annotations

import argparse
import importlib.util
import json
import threading
import time
from pathlib import Path

import pytest

from llm_graph_benchmark.quality import prepare_quality_tasks
from llm_graph_benchmark.io import write_jsonl

spec = importlib.util.spec_from_file_location('quality_judge', Path(__file__).parents[1] / 'studies/d2l-quality-protocol-20260907/judge.py')
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)


def test_parser_does_not_turn_api_errors_or_truncated_json_into_scores():
    assert judge.parse_verdict('<think>reason</think>\n```json\n{"label":"pass","reason":"supported"}\n```')['label'] == 'pass'
    for text in ('{"label":"pass"}', '{"label":"error","reason":"429"}', '{"label":"pass"'):
        with pytest.raises(ValueError):
            judge.parse_verdict(text)


def test_request_preserves_full_evidence_and_excludes_private_keys():
    task = {'rubric': 'judge exactly', 'source_evidence': [{'text': 'x' * 30000}],
            'content': {'source_fact': 'f'}, 'system_id': 'PRIVATE'}
    body = judge.request_body(task, 'MiniMax-M3', 8192)
    assert body['messages'][0]['content'] == task['rubric']
    assert json.loads(body['messages'][1]['content'])['source_evidence'] == task['source_evidence']
    assert 'PRIVATE' not in json.dumps(body)


def build_args(tmp_path):
    tasks, keys = [], []
    for system in ('a', 'b'):
        for i in range(4):
            tid = f'{system}-{i}'
            tasks.append(dict(task_id=tid, kind='fact_recovery',
                content={'source_fact':f'fact{i}', 'candidate_graph_assertions':[{'text':f'fact{i}'}]},
                source_evidence=[{'text':f'fact{i}'}]))
            keys.append(dict(task_id=tid, kind='fact_recovery', system_id=system, submission_hash=system,
                document_id='d', item_id=f'p{i}', retriever='bm25', retriever_params={'top_k':10}))
    output = prepare_quality_tasks(tasks, keys)
    write_jsonl(tmp_path/'tasks.jsonl',output.tasks)
    write_jsonl(tmp_path/'key.jsonl',output.key)
    return argparse.Namespace(tasks=tmp_path/'tasks.jsonl',key=tmp_path/'key.jsonl',out=tmp_path/'out',
        workers=6, retries=1, max_tokens=8192, model='MiniMax-M3', judge_id='test',seed=1,timeout=1)


def test_run_caps_concurrency_resumes_and_refuses_changed_inputs(tmp_path, monkeypatch):
    args = build_args(tmp_path)
    monkeypatch.setenv('MINIMAX_API_KEY','dummy')
    active = peak = calls = 0
    lock = threading.Lock()
    def fake_call(*params):
        nonlocal active, peak, calls
        with lock:
            calls += 1; active += 1; peak = max(peak,active)
        time.sleep(.02)
        with lock:
            active -= 1
        return {'label':'pass','reason':'synthetic fixture only'}
    monkeypatch.setattr(judge,'call',fake_call)
    assert judge.run(args) == 0
    assert peak == 6
    assert calls == 16
    summary=json.loads((args.out/'summary.json').read_text())
    assert summary['status']=='complete' and summary['scored']==16
    assert len((args.out/'judgments.jsonl').read_text().splitlines())==16
    assert judge.run(args)==0 and calls==16
    args.max_tokens=4096
    with pytest.raises(ValueError,match='configuration changed'):
        judge.run(args)


def test_terminal_api_error_stops_queue_and_is_not_complete(tmp_path, monkeypatch):
    args=build_args(tmp_path)
    monkeypatch.setenv('MINIMAX_API_KEY','dummy')
    def failed(*params):
        raise judge.TerminalError('MiniMax status_code=1008')
    monkeypatch.setattr(judge,'call',failed)
    assert judge.run(args)==1
    summary=json.loads((args.out/'summary.json').read_text())
    assert summary['status']=='incomplete' and summary['scored']==0
    assert summary['errors']<=6
    assert summary['missing']>0
