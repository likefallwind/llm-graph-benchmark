"""Resumable official MiniMax scoring for frozen quality tasks (stdlib only)."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import itertools
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from llm_graph_benchmark.aggregation import aggregate_judgments
from llm_graph_benchmark.comparison import compare_paired
from llm_graph_benchmark.io import read_jsonl
from llm_graph_benchmark.report import markdown_report

ENDPOINT = 'https://api.minimaxi.com/v1/text/chatcompletion_v2'
TERMINAL_CODES = {1004, 1008, 2013, 2049, 2067}
LABELS = {'pass', 'fail', 'uncertain'}


def atomic(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_verdict(content, task=None):
    if not isinstance(content, str):
        raise ValueError('response content must be text')
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.S).strip()
    if content.startswith('```'):
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content).strip()
    row = json.loads(content)
    if not isinstance(row, dict) or row.get('label') not in LABELS:
        raise ValueError('invalid semantic label')
    if not isinstance(row.get('reason'), str) or not row['reason'].strip():
        raise ValueError('missing judgment reason')
    if task and task['kind'] == 'assertion_quality_v2_2':
        expected = {k: task['content'][k] for k in ('subject', 'predicate', 'object')}
        if row.get('evaluated_triple') != expected:
            raise ValueError('evaluated_triple differs from immutable input fields')
        axes = {k: row.get(k) for k in ('edge_label', 'description_label', 'condition_label')}
        if any(v not in LABELS for v in axes.values()):
            raise ValueError('missing or invalid quality axis')
        derived = 'fail' if 'fail' in axes.values() else 'uncertain' if 'uncertain' in axes.values() else 'pass'
        if row['label'] != derived:
            raise ValueError('overall label inconsistent with component labels')
        return {'label': derived, 'reason': row['reason'].strip(), 'evaluated_triple': expected, **axes}
    return {'label': row['label'], 'reason': row['reason'].strip()}


def request_body(task, model, max_tokens):
    # The private key and system identity are never sent to the model.
    return {'model': model, 'temperature': 0, 'max_tokens': max_tokens,
            'messages': [{'role': 'system', 'content': task['rubric']},
                         {'role': 'user', 'content': json.dumps(
                             {'content': task['content'], 'source_evidence': task['source_evidence']},
                             ensure_ascii=False)}]}


class TerminalError(RuntimeError):
    pass


def call(task, args, secret, response_path):
    request = urllib.request.Request(ENDPOINT,
        data=json.dumps(request_body(task, args.model, args.max_tokens), ensure_ascii=False).encode(),
        headers={'Authorization': 'Bearer ' + secret, 'Content-Type': 'application/json'}, method='POST')
    # Disable gateway/proxy routing and redirects: credentials go only to the official host.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=args.timeout) as response:
            text = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        if exc.code not in {429} and exc.code < 500:
            raise TerminalError(f'HTTP {exc.code}') from None
        raise RuntimeError(f'HTTP {exc.code}') from None
    # Keep the entire response for audit; redact a credential if a server ever echoes it.
    text = text.replace(secret, '[REDACTED]')
    response_path.write_text(text, encoding='utf-8')
    payload = json.loads(text)
    code = (payload.get('base_resp') or {}).get('status_code', 0)
    if code not in (0, '0', None):
        if int(code) in TERMINAL_CODES:
            raise TerminalError(f'MiniMax status_code={code}')
        raise RuntimeError(f'MiniMax status_code={code}')
    choice = payload['choices'][0]
    if choice.get('finish_reason') == 'length':
        raise ValueError('output token limit reached; incomplete judgment')
    return parse_verdict(choice['message']['content'], task)


def judge_one(task, args, secret, stop):
    tid = task['task_id']
    result_path = args.out / 'results' / (tid + '.json')
    previous = json.loads(result_path.read_text()) if result_path.exists() else {}
    attempts = list(previous.get('attempts', []))
    result = {'task_id': tid, 'kind': task['kind'], 'judge_id': args.judge_id, 'label': 'error',
              'reason': 'interrupted before request', 'attempts': attempts}
    for retry in range(args.retries):
        if stop.is_set():
            break
        started = time.monotonic()
        record = {'attempt': len(attempts) + 1, 'started_at': time.time()}
        response_path = args.out / 'responses' / f'{tid}-{record["attempt"]:03d}.json'
        try:
            verdict = call(task, args, secret, response_path)
            result.update(verdict)
            record['status'] = 'success'
        except (ValueError, KeyError, IndexError, OSError, RuntimeError) as exc:
            message = f'{type(exc).__name__}: {exc}'.replace(secret, '[REDACTED]')[:300]
            result.update(label='error', reason=message)
            record.update(status='error', error=message)
            if isinstance(exc, TerminalError):
                stop.set()
        record['elapsed_seconds'] = round(time.monotonic() - started, 3)
        if response_path.exists():
            record['response_file'] = str(response_path.relative_to(args.out))
            try:
                record['usage'] = json.loads(response_path.read_text()).get('usage', {})
            except ValueError:
                pass
        attempts.append(record)
        atomic(result_path, result)
        if result['label'] in LABELS or stop.is_set():
            break
        if retry + 1 < args.retries:
            stop.wait(min(5 * 2**retry, 60))
    return result


def summarize(args, tasks, keys, *, status):
    rows = []
    for task in tasks:
        path = args.out / 'results' / (task['task_id'] + '.json')
        if path.exists():
            rows.append(json.loads(path.read_text()))
    tmp = args.out / 'judgments.jsonl.tmp'
    tmp.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    tmp.replace(args.out / 'judgments.jsonl')
    metrics = aggregate_judgments(keys, rows)
    atomic(args.out / 'metrics.json', metrics)
    report = markdown_report([], metrics)
    report = report.replace('# LLM Graph Benchmark Report', '# D2L quality v1 — official MiniMax judge', 1)
    report += '\n当前基线仍保留原阶段限制；单一模型评分未经独立校准，不能据此宣称完整方法 SOTA。\n'
    (args.out / 'REPORT.md').write_text(report, encoding='utf-8')
    systems = sorted({r['system_id'] for r in keys})
    comparisons = []
    for left, right in itertools.combinations(systems, 2):
        for kind in ('fact_recovery_strict_v1', 'fact_recovery_core_v1'):
            if not any(k['kind'] == kind and k['system_id'] in {left, right} for k in keys):
                continue
            comparisons.append(compare_paired(keys, rows, left=left, right=right, kind=kind, judge_id=args.judge_id))
    atomic(args.out / 'paired-comparisons.json', comparisons)
    scored = sum(r['label'] in LABELS for r in rows)
    usage = {}
    for row in rows:
        for attempt in row.get('attempts', []):
            for k, value in (attempt.get('usage') or {}).items():
                if isinstance(value, int) and not isinstance(value, bool):
                    usage[k] = usage.get(k, 0) + value
    summary = {'status': 'complete' if scored == len(tasks) else status,
               'total': len(tasks), 'scored': scored, 'errors': sum(r['label'] == 'error' for r in rows),
               'missing': len(tasks) - len(rows), 'usage_including_retries': usage,
               'model': args.model, 'endpoint': ENDPOINT, 'workers': args.workers,
               'judge_id': args.judge_id, 'updated_at': time.time()}
    atomic(args.out / 'summary.json', summary)
    return summary


def run(args):
    if not 1 <= args.workers <= 6 or args.retries < 1 or args.max_tokens < 1:
        raise ValueError('workers must be 1..6; retries and max_tokens positive')
    tasks, keys = read_jsonl(args.tasks), read_jsonl(args.key)
    by_id = {t['task_id']: t for t in tasks}
    if len(by_id) != len(tasks) or len({k['task_id'] for k in keys}) != len(keys) or set(by_id) != {k['task_id'] for k in keys}:
        raise ValueError('tasks/key IDs must be unique and match exactly')
    for task in tasks:
        if not re.fullmatch(r'q_[a-f0-9]{24}', task['task_id']):
            raise ValueError('invalid quality task ID')
        actual = hashlib.sha256(json.dumps(task['rubric'], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if task['rubric_sha256'] != actual:
            raise ValueError('rubric hash mismatch')
    for key in keys:
        task = by_id[key['task_id']]
        if key['rubric_sha256'] != task['rubric_sha256'] or key['kind'] != task['kind']:
            raise ValueError('task/key rubric or kind mismatch')
    config = {'tasks_sha256': digest(args.tasks), 'key_sha256': digest(args.key),
              'runner_sha256': digest(__file__), 'model': args.model, 'endpoint': ENDPOINT,
              'temperature': 0, 'max_tokens': args.max_tokens, 'judge_id': args.judge_id,
              'seed': args.seed, 'workers': args.workers}
    args.out.mkdir(parents=True, exist_ok=True)
    # Only one scoring writer may use this output directory, including during resume.
    with (args.out / 'writer.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = args.out / 'run-config.json'
        if path.exists() and json.loads(path.read_text()) != config:
            raise ValueError('resume configuration changed; choose a new output directory')
        atomic(path, config)
        for name in ('results', 'responses'):
            (args.out / name).mkdir(exist_ok=True)
        completed = set()
        for task in tasks:
            p = args.out / 'results' / (task['task_id'] + '.json')
            if p.exists():
                row = json.loads(p.read_text())
                if row.get('task_id') != task['task_id'] or row.get('judge_id') != args.judge_id:
                    raise ValueError('cached result identity mismatch')
                if row.get('label') in LABELS:
                    completed.add(task['task_id'])
        pending = [t for t in tasks if t['task_id'] not in completed]
        random.Random(args.seed).shuffle(pending)
        secret = next((os.environ[k].strip() for k in ('MINIMAX_API_KEY','MINIMAX_API','minimax_api') if os.environ.get(k)), '')
        if secret.lower().startswith('bearer '):
            secret = secret[7:].strip()
        if pending and not secret:
            raise ValueError('MINIMAX_API_KEY unavailable')
        summary = summarize(args, tasks, keys, status='running')
        print(f"START total={len(tasks)} cached={len(completed)} pending={len(pending)} workers={args.workers} model={args.model} endpoint={ENDPOINT}", flush=True)
        stop = threading.Event()
        iterator = iter(pending)
        consecutive_errors = 0
        def submit_next(pool, futures):
            task = next(iterator, None)
            if task is not None and not stop.is_set():
                futures.add(pool.submit(judge_one, task, args, secret, stop))
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = set()
            for _ in range(args.workers):
                submit_next(pool, futures)
            while futures:
                ready, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in ready:
                    futures.remove(future)
                    result = future.result()
                    consecutive_errors = consecutive_errors + 1 if result['label'] == 'error' else 0
                    if consecutive_errors >= 6:
                        stop.set()
                    summary = summarize(args, tasks, keys, status='running')
                    print(f"[{summary['scored']}/{summary['total']}] {result['kind']} {result['label']} errors={summary['errors']}", flush=True)
                    submit_next(pool, futures)
        summary = summarize(args, tasks, keys, status='incomplete')
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return 0 if summary['status'] == 'complete' else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--key', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--model', default='MiniMax-M3')
    parser.add_argument('--judge-id', default='minimax-m3-official-quality-v1-t0-8192')
    parser.add_argument('--max-tokens', type=int, default=8192)
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--retries', type=int, default=4)
    parser.add_argument('--seed', type=int, default=20260907)
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
