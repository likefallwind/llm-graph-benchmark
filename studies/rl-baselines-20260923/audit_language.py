from pathlib import Path
import json,re,hashlib,collections,subprocess
root=Path('/home/likefallwind/code/llm-graph-benchmark');out=root/'outputs/rl-baselines-20260923';book=root/'outputs/rl-book2-20260923'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
doc=json.loads((book/'documents.jsonl').read_text().splitlines()[0]);units={u['unit_id']:u for u in doc['units']}
chunks=[json.loads(x) for x in (out/'source/frozen-corpus/chunks.jsonl').read_text().splitlines()]
flat=[uid for c in chunks for uid in c['unit_ids']]
assert len(flat)==len(set(flat))==2920 and all(x.startswith('S2:') for x in flat)
assert flat==[u['unit_id'] for u in doc['units'] if u['unit_id'].startswith('S2:')]
assert all(c['text']=='\n\n'.join(units[i]['text'] for i in c['unit_ids']) for c in chunks)
assert sha(out/'source/frozen-corpus/chunks.jsonl')==sha(out/'source-gateway-c6/frozen-corpus/chunks.jsonl')
cjk=lambda s:bool(re.search('[\u4e00-\u9fff]',s))
audit={'corpus':{'chunks':len(chunks),'units':len(flat),'all_RL_source':True,'verbatim_source_order':True,'corpus_sha256':sha(out/'source/frozen-corpus/chunks.jsonl'),'chunks_with_CJK':sum(cjk(c['text']) for c in chunks)},'methods':{},'upstream':{}}
for name in ['graphrag','autoschemakg','kg-gen']:
 p=Path('/home/likefallwind/code/llm-graph-baselines')/name
 audit['upstream'][name]={'commit':subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip(),'clean':not bool(subprocess.check_output(['git','-C',str(p),'status','--porcelain'],text=True).strip())}
for name,path in [('ours',book/'submission.json'),('graphrag',out/'graphrag/submission.json'),('autoschemakg',out/'autoschemakg/submission.json')]:
 s=read(path);es=s['documents'][0]['entities'];aa=s['documents'][0]['assertions']
 audit['methods'][name]={'entities':len(es),'assertions':len(aa),'entity_names_with_CJK':sum(cjk(e['name']) for e in es),'available_descriptions_with_CJK':sum(cjk(e.get('definition','')) for e in es if e.get('metadata',{}).get('definition_available') is not False),'predicates_with_CJK':sum(cjk(a['predicate']) for a in aa),'examples':[{'name':e['name'],'types':e.get('types',[])} for e in es[:3]],'referenced_source_prefixes':dict(collections.Counter(ref['unit_id'].split(':')[0] for e in es for ref in e.get('evidence',[])))}
kgfiles=list((out/'kggen/extraction/chunks').glob('chunk-*.json'))
ks=[read(p) for p in kgfiles if read(p).get('status')=='done']
lookup={tuple(c['unit_ids']) for c in chunks}
assert all(tuple(x['unit_ids']) in lookup for x in ks)
kn=set(n for x in ks for n in x['graph']['entities'])
audit['methods']['kggen']={'completed_chunks':len(ks),'all_chunks_have_RL_provenance':True,'raw_unique_names':len(kn),'raw_names_with_CJK':sum(cjk(n) for n in kn),'examples':sorted(kn)[:5],'final_graph_complete':(out/'kggen/.finished').exists()}
(out/'LANGUAGE_METHOD_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));print(json.dumps(audit,ensure_ascii=False,indent=2))
