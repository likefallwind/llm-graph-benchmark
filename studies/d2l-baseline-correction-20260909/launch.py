"""Durable controller: pinned source, shared API limit, construction then scoring."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from common import BENCH, CORPUS, UPSTREAM, read, sha, write, benchmark_path


def launch(root,prepare_only=False):
    root.mkdir(parents=True,exist_ok=True)
    lock=(root/'controller.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    source=root/'source'
    if not source.exists():
        source.mkdir()
        for file in Path(__file__).parent.glob('*.py'):shutil.copy2(file,source/file.name)
        # Freeze evaluator library and legacy rubric/parser sources used by evaluate.py.
        shutil.copytree(BENCH/'src',source/'benchmark-src',ignore=shutil.ignore_patterns('__pycache__','*.egg-info'))
        legacy=source/'frozen-evaluation';legacy.mkdir()
        for name in ('judge_carb.py','review_tasks.py'):
            shutil.copy2(BENCH/'studies/d2l-fullbook-open-baselines-20260826'/name,legacy/name)
        shutil.copy2(BENCH/'studies/d2l-quality-protocol-20260907/judge.py',legacy/'judge.py')
        frozen_bench=source/'frozen-benchmark';frozen_bench.mkdir()
        original_bench=benchmark_path()
        shutil.copy2(original_bench,frozen_bench/'benchmark.json')
        for key,value in read(original_bench).items():
            if key.endswith('_file'):
                destination=frozen_bench/value;destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(original_bench.parent/value,destination)
        (source/'frozen-corpus').mkdir()
        shutil.copy2(CORPUS,source/'frozen-corpus/chunks.jsonl')
        write(root/'launch.json',dict(created_at=time.time(),corpus=str(CORPUS),corpus_sha256=sha(CORPUS),
              concurrent_request_limit=6,model='MiniMax-M3',
              source_sha256={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()},
              baseline_commits={n:subprocess.check_output(['git','-C',str(UPSTREAM/n),'rev-parse','HEAD'],text=True).strip()
                                for n in ('kg-gen','autoschemakg','graphrag')}))
    manifest=read(root/'launch.json')
    if sha(CORPUS)!=manifest['corpus_sha256']:raise ValueError('corpus changed')
    for path,h in manifest['source_sha256'].items():
        if sha(source/path)!=h:raise ValueError('runner snapshot changed')
    for name,commit in manifest['baseline_commits'].items():
        actual=subprocess.check_output(['git','-C',str(UPSTREAM/name),'rev-parse','HEAD'],text=True).strip()
        if actual!=commit or subprocess.check_output(['git','-C',str(UPSTREAM/name),'status','--porcelain'],text=True).strip():
            raise ValueError('upstream checkout changed')
    if prepare_only:
        return
    if (root/'.finished').exists():return
    (root/'.exit').unlink(missing_ok=True)
    (root/'.started').write_text(str(time.time())+'\n')
    def stop(signum,frame):
        raise KeyboardInterrupt(f'Controller signal {signum}')
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    signal.signal(signal.SIGHUP,stop)
    jobs={};status={}
    def spawn(name,stage):
        env_name='graphrag' if name=='graphrag' else 'kg-gen'
        env=dict(os.environ,PYTHONPATH=str(source/'benchmark-src')+':'+str(UPSTREAM/'autoschemakg'),
            PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='20260909',
            OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
            HF_HUB_OFFLINE='1',DSPY_CACHEDIR=str(root/'dspy-cache'),
            LITELLM_LOCAL_MODEL_COST_MAP='True',TOKENIZERS_PARALLELISM='false')
        args=([str(source/('run_'+name+'.py')),'--out',str(root/name)] if stage=='construction'
              else [str(source/'evaluate.py'),'--run',str(root/name)])
        log=(root/(name+'-'+stage+'.log')).open('a')
        cmd=[str(UPSTREAM/env_name/'.venv/bin/python'),'-u',*args,'--lock-root',str(root/'request-slots')]
        process=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[name]=(process,log,stage)
        status[name]=dict(stage=stage,status='running',pid=process.pid)
    for name in ('kggen','autoschemakg','graphrag'):
        if (root/name/'evaluation/.finished').exists():status[name]=dict(status='complete');continue
        spawn(name,'evaluation' if (root/name/'.finished').exists() else 'construction')
    try:
        while jobs:
            for name,(process,log,stage) in list(jobs.items()):
                code=process.poll()
                if code is None:continue
                log.close();del jobs[name]
                write(root/(name+'-'+stage+'-exit.json'),dict(exit_code=code,at=time.time()))
                status[name]=dict(stage=stage,status='failed' if code else 'complete',exit_code=code)
                expected=root/name/('.finished' if stage=='construction' else 'evaluation/.finished')
                if code==0 and not expected.exists():status[name]['status']='failed_missing_artifacts'
                elif code==0 and stage=='construction':spawn(name,'evaluation')
            for name in status:
                progress=root/name/('evaluation/progress.json' if status[name].get('stage')=='evaluation' else 'progress.json')
                if progress.exists():status[name]['progress']=read(progress)
            write(root/'status.json',dict(updated_at=time.time(),methods=status,
                status='running' if jobs else 'complete' if all(x['status']=='complete' for x in status.values()) else 'incomplete'))
            if jobs:time.sleep(10)
    finally:
        if jobs:
            for process,log,stage in jobs.values():
                try:os.killpg(process.pid,15)
                except ProcessLookupError:pass
                log.close()
            (root/'.exit').write_text('1\n')
    complete=all(x['status']=='complete' for x in status.values())
    if complete:
        results={name:read(root/name/'evaluation/summary.json') for name in status}
        write(root/'results.json',results)
        lines=['# 修正基线结果','',
               'MiniMax-M3 官方 API；全任务共享最大并发 6。质量按 v2.2，覆盖按冻结 CaRB covered。','',
               '| 方法 | 联合通过/样本 | 事实覆盖/48 |','|---|---:|---:|']
        for name,result in results.items():
            lines.append(f"| {name} | {result['quality'].get('pass',0)}/{result['quality_total']} | {result['recall'].get('yes',0)}/{result['recall_total']} |")
        lines+=['','这是修正配置的描述性结果，仍受同模型裁判与单书材料限制。',
                'KGGen 为官方 LM_BASED 模式，多语言召回；原始抽取复用并保存哈希。',
                'AutoSchemaKG 已完成原生概念化；本表质量/召回仅评语义断言，schema 另存。',
                'GraphRAG 保留原生关系描述，related_to 为格式适配，不代表开放谓词发现。']
        (root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
        (root/'.finished').write_text(str(time.time())+'\n')
    (root/'.exit').write_text('0\n' if complete else '1\n')
    if not complete:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    launch(a.out,a.prepare_only)
