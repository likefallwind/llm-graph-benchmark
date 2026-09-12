"""Fresh official Chinese extraction and complete AutoSchemaKG conceptualization."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
from pathlib import Path
import random
import threading
import time

from common import (CORPUS, MODEL, SEED, Client, checkpoint, freeze, read, rows, sha, usage, write, validate_export, openai_shape, parallel)
from recovery import strict_concept_batch, validate_concept_response


def run(out,lock_root,limit=None,offline_prepare=False):
    from openai import OpenAI
    from openai.types.chat import ChatCompletion
    from atlas_rag.llm_generator import GenerationConfig, LLMGenerator
    from atlas_rag.kg_construction.triple_config import ProcessingConfig
    from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
    from atlas_rag.kg_construction.utils.json_processing.json_to_csv import clean_text
    from llm_graph_benchmark.adapters.triples import submission_from_triples

    chunks=rows(CORPUS)
    if limit:
        chunks=chunks[:limit]
    out.mkdir(parents=True,exist_ok=True)
    freeze(out/'manifest.json',dict(method='AutoSchemaKG',
        upstream_commit='d0a1666ae6621806faf814504c73678de4e809f2',model=MODEL,
        corpus_sha256=sha(CORPUS),chunks=len(chunks),seed=SEED,language='zh-CN',
        extraction='fresh official three-stage extraction; valid empty lists retained',
        conceptualization='official entity, event and relation conceptualization, CSV assembly and full GraphML',
        transport='native official API; raw responses and failure-only retries; shared six-slot limiter',
        schema_contract='source extraction assertions and generated conceptualization stored separately; no invented definitions'))
    if offline_prepare:
        return
    transport=Client(out,lock_root)
    concept_phase=False

    def generator():
        client=OpenAI(api_key='unused-native-transport',max_retries=0)
        def create(**kwargs):
            result=transport.complete(kwargs['messages'],kwargs.get('max_tokens') or 8192,cache=concept_phase)
            return ChatCompletion.model_validate(openai_shape(result))
        client.chat.completions.create=create
        model=LLMGenerator(client,model_name=MODEL,backend='custom',max_workers=6,
            default_config=GenerationConfig(max_tokens=8192,temperature=0.0,do_sample=False,seed=SEED))
        if concept_phase:
            model.generate_response=lambda messages,**kwargs:strict_concept_batch(transport,messages,**kwargs)
        return model

    def config():
        return ProcessingConfig(model_path=MODEL,data_directory=str(out/'kg_extraction'),
            filename_pattern='d2l_corrected',output_directory=str(out),max_new_tokens=8192,
            max_workers=6,record=True,allow_empty=True,include_concept=True,batch_size_concept=64)

    local=threading.local()
    def extract(chunk):
        if not hasattr(local,'extractor'):
            local.extractor=KnowledgeGraphExtractor(model=generator(),config=config())
        extractor=local.extractor
        inputs=dict(chunk=chunk,prompts=extractor.prompt_instructions,schema=extractor.result_schema)
        def invoke():
            outputs=[];parsed=[];keys=list(extractor.result_schema)
            for key in keys:
                messages=[[{'role':'system','content':extractor.prompt_instructions['zh-CN']['system']},
                           {'role':'user','content':extractor.prompt_instructions['zh-CN'][key]+'\n'+chunk['text']}]]
                # This is exactly CustomDataLoader.create_batch_instructions for a frozen chunk.
                def stage():
                    value,data=extractor.process_stage(messages,extractor.result_schema[key])
                    text=value[0][0]
                    if not isinstance(json.loads(text),list):
                        raise ValueError('Upstream returned invalid extraction, including exhausted retries')
                    return dict(output=value[0],parsed=data[0])
                result=checkpoint(out/'stages'/f"chunk-{chunk['chunk_index']:04d}-{key}.json",
                    dict(messages=messages,schema=extractor.result_schema[key]),stage)
                outputs.append(result['output']);parsed.append(result['parsed'])
            return extractor.prepare_result_dict(str(chunk['chunk_index']),chunk['text'],
                dict(lang='zh-CN',unit_ids=chunk['unit_ids']),(outputs,parsed),keys)
        result=checkpoint(out/'chunks'/f"chunk-{chunk['chunk_index']:04d}.json",inputs,invoke)
        return chunk,result

    completed={}
    for chunk,result in parallel(extract,chunks):
        completed[chunk['chunk_index']]=result
        write(out/'progress.json',dict(stage='extraction',completed=len(completed),total=len(chunks)))
        if len(completed)%25==0:
            print(f'AutoSchemaKG extraction {len(completed)}/{len(chunks)}',flush=True)
    target=out/'kg_extraction'/'d2l_corrected.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(''.join(json.dumps(completed[c['chunk_index']],ensure_ascii=False)+'\n' for c in chunks))

    # The official conceptualizer samples neighbors and shuffles work. Seed before each replay;
    # cached responses preserve successful generations while interrupted CSV assembly is rebuilt.
    random.seed(SEED)
    concept_phase=True
    extractor=KnowledgeGraphExtractor(model=generator(),config=config())
    extractor.convert_json_to_csv()
    missing=out/'triples_csv'/'missing_concepts_d2l_corrected_from_json.csv'
    expected=list(csv.reader(missing.open()))[1:]
    write(out/'progress.json',dict(stage='conceptualization',expected=len(expected)))
    extractor.generate_concept_csv_temp(language='zh-CN')
    concept_file=out/'concepts'/'concept_shard_0.csv'
    concepts=list(csv.DictReader(concept_file.open()))
    expected_keys={(r[0],r[1].lower()) for r in expected}
    obtained_keys={(r['node'],r['node_type'].lower()) for r in concepts}
    if expected_keys!=obtained_keys or len(concepts)!=len(expected):
        raise ValueError('Conceptualization coverage mismatch')
    for row in concepts:
        validate_concept_response({'choices':[{'message':{'content':row['conceptualized_node']}}]})
    extractor.create_concept_csv()
    extractor.convert_to_graphml()

    # Export native semantic assertions without recasting induced schema as corpus quotations.
    # Full concepts and membership edges remain in native GraphML/CSV and schema.json.
    types=defaultdict(set);evidence=defaultdict(set);triples=[]
    for chunk in chunks:
        result=completed[chunk['chunk_index']];units=chunk['unit_ids']
        for key,kind in [('entity_relation','entity'),('event_relation','event')]:
            for item in result[key+'_dict']:
                s,p,o=[clean_text(item[k]) for k in ('Head','Relation','Tail')]
                triples.append(dict(subject=s,predicate=p,object=o,evidence_unit_ids=units))
                for name in (s,o):types[name].add(kind);evidence[name].update(units)
        for item in result['event_entity_dict']:
            event=clean_text(item['Event']);types[event].add('event');evidence[event].update(units)
            for name in item['Entity']:
                name=clean_text(name);types[name].add('entity');evidence[name].update(units)
                triples.append(dict(subject=event,predicate='is participated by',object=name,
                                    text=f'{event} 由 {name} 参与。',evidence_unit_ids=units))
    concept_map=defaultdict(set)
    for item in concepts:
        concept_map[(item['node'],item['node_type'].lower())].update(
            s.strip() for s in item['conceptualized_node'].split(',') if s.strip())
    native_nodes=list(csv.DictReader((out/'triples_csv/triple_nodes_d2l_corrected_from_json_without_emb.csv').open()))
    native_edges=list(csv.DictReader((out/'triples_csv/triple_edges_d2l_corrected_from_json_without_emb.csv').open()))
    native_triples={(r[':START_ID'],r['relation'],r[':END_ID']) for r in native_edges}
    adapted_triples={(r['subject'],r['predicate'],r['object']) for r in triples
                     if all(r[k] for k in ('subject','predicate','object'))}
    if native_triples!=adapted_triples:
        raise ValueError('Adapted triples differ from official native CSV')
    entities=[]
    for row in native_nodes:
        name=row['name:ID'];kind=row['type'].lower()
        induced=concept_map.get((name,kind),set())
        if not induced:raise ValueError('Native node has no completed conceptualization')
        entities.append(dict(name=name,types=sorted(induced),evidence_unit_ids=sorted(evidence[name])))
    submission,report=submission_from_triples(triples,entity_records=entities,
        benchmark_id='d2l-fullbook-v1',document_id='d2l-zh-official',
        system_id='autoschemakg-m3-full-zh-corrected',system_name='AutoSchemaKG full construction (Chinese)',
        system_version='d0a1666ae662',runtime=usage(out),metadata=read(out/'manifest.json'))
    submission['metadata'].update(schema_artifact='schema.json',native_graph='kg_graphml/d2l_corrected_graph.graphml',
        type_semantics='Upstream induced concepts, not placeholder entity/event labels',
        evaluation_scope='semantic extraction + event participation; induced schema stored separately, not independently evaluated')
    write(out/'schema.json',dict(concepts=concepts,expected=len(expected),covered=len(concepts)))
    write(out/'submission.json',submission);write(out/'adapter-report.json',report)
    validate_export(out)
    write(out/'summary.json',dict(status='complete',chunks=len(chunks),concepts=len(concepts),
        expected_concepts=len(expected),usage=usage(out),
        assertions=len(submission['documents'][0]['assertions'])))
    (out/'.finished').write_text(str(time.time())+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--lock-root',type=Path,required=True);p.add_argument('--limit',type=int)
    p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    run(a.out,a.lock_root,a.limit,a.prepare_only)
