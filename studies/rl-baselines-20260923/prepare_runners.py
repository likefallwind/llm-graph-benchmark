from pathlib import Path
import json, shutil, subprocess
root=Path('/home/likefallwind/code/llm-graph-benchmark')
study=root/'studies/rl-baselines-20260923';study.mkdir(exist_ok=True)
base=root/'studies/d2l-baseline-correction-recovery-20260910'
out=root/'outputs/rl-baselines-20260923';out.mkdir(exist_ok=True)
book=root/'outputs/rl-book2-20260923'
bench=json.loads((book/'benchmark-reviewed.json').read_text());doc=json.loads((book/'documents.jsonl').read_text().splitlines()[0]);did=doc['document_id']
units=[u for u in doc['units'] if u['unit_id'].startswith('S2:')]
chunks=[];group=[]
for u in units:
    if group and sum(len(x['text'])+2 for x in group)+len(u['text'])>6000:
        chunks.append({'chunk_index':len(chunks),'unit_ids':[x['unit_id'] for x in group],'text':'\n\n'.join(x['text'] for x in group)});group=[]
    group.append(u)
if group:chunks.append({'chunk_index':len(chunks),'unit_ids':[x['unit_id'] for x in group],'text':'\n\n'.join(x['text'] for x in group)})
assert [i for c in chunks for i in c['unit_ids']]==[u['unit_id'] for u in units]
(study/'frozen-corpus').mkdir(exist_ok=True)
(study/'frozen-corpus/chunks.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in chunks))
(study/'frozen-benchmark').mkdir(exist_ok=True)
shutil.copy2(book/'benchmark-reviewed.json',study/'frozen-benchmark/benchmark.json')
for k,v in bench.items():
    if k.endswith('_file'):shutil.copy2(book/v,study/'frozen-benchmark'/v)
for name in ['common.py','recovery.py','run_graphrag.py','run_autoschemakg.py','run_kggen.py']:
    s=(base/name).read_text()
    s=s.replace('SEED = 20260909','SEED = 20260923').replace('limit=6','limit=4').replace('workers=6','workers=4').replace('min(max_workers,6)','min(max_workers,4)').replace("prompts['summarization_prompt'],6)","prompts['summarization_prompt'],4)")
    s=s.replace('Chinese','English').replace('zh-CN','en').replace("'d2l-fullbook-v1'",repr(bench['benchmark_id'])).replace("'d2l-zh-official'",repr(did)).replace('-zh-corrected','-en-rl').replace('d2l_corrected','rl_corrected').replace('six-slot','four-slot').replace('six work','four work').replace('six-slot','four-slot').replace('64 to 6','64 to 4').replace("f'{event} 由 {name} 参与。'","f'{event} is participated by {name}.'")
    if name=='common.py':
        s=s.replace('if not 1 <= limit <= 6:', 'if not 1 <= limit <= 4:').replace('concurrency must be in 1..6','concurrency must be in 1..4')
    if name=='run_kggen.py':
        s=s.replace('validate_export, openai_shape)', 'validate_export, openai_shape, parallel)')
        start=s.index('    historical = ');stop=s.index('    chunks = ',start)
        s=s[:start]+"    historical = out/'extraction'\n"+s[stop:]
        start=s.index('    class NativeLM(');stop=s.index('    kg=KGGen(',start)
        native=s[start:stop];s=s[:start]+s[stop:]
        anchor='    raw_triples = []'
        extract='''    transport = Client(out,lock_root)
'''+native+'''    local=threading.local()
    def extract(chunk):
        if not hasattr(local,'kg'):
            local.kg=KGGen(model='openai/'+MODEL,api_key='unused-native-transport',
                retrieval_model='/home/likefallwind/.cache/huggingface/hub/models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3',temperature=0,max_tokens=8192)
            local.kg.lm=NativeLM(model='openai/'+MODEL,temperature=0,max_tokens=8192,cache=False)
        graph=checkpoint(historical/'checkpoints'/f"chunk-{chunk['chunk_index']:04d}.json",chunk,
            lambda:local.kg.generate(chunk['text'],deduplication_method=None).model_dump(mode='json'))
        write(historical/'chunks'/f"chunk-{chunk['chunk_index']:04d}.json",
              dict(status='done',unit_ids=chunk['unit_ids'],graph=graph))
        return chunk['chunk_index']
    if offline_prepare:
        write(out/'prepared.json',dict(chunks=len(chunks),stage='fresh extraction required'))
        return
    for count,_ in enumerate(parallel(extract,chunks),1):
        write(out/'progress.json',dict(stage='extraction',completed=count,total=len(chunks)))
'''
        s=s.replace(anchor,extract+anchor)
        s=s.replace("historical_extraction_usage=read(historical/'run-report.json')['usage']", "extraction_included_in_usage=True")
    (study/name).write_text(s)
# Verify upstream checkouts without modifying them.
commits={}
for n in ['graphrag','autoschemakg','kg-gen']:
    p=Path('/home/likefallwind/code/llm-graph-baselines')/n
    commits[n]=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()
    assert not subprocess.check_output(['git','-C',str(p),'status','--porcelain'],text=True).strip(),n
print(json.dumps({'study':str(study),'document_id':did,'chunks':len(chunks),'source_units':len(units),'commits':commits}))
