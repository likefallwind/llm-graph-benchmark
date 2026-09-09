"""Delayed, bounded completion of the already-authorized frozen evaluation."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

REPO = Path('/home/likefallwind/code/llm-graph-benchmark')
RUN = REPO / 'outputs/d2l-quality-v22-full-m3-c4-20260908-125935'
PREPARED = REPO / 'outputs/d2l-quality-v22-20260908'
STUDY = REPO / 'studies/d2l-quality-v22-20260908'
CONTROL = RUN / 'background-completion'
OUT = REPO / 'outputs/d2l-quality-v22-results-20260908'
PYTHON = '/home/likefallwind/miniconda3/bin/python'

def now():
    return datetime.datetime.now().astimezone().isoformat()

def status(stage, **extra):
    data = dict(stage=stage, at=now(), run=str(RUN), report=str(OUT), **extra)
    temp = CONTROL / 'status.tmp'
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(CONTROL / 'status.json')
    print(json.dumps(data, ensure_ascii=False), flush=True)

def summary():
    return json.loads((RUN / 'summary.json').read_text())

def complete(s):
    return (s.get('status') == 'complete' and s.get('scored') == 1000
            and s.get('total') == 1000 and not s.get('errors') and not s.get('missing')
            and (RUN / '.exit').exists() and (RUN / '.exit').read_text().strip() == '0'
            and (RUN / '.finished').exists())

def writer_busy():
    with (RUN / 'writer.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(lock, fcntl.LOCK_UN)
    # The launcher can briefly outlive the scoring lock while finalizing markers.
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            argv = (entry / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if b'/tmp/launch-v22.py' in argv or str(STUDY / 'run.py').encode() in argv:
            return True
    return False

def main():
    check_at = time.time() + 1800
    status('scheduled', next_check_at=datetime.datetime.fromtimestamp(check_at).astimezone().isoformat(), summary=summary())
    time.sleep(max(0, check_at - time.time()))
    deadline = time.time() + 4 * 3600
    for attempt in range(4):
        while writer_busy():
            if time.time() > deadline:
                raise RuntimeError('Writer still active after four hours; no duplicate writer started')
            status('waiting_for_existing_writer', summary=summary())
            time.sleep(60)
        current = summary()
        if complete(current):
            break
        if attempt == 3:
            raise RuntimeError('Three recovery rounds exhausted; inspect retained error responses')
        status('resuming_errors_only', recovery_round=attempt + 1, summary=current)
        subprocess.run([PYTHON, str(STUDY / 'run.py'), '--phase', 'full', '--resume', str(RUN)], cwd=REPO, check=True)
        if not complete(summary()):
            time.sleep(60)
    if not complete(summary()):
        raise RuntimeError('Completion validation failed')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(REPO / 'src'))
    status('validating_and_reporting', summary=summary())
    subprocess.run([PYTHON, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests'], cwd=REPO, env=env, check=True)
    subprocess.run([PYTHON, str(STUDY / 'analyze.py'), '--run', str(RUN), '--prepared', str(PREPARED),
                    '--previous', str(REPO / 'outputs/d2l-quality-m3-official-c4-20260907-174524'),
                    '--out', str(OUT)], cwd=REPO, env=env, check=True)
    if not (OUT / 'RESULTS.md').is_file() or not (OUT / 'analysis.json').is_file():
        raise RuntimeError('Expected final report artifacts absent')
    status('complete', summary=summary())

if __name__ == '__main__':
    CONTROL.mkdir(exist_ok=True)
    with (CONTROL / 'controller.lock').open('a') as ownership:
        fcntl.flock(ownership, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (CONTROL / '.started').write_text(now() + '\n')
        code = 1
        try:
            main()
            (CONTROL / '.finished').write_text(now() + '\n')
            code = 0
        except Exception as exc:
            status('needs_attention', error=str(exc))
            traceback.print_exc()
        finally:
            (CONTROL / '.exit').write_text(str(code) + '\n')
        raise SystemExit(code)
