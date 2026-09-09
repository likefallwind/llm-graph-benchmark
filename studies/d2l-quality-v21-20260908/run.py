from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shlex,shutil,subprocess
repo=Path('/home/likefallwind/code/llm-graph-benchmark')
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['checks','natural','full'],required=True);p.add_argument('--resume',type=Path);a=p.parse_args()
prepared=repo/'outputs/d2l-quality-v21-20260908'
if a.phase!='checks':
    gate=json.loads((prepared/'checks-status.json').read_text())
    assert gate['rule_check_gate']=='pass'
    review=prepared/'codex-natural-review.jsonl'
    assert len(review.read_text().splitlines())==25
if a.phase=='full':
    assert json.loads((prepared/'natural-status.json').read_text())['status']=='complete'
secret=next((os.environ[k].strip() for k in ('MINIMAX_API_KEY','MINIMAX_API','minimax_api') if os.environ.get(k)), '')
if not secret:
 for line in (Path('/home/likefallwind')/'.bashrc').read_text().splitlines():
  if not re.match(r'^\s*(?:export\s+)?(?:MINIMAX_API_KEY|MINIMAX_API|minimax_api)=',line):continue
  parts=shlex.split(line,comments=True)
  if parts and parts[0]=='export':parts=parts[1:]
  if len(parts)==1:
   val=parts[0].split('=',1)[1]
   if not any(c in val for c in ('$','`','\n')):secret=val.strip();break
if secret.lower().startswith('bearer '):secret=secret[7:].strip()
if not secret:raise SystemExit('Static MINIMAX_API_KEY unavailable')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
judge_id='minimax-m3-official-quality-v21-t0-8192'
if a.resume:
    run=a.resume.resolve();info=json.loads((run/'launch.json').read_text());assert info['phase']==a.phase
    for name,h in info['source_sha256'].items():assert sha(run/name)==h
else:
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    run=repo/'outputs'/('d2l-quality-v21-'+a.phase+'-m3-c4-'+stamp)
    run.mkdir();(run/'source').mkdir()
    shutil.copytree(repo/'src',run/'source/src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    for name,source in [('judge.py','studies/d2l-quality-protocol-20260907/judge.py'),('calibration.py','studies/d2l-quality-v2-20260908/calibration.py')]:shutil.copy2(repo/source,run/'source'/name)
    prefix={'checks':'checks-','natural':'natural-','full':''}[a.phase]
    for name in ('tasks','key'):shutil.copy2(prepared/(prefix+name+'.jsonl'),run/(name+'.jsonl'))
    count=len((run/'tasks.jsonl').read_text().splitlines())
    info=dict(run_directory=str(run),phase=a.phase,started_at=datetime.datetime.now().astimezone().isoformat(),workers=4,model='MiniMax-M3',judge_id=judge_id,
      endpoint='https://api.minimaxi.com/v1/text/chatcompletion_v2',tasks=count,
      source_sha256={str(p.relative_to(run)):sha(p) for p in (run/'source').rglob('*') if p.is_file()},
      inputs_sha256={n:sha(run/n) for n in ('tasks.jsonl','key.jsonl')})
    if a.phase!='checks': info['pre_api_review_sha256']=sha(prepared/'codex-natural-review.jsonl')
    (run/'launch.json').write_text(json.dumps(info,indent=2)+'\n')
for name,h in info['inputs_sha256'].items():assert sha(run/name)==h
Path('/tmp/quality-v21-'+a.phase+'-active.json').write_text(json.dumps(info,indent=2)+'\n')
# Preserve history across API-error-only resumes; don't overwrite completed semantic judgments.
with (run/'invocations.jsonl').open('a') as f:f.write(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'resume':bool(a.resume)})+'\n')
if (run/'.exit').exists():(run/'.exit').unlink()
(run/'.started').write_text(datetime.datetime.now().astimezone().isoformat()+'\n')
env=dict(os.environ,MINIMAX_API_KEY=secret,PYTHONPATH=str(run/'source/src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
cmd=['/home/likefallwind/miniconda3/bin/python',str(run/'source/judge.py'),'--tasks',str(run/'tasks.jsonl'),'--key',str(run/'key.jsonl'),'--out',str(run),'--workers','4','--judge-id',judge_id]
print(json.dumps({'run':str(run),'status':'starting','tasks':info['tasks'],'workers':4}),flush=True)
with (run/'run.log').open('a') as log:r=subprocess.run(cmd,env=env,cwd=repo,stdout=log,stderr=subprocess.STDOUT)
(run/'.exit').write_text(str(r.returncode)+'\n')
if r.returncode==0:(run/'.finished').write_text(datetime.datetime.now().astimezone().isoformat()+'\n')
if a.phase=='checks' and (run/'judgments.jsonl').exists():
    report=run/'rule-check-report.json'
    if report.exists():report.rename(run/('rule-check-report-'+datetime.datetime.now().strftime('%H%M%S')+'.json'))
    subprocess.run(['/home/likefallwind/miniconda3/bin/python',str(run/'source/calibration.py'),'--key',str(run/'key.jsonl'),'--judgments',str(run/'judgments.jsonl'),'--judge-id',judge_id,'--out',str(report)],env=env,cwd=repo,check=True)
    state=json.loads(report.read_text());state['run_directory']=str(run)
else:
    state=json.loads((run/'summary.json').read_text());state['run_directory']=str(run)
(prepared/(a.phase+'-status.json')).write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps({'run':str(run),'exit_code':r.returncode}),flush=True)
