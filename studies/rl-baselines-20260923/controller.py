"""Sequential RL baseline construction + the selected-metrics workflow (MiniMax, 4)."""
from pathlib import Path
import csv
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from llm_graph_benchmark.workflow import engine, transport
from llm_graph_benchmark.workflow.preparation import prepare, read, sha
from llm_graph_benchmark.workflow.reporting import report

ROOT=Path('/home/likefallwind/code/llm-graph-benchmark')
OUT=ROOT/'outputs/rl-baselines-20260923'
BOOK=ROOT/'outputs/rl-book2-20260923'
UP=Path('/home/likefallwind/code/llm-graph-baselines')
SOURCE=Path(__file__).resolve().parent
ORDER=('graphrag','autoschemakg','kggen')
NAMES={'graphrag':'GraphRAG','autoschemakg':'AutoSchemaKG','kggen':'KGGen'}

def state(phase,**kwargs):
    transport.write(OUT/'status.json',dict(phase=phase,updated_at=time.time(),pid=os.getpid(),model='MiniMax-M3',workers=4,order=list(ORDER),**kwargs))

def verify_snapshot():
    m=read(OUT/'launch-manifest.json')
    for path,h in m['files'].items():
        if sha(SOURCE/path)!=h:raise ValueError('Frozen runner/input changed: '+path)
    for name,commit in m['upstream_commits'].items():
        p=UP/name
        if subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()!=commit:raise ValueError('Upstream revision changed')
        if subprocess.check_output(['git','-C',str(p),'status','--porcelain'],text=True).strip():raise ValueError('Upstream worktree changed')

def archive(run,dest):
    summary=report(run)
    dest.mkdir(parents=True,exist_ok=True)
    for name in ('REPORT.md','comparison.csv','summary.json','case-results.json','manifest.json','sampling.json','parser-recovery-audit.json','parent-manifest.json'):
        if (run/name).exists():shutil.copy2(run/name,dest/name)
    transport.write(dest/'archive.json',{'run':str(run),'complete':summary['complete'],'at':time.time()})
    return summary

def judge(run):
    for attempt in range(2):
        if engine.status(run)['complete']:break
        engine.execute(run,retry_failed=True)
        if (run/'api/terminal-error.json').exists():raise RuntimeError('Provider terminal error; see run API status')
    return report(run)

def config_for(name):
    folder=OUT/name
    full=read(folder/'submission.json')
    # Represent native absence, never score the adapter placeholder as a description.
    for doc in full['documents']:
        for ent in doc['entities']:
            if ent.get('metadata',{}).get('definition_available') is False:ent['definition']=''
    transport.write(folder/'workflow-full-submission.json',full)
    quality=json.loads(json.dumps(full))
    if name=='autoschemakg':
        for doc in quality['documents']:
            doc['assertions']=[a for a in doc['assertions'] if a['predicate']!='is participated by']
    transport.write(folder/'workflow-quality-submission.json',quality)
    sys.path.insert(0,str(SOURCE))
    import common
    usage=common.usage(folder)
    transport.write(folder/'construction-usage.json',dict(input_tokens=usage['input_tokens'],output_tokens=usage['output_tokens'],source=str(folder/'requests'),note='All recorded construction responses with usage; evaluation excluded'))
    config={'benchmark':str(SOURCE/'frozen-benchmark/benchmark.json'),'seed':20260923,'workers':4,
            'submissions':[{'path':str(folder/'workflow-quality-submission.json'),'structure_path':str(folder/'workflow-full-submission.json'),
            'name':NAMES[name],'construction_usage':str(folder/'construction-usage.json'),
            'scope_note':('Semantic quality excludes native event-participation edges; structure retains full extracted graph; induced schema stored separately.' if name=='autoschemakg' else 'Pinned original construction, English RL source only; native output semantics retained.')} ]}
    transport.write(folder/'workflow.json',config)
    return folder/'workflow.json'

def combined(runs):
    table={};labels=[]
    for name,run in runs:
        rows=list(csv.reader((run/'comparison.csv').open()))
        for row in rows[1:]:
            if row[0] not in table:table[row[0]]={};labels.append(row[0])
            table[row[0]][name]=row[1]
    names=[n for n,_ in runs]
    with (OUT/'comparison.csv').open('w',newline='') as handle:
        w=csv.writer(handle);w.writerow(['指标',*names])
        for label in labels:w.writerow([label,*[table[label].get(n,'N/A') for n in names]])
    lines=['# 强化学习书：方法对比','', '本方法为跨书增量图；三个基线仅使用强化学习书原文。共用冻结题集与评分工作流，非等构图预算实验。','', '|指标|'+'|'.join(names)+'|','|---|'+'---:|'*len(names)]
    lines += ['|'+label+'|'+'|'.join(table[label].get(n,'N/A') for n in names)+'|' for label in labels]
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n')

def main():
    OUT.mkdir(exist_ok=True)
    with (OUT/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        verify_snapshot()
        ours=BOOK/'evaluation-c4-final'
        state('ours_evaluation',run=str(ours))
        if not judge(ours)['complete']:
            state('blocked_ours_incomplete',run=str(ours));return 3
        archive(ours,ROOT/'results/sutton-barto-20260923')
        runs=[('我们的方法',ours)]
        combined(runs)
        for name in ORDER:
            verify_snapshot();folder=OUT/name;folder.mkdir(exist_ok=True)
            if not (folder/'.finished').exists():
                state('construction',method=name)
                env=dict(os.environ,PYTHONPATH=str(SOURCE/'benchmark-src')+':'+str(UP/'autoschemakg'),
                    PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='20260923',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                    HF_HUB_OFFLINE='1',DSPY_CACHEDIR=str(OUT/'dspy-cache'),LITELLM_LOCAL_MODEL_COST_MAP='True',TOKENIZERS_PARALLELISM='false')
                interpreter=UP/('graphrag' if name=='graphrag' else 'kg-gen')/'.venv/bin/python'
                cmd=[str(interpreter),'-u',str(SOURCE/('run_'+name+'.py')),'--out',str(folder),'--lock-root',str(engine.slots_path())]
                with (OUT/(name+'-construction.log')).open('ab') as log:
                    code=subprocess.call(cmd,env=env,cwd=ROOT,stdout=log,stderr=log)
                if code or not (folder/'.finished').exists():
                    state('construction_failed',method=name,exit_code=code);return 3
            run=folder/'evaluation'
            if not run.exists():prepare(config_for(name),run)
            state('evaluation',method=name,run=str(run))
            summary=judge(run)
            archive(run,ROOT/'results/sutton-barto-baselines-20260923'/name)
            runs.append((NAMES[name],run));combined(runs)
        complete=all(engine.status(run)['complete'] for _,run in runs)
        dest=ROOT/'results/sutton-barto-baselines-20260923';dest.mkdir(exist_ok=True)
        for file in ('RESULTS.md','comparison.csv','launch-manifest.json'):shutil.copy2(OUT/file,dest/file)
        state('complete' if complete else 'evaluation_incomplete',runs={n:str(r) for n,r in runs})
        return 0 if complete else 3

if __name__=='__main__':
    try:code=main()
    except BaseException as error:
        state('controller_error',error_type=type(error).__name__);raise
    finally:(OUT/'.exit').write_text(str(locals().get('code',2)))
    raise SystemExit(code)
