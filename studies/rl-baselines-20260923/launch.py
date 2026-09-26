"""Freeze and detach the sequential, four-request MiniMax baseline workflow."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time
from llm_graph_benchmark.workflow.preparation import sha
from llm_graph_benchmark.workflow.transport import write, load_secret

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/rl-baselines-20260923'
SOURCE=OUT/'source'
UP=Path('/home/likefallwind/code/llm-graph-baselines')
if not SOURCE.exists():
    shutil.copytree(Path(__file__).resolve().parent,SOURCE,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'src',SOURCE/'benchmark-src',ignore=shutil.ignore_patterns('__pycache__','*.egg-info'))
    write(OUT/'launch-manifest.json',{'created_at':time.time(),'model':'MiniMax-M3','workers':4,
        'order':['ours_remaining','graphrag','autoschemakg','kggen'],
        'files':{str(p.relative_to(SOURCE)):sha(p) for p in SOURCE.rglob('*') if p.is_file()},
        'upstream_commits':{n:subprocess.check_output(['git','-C',str(UP/n),'rev-parse','HEAD'],text=True).strip() for n in ('graphrag','autoschemakg','kg-gen')}})
manifest=json.loads((OUT/'launch-manifest.json').read_text())
for path,h in manifest['files'].items():
    assert sha(SOURCE/path)==h,'Frozen source changed'
if '--prepare-only' in sys.argv:
    print(json.dumps({'prepared':True,'snapshot':str(SOURCE)}));raise SystemExit(0)
load_secret()
# The controller owns the process lock. A second launcher is rejected before dispatch.
import fcntl
with (OUT/'controller.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with (OUT/'controller.log').open('ab') as log:
        env=dict(os.environ,PYTHONPATH=str(SOURCE/'benchmark-src'),PYTHONDONTWRITEBYTECODE='1')
        child=subprocess.Popen([sys.executable,'-u',str(SOURCE/'controller.py')],cwd=ROOT,env=env,
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
write(OUT/'launch.json',{'pid':child.pid,'started_at':time.time(),'workers':4,'model':'MiniMax-M3'})
print(json.dumps({'pid':child.pid,'workers':4,'model':'MiniMax-M3','output':str(OUT)}))
