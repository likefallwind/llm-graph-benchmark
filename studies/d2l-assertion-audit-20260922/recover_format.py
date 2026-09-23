"""Recover only malformed JSON responses locally; never repeat semantic votes."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import time


def recover(old, new):
    spec = importlib.util.spec_from_file_location('frozen_recovery_parser', new / 'evaluate.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    for name in ('prompts.json', 'development.json', 'tasks.json'):
        if m.read(old / name) != m.read(new / name):
            raise ValueError('Cannot recover with changed scoring inputs: ' + name)
    if not (old / 'development-report.json').exists():
        raise ValueError('Wait for old development run to finish')
    tasks = m.read(new / 'development.json'); requests = {}
    for req in sorted((old / 'api/requests').glob('*/request.json')):
        msg = m.read(req)['messages']
        key = json.dumps(msg, ensure_ascii=False, sort_keys=True)
        requests.setdefault(key, []).append(req.parent)
    reused = []
    for t in tasks:
        src = old / 'results' / (t['id'] + '.json'); dst = new / 'results' / src.name
        if dst.exists():
            raise ValueError('Destination already has a judgment')
        result = m.read(src); item = {'id': t['id'], 'old_result_sha256': m.sha(src)}
        if result['status'] == 'done':
            item['action'] = 'preserve_valid_result'
        else:
            msg = m.messages(t, m.read(new / 'prompts.json')['correctness'])
            candidates = []
            for folder in requests.get(json.dumps(msg, ensure_ascii=False, sort_keys=True), []):
                for f in folder.glob('attempt-*.json'):
                    attempt = m.read(f)
                    candidates.append((attempt.get('started_at', 0), f, attempt))
            item['action'] = 'preserve_unassessed'
            for _, f, attempt in sorted(candidates):
                try:
                    raw = json.loads(attempt['raw_body'])
                    value = m.parse(raw, t)
                except (ValueError, KeyError, TypeError):
                    continue
                # First structurally valid chronological response, irrespective
                # of its label or whether it matches a development expectation.
                result = {'task_id': t['id'], 'status': 'done', 'value': value,
                    'finished_at': time.time(), 'recovered_from': str(f), 'raw_attempt_sha256': m.sha(f)}
                item.update(action='format_recovery', raw_attempt=str(f), raw_attempt_sha256=m.sha(f))
                break
        m.write(dst, result); reused.append(item)
    m.write(new / 'format-recovery.json', {'source_run': str(old), 'network_calls': 0,
        'selection': 'Preserve all old valid results; for failures use first chronological response passing structural checks, without consulting expected labels.', 'records': reused})
    print(json.dumps({'records': len(reused), 'recovered': sum(x['action'] == 'format_recovery' for x in reused), 'preserved_valid': sum(x['action'] == 'preserve_valid_result' for x in reused)}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--old', type=Path, required=True);p.add_argument('--new', type=Path, required=True);a=p.parse_args();recover(a.old.resolve(), a.new.resolve())
