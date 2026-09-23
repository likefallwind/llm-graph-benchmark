"""Launch one frozen evaluation in detached tmux; never print credentials."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def worker(run):
    code = 1
    (run / '.started').write_text(stamp() + '\n')
    try:
        with (run / 'run.log').open('a', buffering=1) as log:
            log.write('Started ' + stamp() + '\n')
            child = subprocess.run([sys.executable, str(run / 'evaluate.py'), 'run', '--run', str(run)],
                                   stdout=log, stderr=subprocess.STDOUT, cwd=run)
            code = child.returncode if child.returncode >= 0 else 128 - child.returncode
            if code == 0:
                summary = json.loads((run / 'summary.json').read_text())
                progress = json.loads((run / 'progress.json').read_text())
                if not summary.get('complete') or progress.get('phase') != 'complete':
                    code = 5
            log.write(f'Exited {code} at {stamp()}\n')
    finally:
        (run / '.exit').write_text(str(code) + '\n')
        if code == 0:
            (run / '.finished').write_text(stamp() + '\n')
    return code


def launch(run):
    if not os.environ.get('MINIMAX_API_KEY'):
        raise RuntimeError('Inherited MINIMAX_API_KEY is required')
    if (run / '.started').exists() or (run / 'launch.json').exists():
        raise RuntimeError('Run already launched; inspect durable state before resuming')
    name = run.name
    command = shlex.join([sys.executable, str(run / 'background.py'), 'worker', '--run', str(run)])
    # An isolated tmux server inherits this credential without command-line or file storage.
    env = {k: os.environ[k] for k in ('HOME', 'PATH', 'LANG', 'LC_ALL', 'MINIMAX_API_KEY') if k in os.environ}
    env.update(PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1')
    subprocess.run(['tmux', '-L', name, '-f', '/dev/null', 'new-session', '-d', '-s', name,
                    '-c', str(run), command], env=env, check=True)
    info = {'session': name, 'socket': name, 'run': str(run), 'started_launch_at': stamp(),
            'log': str(run / 'run.log'), 'progress': str(run / 'progress.json'),
            'exit': str(run / '.exit'), 'finished': str(run / '.finished')}
    (run / 'launch.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['launch', 'worker'])
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run.resolve()
    sys.exit(launch(run_dir) if args.action == 'launch' else worker(run_dir))
