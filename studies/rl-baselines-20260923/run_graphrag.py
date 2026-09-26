"""GraphRAG's official LLM graph construction with English auto-tuned prompts."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import random
import time
from types import SimpleNamespace

from common import CORPUS, MODEL, SEED, Client, checkpoint, freeze, read, rows, sha, usage, write, validate_export, parallel


def run(out,lock_root,limit=None,offline_prepare=False):
    import pandas as pd
    import tiktoken
    from graphrag.tokenizer.get_tokenizer import get_tokenizer
    from graphrag.prompt_tune.generator.domain import generate_domain
    from graphrag.prompt_tune.generator.persona import generate_persona
    from graphrag.prompt_tune.generator.entity_relationship import generate_entity_relationship_examples
    from graphrag.prompt_tune.generator.extract_graph_prompt import create_extract_graph_prompt
    from graphrag.prompt_tune.generator.entity_summarization_prompt import create_entity_summarization_prompt
    from graphrag.index.operations.extract_graph.graph_extractor import GraphExtractor
    from graphrag.index.operations.extract_graph.extract_graph import _merge_entities, _merge_relationships
    from graphrag.index.operations.extract_graph.utils import filter_orphan_relationships
    from graphrag.index.operations.summarize_descriptions.summarize_descriptions import summarize_descriptions
    from graphrag.callbacks.noop_workflow_callbacks import NoopWorkflowCallbacks
    from llm_graph_benchmark.adapters.triples import submission_from_triples

    chunks=rows(CORPUS)
    if limit:
        chunks=chunks[:limit]
    out.mkdir(parents=True,exist_ok=True)
    freeze(out/'manifest.json',dict(method='GraphRAG standard LLM graph construction',
        upstream_commit='7bb23cc7f32f47cf618a1ae9cca39a6695f434ae',model=MODEL,
        corpus_sha256=sha(CORPUS),chunks=len(chunks),seed=SEED,language='English',
        prompt_tuning='official domain/persona/example generation; public untyped extraction template',
        max_gleanings=1,summarize_max_length=500,summarize_max_input_tokens=4000,
        scope='official extraction, entity/relationship merging and description summarization; no community QA/report tasks',
        relation_semantics='related_to edge with native relationship description; adapter does not invent typed predicates',
        provenance='exact frozen source chunk IDs, carried by upstream merge; no marker regex reconstruction'))
    if offline_prepare:
        return
    transport=Client(out,lock_root)

    class Completion:
        tokenizer=get_tokenizer()
        def __init__(self,cache=False):self.cache=cache
        async def completion_async(self,messages,**kwargs):
            result=await asyncio.to_thread(transport.complete,messages,8192,self.cache)
            return SimpleNamespace(content=result['choices'][0]['message']['content'])

    def tune():
        sample=random.Random(SEED).sample(chunks,min(15,len(chunks)))
        tokenizer=tiktoken.get_encoding('cl100k_base')
        docs=[tokenizer.decode(tokenizer.encode(c['text'])[:200]) for c in sample]
        async def generate():
            model=Completion(cache=True)
            domain=await generate_domain(model,docs)
            persona=await generate_persona(model,domain)
            examples=await generate_entity_relationship_examples(model,persona,None,docs,'English')
            # The resulting template is formatted again by GraphExtractor. Escape literal
            # braces in inserted examples so code/formulas remain literal input text.
            literal=lambda s:s.replace('{','{{').replace('}','}}')
            prompt=create_extract_graph_prompt(None,list(map(literal,docs)),list(map(literal,examples)),
                                               'English',2000,tokenizer=model.tokenizer)
            summary=create_entity_summarization_prompt(literal(persona),'English')
            return dict(domain=domain,persona=persona,docs=docs,examples=examples,
                        extraction_prompt=prompt,summarization_prompt=summary,
                        sampled_chunk_indices=[c['chunk_index'] for c in sample])
        return asyncio.run(generate())
    prompts=checkpoint(out/'prompts.json',dict(corpus=sha(CORPUS),limit=limit,seed=SEED),tune)

    def extract(chunk):
        def invoke():
            # The public __call__ swallows API failures. Record them and reject the chunk,
            # while keeping genuinely empty parsed outputs as valid observations.
            errors=[]
            extractor=GraphExtractor(Completion(cache=True),prompts['extraction_prompt'],1,
                                     on_error=lambda e,s,d:errors.append(type(e).__name__))
            entities,relations=asyncio.run(extractor(chunk['text'].strip(),[],str(chunk['chunk_index'])))
            if errors:
                raise RuntimeError('Upstream extraction failure: '+','.join(errors))
            return dict(entities=entities.to_dict('records'),relationships=relations.to_dict('records'))
        return chunk,checkpoint(out/'chunks'/f"chunk-{chunk['chunk_index']:04d}.json",
                                dict(chunk=chunk,prompts=prompts),invoke)
    extracted={}
    for chunk,result in parallel(extract,chunks):
        extracted[chunk['chunk_index']]=result
        write(out/'progress.json',dict(stage='extraction',completed=len(extracted),total=len(chunks)))
        if len(extracted)%25==0:
            print(f'GraphRAG extraction {len(extracted)}/{len(chunks)}',flush=True)
    entity_frames=[];relation_frames=[]
    for chunk in chunks:
        result=extracted[chunk['chunk_index']]
        entity_frames.append(pd.DataFrame(result['entities'],columns=['title','type','description','source_id']))
        relation_frames.append(pd.DataFrame(result['relationships'],columns=['source','target','description','source_id','weight']))
    entities=_merge_entities(entity_frames);relationships=_merge_relationships(relation_frames)
    before=len(relationships)
    relationships=filter_orphan_relationships(relationships,entities)
    entities.to_parquet(out/'raw_entities.parquet');relationships.to_parquet(out/'raw_relationships.parquet')
    write(out/'progress.json',dict(stage='summarize_descriptions',entities=len(entities),relationships=len(relationships)))
    entity_summaries,relation_summaries=asyncio.run(summarize_descriptions(
        entities,relationships,NoopWorkflowCallbacks(),Completion(cache=True),500,4000,
        prompts['summarization_prompt'],4))
    # Equivalent to the upstream workflow merge, retaining columns for a valid empty graph.
    relationships=relationships.drop(columns=['description']).merge(
        relation_summaries.reindex(columns=['source','target','description']),on=['source','target'],how='left')
    entities=entities.drop(columns=['description']).merge(
        entity_summaries.reindex(columns=['title','description']),on='title',how='left')
    entities.to_parquet(out/'entities.parquet');relationships.to_parquet(out/'relationships.parquet')
    units={str(c['chunk_index']):c['unit_ids'] for c in chunks}
    def evidence(ids):
        return sorted({p for i in ids for p in units[str(i)]})
    entity_records=[dict(name=row['title'],definition=row['description'],types=[row['type']],
                         evidence_unit_ids=evidence(row['text_unit_ids'])) for row in entities.to_dict('records')]
    triples=[dict(subject=row['source'],predicate='related_to',object=row['target'],
                  text=row['description'],evidence_unit_ids=evidence(row['text_unit_ids']))
             for row in relationships.to_dict('records')]
    submission,report=submission_from_triples(triples,entity_records=entity_records,
        benchmark_id='sutton-barto-2e-rl-book2-v1',document_id='sutton-barto-2e-en-full-structured-v1',
        system_id='graphrag-m3-standard-en-rl',system_name='GraphRAG standard graph construction (English)',
        system_version='7bb23cc7f32f',runtime=usage(out),metadata=read(out/'manifest.json'))
    write(out/'submission.json',submission);write(out/'adapter-report.json',report)
    validate_export(out)
    write(out/'summary.json',dict(status='complete',chunks=len(chunks),usage=usage(out),
        upstream_orphan_relationships_removed=before-len(relationships),
        entities=len(submission['documents'][0]['entities']),assertions=len(submission['documents'][0]['assertions'])))
    (out/'.finished').write_text(str(time.time())+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--lock-root',type=Path,required=True);p.add_argument('--limit',type=int)
    p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    run(a.out,a.lock_root,a.limit,a.prepare_only)
