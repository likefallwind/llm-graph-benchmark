"""Queue one bounded technical-failure retry after the active evaluation."""
import fcntl
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rl_pipeline', here / 'run_pipeline.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
with (p.OUT / '.queued-retry.lock').open('a') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A retry is already queued')
    p.transport.write(p.OUT / 'queued-retry-state.json', {'phase': 'waiting_for_active_run', 'queued_at': time.time()})
    while p.engine.active(p.RUN):
        time.sleep(20)
    # Allow the pipeline to finish reporting and release its own lock.
    with (p.OUT / '.pipeline.lock').open('a') as pipeline_lock:
        fcntl.flock(pipeline_lock, fcntl.LOCK_EX)
    state = p.engine.status(p.RUN)
    if state.get('statuses', {}).get('failed', 0):
        p.transport.write(p.OUT / 'queued-retry-state.json', {'phase': 'retrying', 'started_at': time.time()})
        code = subprocess.call([sys.executable, str(here / 'run_pipeline.py'), '--retry-failed'], cwd=p.ROOT)
    else:
        code = 0
    p.transport.write(p.OUT / 'queued-retry-state.json', {'phase': 'finished', 'exit_code': code, 'finished_at': time.time()})
