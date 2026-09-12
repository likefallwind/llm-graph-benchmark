"""One frozen chunk per baseline; all calls share the same six request slots."""
import os
from pathlib import Path
import subprocess
import sys
from common import UPSTREAM, BENCH, write

root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
limit=sys.argv[2] if len(sys.argv)>2 else '1'
source=Path(__file__).resolve().parent
jobs=[]
for method,env_name in [('kggen','kg-gen'),('autoschemakg','kg-gen'),('graphrag','graphrag')]:
    env=dict(os.environ,PYTHONPATH=str(BENCH/'src')+':'+str(UPSTREAM/'autoschemakg'),
             PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='20260909',
             OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             HF_HUB_OFFLINE='1',DSPY_CACHEDIR=str(root/'dspy-cache'),
             LITELLM_LOCAL_MODEL_COST_MAP='True',TOKENIZERS_PARALLELISM='false')
    log=(root/(method+'.log')).open('a')
    cmd=[str(UPSTREAM/env_name/'.venv/bin/python'),'-u',str(source/('run_'+method+'.py')),
         '--out',str(root/method),'--lock-root',str(root/'request-slots'),'--limit',limit]
    process=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    jobs.append((method,process,log))
codes={}
for name,p,log in jobs:
    codes[name]=p.wait();log.close()
    print(name,'exit',codes[name],flush=True)
write(root/'smoke-status.json',codes)
sys.exit(1 if any(codes.values()) else 0)
