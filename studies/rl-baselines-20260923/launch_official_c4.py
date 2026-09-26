"""Start the authorized Gateway continuation; preserve all prior successful work."""
from pathlib import Path
import fcntl,json,os,subprocess,sys,time
from llm_graph_benchmark.workflow.preparation import sha
from llm_graph_benchmark.workflow.transport import write
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/rl-baselines-20260923';SOURCE=OUT/'source-official-c4-resume'
sys.path.insert(0,str(SOURCE))
from gateway_adapter import load_secret
load_secret()
with (OUT/'controller.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path=OUT/'launch-official-c4-manifest.json'
    if not path.exists():
        parent=json.loads((OUT/'launch-manifest.json').read_text())
        write(path,{'created_at':time.time(),'backend':'minimax-official','request_model':'MiniMax-M3','workers':4,
            'parent_manifest_sha256':sha(OUT/'launch-manifest.json'),
            'upstream_commits':parent['upstream_commits'],
            'files':{str(p.relative_to(SOURCE)):sha(p) for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts},
            'transport_note':'Official MiniMax envelope; whole JSON fence rendering only; original responses preserved',
            'resume_note':'Prior successful evaluations preserved. KGGen extraction resumes native checkpoints; no repeated successful chunks.'})
    m=json.loads(path.read_text())
    for p,h in m['files'].items():assert sha(SOURCE/p)==h,'Frozen gateway source changed'
    if '--prepare-only' in sys.argv:print('Gateway snapshot verified');raise SystemExit(0)
    if (OUT/'.exit').exists():
        (OUT/'.exit').rename(OUT/('.exit-before-gateway-'+str(time.time_ns())))
    with (OUT/'controller-official-c4.log').open('ab') as log:
        env=dict(os.environ,PYTHONPATH=str(SOURCE/'benchmark-src'),PYTHONDONTWRITEBYTECODE='1')
        child=subprocess.Popen([sys.executable,'-u',str(SOURCE/'controller.py')],env=env,cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
write(OUT/'launch-official-c4.json',{'pid':child.pid,'at':time.time(),'backend':'minimax-official','model':'MiniMax-M3','workers':4})
print(json.dumps({'pid':child.pid,'backend':'minimax-official','model':'MiniMax-M3','workers':4}))
