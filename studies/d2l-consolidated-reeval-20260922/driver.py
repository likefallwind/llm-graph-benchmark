"""Detached phase launcher. Credentials are inherited, never written."""
from pathlib import Path
import argparse,datetime,json,os,shlex,subprocess,sys

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def worker(run,phase):
 code=1;(run/('.'+phase+'.started')).write_text(now()+'\n')
 try:
  with (run/(phase+'.log')).open('a',buffering=1) as log:
   code=subprocess.run([sys.executable,str(run/'evaluate.py'),phase,'--run',str(run)],cwd=run,stdout=log,stderr=subprocess.STDOUT).returncode
   if phase=='run':
    report=subprocess.run([sys.executable,str(run/'finalize.py'),str(run)],cwd=run,stdout=log,stderr=subprocess.STDOUT)
    if not code:code=report.returncode
   log.write('Exited '+str(code)+' at '+now()+'\n')
 finally:
  (run/('.'+phase+'.exit')).write_text(str(code)+'\n')
  if code==0:(run/('.'+phase+'.finished')).write_text(now()+'\n')
 return code

def launch(run,phase):
 if not os.environ.get('MINIMAX_API_KEY'):raise RuntimeError('Credential unavailable')
 if (run/('.'+phase+'.started')).exists() or (run/(phase+'-launch.json')).exists():raise RuntimeError('Phase already launched')
 env={k:os.environ[k] for k in ['HOME','PATH','LANG','LC_ALL','MINIMAX_API_KEY'] if k in os.environ};env.update(PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
 name=run.name+'-'+phase;cmd=shlex.join([sys.executable,str(run/'driver.py'),'worker','--phase',phase,'--run',str(run)])
 subprocess.run(['tmux','-L',name,'-f','/dev/null','new-session','-d','-s',name,'-c',str(run),cmd],env=env,check=True)
 info={'run':str(run),'phase':phase,'session':name,'socket':name,'launched_at':now(),'max_http_concurrency':6};(run/(phase+'-launch.json')).write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info));return 0
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','worker']);p.add_argument('--phase',choices=['check','pilot','run'],required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args();sys.exit((launch if a.action=='launch' else worker)(a.run,a.phase))
