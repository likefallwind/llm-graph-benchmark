# D2L hybrid retrieval experiment

This study compares the existing frozen `char-ngram-bm25-v1` top-10
fact-recovery candidate set with multilingual E5 top-10 and their deduplicated
union.  The union preserves all BM25 candidates in their original order and
appends only embedding-exclusive candidates, so paired judging isolates
candidate-set expansion rather than reranking.

The experiment intentionally lives outside the dependency-free benchmark core.
It uses the already cached `intfloat/multilingual-e5-small` model and records
its exact Hugging Face revision in the output manifest.

Run the retrieval stage from the repository root:

```bash
PYTHONPATH=src /home/likefallwind/miniconda3/bin/python \
  studies/d2l-hybrid-retrieval-20260903/run_retrieval.py \
  --benchmark outputs/d2l-full1105-vnext-20260826/benchmark.json \
  --submission llm-knowledge-graph-full1105-vnext=outputs/d2l-full1105-vnext-20260826/submission.json \
  --model /home/likefallwind/.cache/huggingface/hub/models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3 \
  --model-id intfloat/multilingual-e5-small@614241f622f5 \
  --out-dir outputs/d2l-hybrid-retrieval-20260903
```

The generated per-system `all-tasks.jsonl` is compatible with the existing
`judge_carb.py` evaluator.  Judge BM25 failures first: existing BM25 `yes`
results remain `yes` under the multi-match recall rule because added unrelated
candidates cannot reduce `covered`.

`embedding-tasks.jsonl` contains the embedding-only top-10 task set for a
separate E5-only score; `all-tasks.jsonl` contains the hybrid union task set.
