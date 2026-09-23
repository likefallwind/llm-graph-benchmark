import json,hashlib,pathlib,shutil,datetime
root=pathlib.Path('/home/likefallwind/code/llm-graph-benchmark')
src=root/'outputs/d2l-assertion-ledger-v25-20260922'
dst=root/'outputs/d2l-assertion-ledger-v25-20260922-recovery01'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert (src/'.exit').read_text().strip()=='3'
assert not dst.exists()
manifest=read(src/'manifest.json'); companion=read(src/'companion-manifest.json')
files=set(manifest['frozen_files'])|set(companion['sha256'])|{'manifest.json','companion-manifest.json','development-report.json','pilot-review.json','PILOT_REVIEW.md','ledger-reuse.json'}
for name,h in {**manifest['frozen_files'],**companion['sha256']}.items():assert sha(src/name)==h,name
ids={t['id'] for t in read(src/'tasks.json')};failed=[];valid={}
for i in ids:
 f=src/'results'/(i+'.json');r=read(f)
 if r['status']=='failed':failed.append(i)
 else:assert r['status']=='done';valid[f.name]=sha(f)
assert len(failed)==55 and len(valid)==745
(dst/'results').mkdir(parents=True);(dst/'prior-failures').mkdir()
for n in files:shutil.copy2(src/n,dst/n)
shutil.copytree(src/'ledgers',dst/'ledgers')
for f in (src/'results').glob('*.json'):
 target=dst/('prior-failures' if f.stem in failed else 'results')/f.name
 shutil.copy2(f,target)
for n,h in valid.items():assert sha(dst/'results'/n)==h
provenance={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parent_run':str(src),'retry_policy':'One additional bounded pass on all 55 technical failures, regardless of method. Same frozen evaluator, prompts, context, model, concurrency 6. Preserve all existing valid final labels and valid first-stage ledgers. No semantic label selection.','retry_ids':sorted(failed),'preserved_final_sha256':valid,'preserved_ledger_sha256':{f.name:sha(f) for f in (dst/'ledgers').glob('*.json')},'parent_failure_sha256':{(i+'.json'):sha(src/'results'/(i+'.json')) for i in failed}}
(dst/'recovery-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'run':str(dst),'retry':len(failed),'preserved':len(valid)}))
