"""Public KGGen LM_BASED normalization, with bounded scheduling and lineage."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import random
import sys
import threading
import time

from common import (BENCH, UPSTREAM, CORPUS, MODEL, SEED, Client, checkpoint,
                    digest, freeze, map_kggen_relations, read, rows, sha, usage, write, validate_export, openai_shape)


def run(out, lock_root, limit=None, offline_prepare=False):
    import dspy
    import numpy as np
    from openai.types.chat import ChatCompletion
    from kg_gen import KGGen
    from kg_gen.models import Graph
    from kg_gen.steps._3_deduplicate import DeduplicateMethod
    import kg_gen.utils.llm_deduplicate as module
    from llm_graph_benchmark.adapters.triples import submission_from_triples

    random.seed(SEED)
    np.random.seed(SEED)
    out.mkdir(parents=True,exist_ok=True)
    historical = BENCH/'outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105'
    chunks = rows(CORPUS)
    if limit:
        chunks = chunks[:limit]
    raw_triples = []
    graphs = []
    hashes = {}
    for chunk in chunks:
        path = historical/'chunks'/f"chunk-{chunk['chunk_index']:04d}.json"
        old = read(path)
        if old['status'] != 'done' or old['unit_ids'] != chunk['unit_ids']:
            raise ValueError('Incomplete or mismatched historical extraction')
        hashes[str(path)] = sha(path)
        graph = Graph.model_validate(old['graph'])
        graph.entity_metadata = {name:set(chunk['unit_ids']) for name in graph.entities}
        graphs.append(graph)
        raw_triples.extend(dict(subject=s,predicate=p,object=o,evidence_unit_ids=chunk['unit_ids'])
                           for s,p,o in sorted(graph.relations))
    embedding = Path('/home/likefallwind/.cache/huggingface/hub/models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3')
    freeze(out/'manifest.json',dict(method='KGGen', public_method='DeduplicateMethod.LM_BASED',
        upstream_commit='6259b4c71523ceae75dafb4acec2eb833bef8f8e', model=MODEL,
        seed=SEED, hash_seed=os.environ.get('PYTHONHASHSEED'), corpus_sha256=sha(CORPUS),
        chunks=len(chunks), extraction_hashes=hashes, embedding=str(embedding),
        semantics='Official aggregate and LM_BASED deduplication; multilingual retrieval_model public parameter. No SemHash stage.',
        changes=['transport only MiniMax official', 'executor 64 to 6',
                 'checkpoint successful clusters; fail if upstream swallowed any exception',
                 'exact relation lineage replaces endpoint intersection evidence']))
    if offline_prepare:
        write(out/'prepared.json',dict(chunks=len(chunks),raw_triples=len(raw_triples)))
        return
    transport = Client(out,lock_root)

    class NativeLM(dspy.BaseLM):
        forward_contract='legacy'
        def forward(self,prompt=None,messages=None,**kwargs):
            response=transport.complete(messages or [{'role':'user','content':prompt}])
            return ChatCompletion.model_validate(openai_shape(response))

    kg=KGGen(model='openai/'+MODEL,api_key='unused-native-transport',
             retrieval_model=str(embedding),temperature=0,max_tokens=8192)
    kg.lm=NativeLM(model='openai/'+MODEL,temperature=0,max_tokens=8192,cache=False)
    aggregate=kg.aggregate(graphs)
    write(out/'aggregate.json',aggregate.model_dump(mode='json'))

    class BoundedExecutor(ThreadPoolExecutor):
        def __init__(self,max_workers=6,**kwargs):
            super().__init__(max_workers=min(max_workers,6),**kwargs)

    module.ThreadPoolExecutor=BoundedExecutor
    # Preserve parsed item decisions within a cluster, so a later API/parse failure
    # never rerolls already valid aliases and duplicate decisions on resume.
    predict_forward=dspy.Predict.forward
    def durable_predict(self,**kwargs):
        inputs=dict(instructions=self.signature.instructions,kwargs=kwargs)
        def invoke():return predict_forward(self,**kwargs).toDict()
        result=checkpoint(out/'decisions'/(digest(inputs)+'.json'),inputs,invoke)
        return dspy.Prediction(**result)
    dspy.Predict.forward=durable_predict
    original=module.LLMDeduplicate.deduplicate_cluster
    failures=[]
    progress_lock=threading.Lock()
    completed=0

    def durable_cluster(self,cluster,type='node'):
        nonlocal completed
        inputs=dict(type=type,cluster=cluster)
        path=out/'clusters'/(digest(inputs)+'.json')
        def invoke():
            items,mapping=original(self,cluster,type)
            return dict(items=sorted(items),mapping={k:sorted(v) for k,v in mapping.items()})
        try:
            result=checkpoint(path,inputs,invoke)
            with progress_lock:
                completed+=1
                write(out/'progress.json',dict(stage='llm_normalization',completed_clusters=completed))
            return set(result['items']),{k:set(v) for k,v in result['mapping'].items()}
        except Exception as exc:
            failures.append(str(exc))
            raise
    module.LLMDeduplicate.deduplicate_cluster=durable_cluster
    final=kg.deduplicate(aggregate,method=DeduplicateMethod.LM_BASED)
    if failures:
        raise RuntimeError(f'{len(failures)} failed clusters; incomplete graph not exported')
    graph=final.model_dump(mode='json')
    triples,lineage=map_kggen_relations(raw_triples,graph)
    write(out/'graph.json',graph)
    write(out/'claim-lineage.json',lineage)
    entities=[dict(name=name,evidence_unit_ids=sorted((final.entity_metadata or {}).get(name,set())),
                   aliases=sorted((final.entity_clusters or {}).get(name,set())-{name}))
              for name in sorted(final.entities)]
    submission,report=submission_from_triples(triples,entity_records=entities,
        benchmark_id='d2l-fullbook-v1',document_id='d2l-zh-official',
        system_id='kggen-m3-lm-based-zh-corrected',system_name='KGGen LM-based normalization (multilingual)',
        system_version='6259b4c71523',runtime=usage(out),metadata=read(out/'manifest.json'))
    write(out/'submission.json',submission)
    write(out/'adapter-report.json',report)
    validate_export(out)
    write(out/'summary.json',dict(status='complete',chunks=len(chunks),
        entities=len(submission['documents'][0]['entities']),assertions=len(submission['documents'][0]['assertions']),
        normalization_usage=usage(out),historical_extraction_usage=read(historical/'run-report.json')['usage']))
    (out/'.finished').write_text(str(time.time())+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--lock-root',type=Path,required=True);p.add_argument('--limit',type=int)
    p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    run(a.out,a.lock_root,a.limit,a.prepare_only)
