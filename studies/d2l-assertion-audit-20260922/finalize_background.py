"""Detached run plus final comparison; credentials stay in inherited environment."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def verify(run):
    hashes = json.loads((run / 'companion-manifest.json').read_text())['sha256']
    for name, h in hashes.items():
        if hashlib.sha256((run / name).read_bytes()).hexdigest() != h:
            raise ValueError('Companion changed: ' + name)


def worker(run, granularity):
    verify(run)
    (run / '.started').write_text(stamp() + '\n')
    code = 1
    try:
        with (run / 'run.log').open('a', buffering=1) as log:
            log.write('Started ' + stamp() + '\n')
            result = subprocess.run([sys.executable, str(run / 'evaluate.py'), 'run', '--run', str(run)], stdout=log, stderr=subprocess.STDOUT, cwd=run)
            code = result.returncode
            finish = subprocess.run([sys.executable, str(run / 'compare.py'), '--run', str(run), '--granularity', str(granularity)], stdout=log, stderr=subprocess.STDOUT, cwd=run)
            if finish.returncode and not code:
                code = finish.returncode
            summary = json.loads((run / 'summary.json').read_text())
            if not code and not summary.get('complete'):
                code = 5
            log.write('Exited ' + str(code) + ' at ' + stamp() + '\n')
    finally:
        (run / '.exit').write_text(str(code) + '\n')
        if code == 0:
            (run / '.finished').write_text(stamp() + '\n')
    return code


def launch(run, granularity):
    verify(run)
    if not os.environ.get('MINIMAX_API_KEY'):
        raise RuntimeError('Inherited credential unavailable')
    if (run / '.started').exists() or (run / 'launch.json').exists():
        raise RuntimeError('Already launched')
    checks = json.loads((run / 'development-report.json').read_text())
    review = json.loads((run / 'pilot-review.json').read_text())
    if not checks['passed'] or not review.get('proceed_exploratory'):
        raise RuntimeError('Development checks and documented pilot review required')
    command = shlex.join([sys.executable, str(run / 'finalize_background.py'), 'worker', '--run', str(run), '--granularity', str(granularity)])
    env = {k: os.environ[k] for k in ('HOME', 'PATH', 'LANG', 'LC_ALL', 'MINIMAX_API_KEY') if k in os.environ}
    env.update(PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1')
    name = run.name
    subprocess.run(['tmux', '-L', name, '-f', '/dev/null', 'new-session', '-d', '-s', name, '-c', str(run), command], env=env, check=True)
    info = {'session': name, 'socket': name, 'run': str(run), 'launched_at': stamp(), 'workers': 6,
        'reports': ['REPORT.md', 'COMPARISON.md', 'comparison.json', 'review-items.json'], 'log': str(run / 'run.log')}
    (run / 'launch.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('action', choices=['launch', 'worker']);p.add_argument('--run', type=Path, required=True);p.add_argument('--granularity', type=Path, required=True);a=p.parse_args();sys.exit((launch if a.action == 'launch' else worker)(a.run.resolve(), a.granularity.resolve()))
