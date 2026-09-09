# D2L BM25 + E5 hybrid retrieval pilot

## Conclusion

On the completed `llm-knowledge-graph` D2L submission, adding the top 10
multilingual-E5 candidates to the existing BM25 top 10 changed one of 48
fact-recovery outcomes:

| Candidate retrieval | yes | no | uncertain | covered / 48 | Wilson 95% CI |
|---|---:|---:|---:|---:|---:|
| BM25 top 10 | 44 | 3 | 1 | 91.7% | 80.4%–96.7% |
| E5 top 10 only | 44 | 4 | 0 | 91.7% | 80.4%–96.7% |
| BM25 top 10 + E5 top 10 union | 45 | 3 | 0 | 93.8% | 83.2%–97.9% |

The paired gain is one probe, or 2.1 percentage points.  The confidence
intervals overlap heavily, so this pilot does not establish a population-level
improvement.  E5 alone ties BM25's aggregate coverage rather than beating it:
the two methods exchange one failure.  This demonstrates complementarity, not
dense-retrieval dominance.  The paired BM25-to-E5 transitions are 43
`yes-to-yes`, three `no-to-no`, one `uncertain-to-yes`, and one `yes-to-no`.

## Frozen setup

- Benchmark: the existing 48 D2L fact probes; no probes were changed or added.
- Submission: `llm-knowledge-graph-full1105-vnext`, 3,309 Assertions.
- Sparse retriever: `char-ngram-bm25-v1`, top 10, `k1=1.2`, `b=0.75`.
- Dense retriever: `intfloat/multilingual-e5-small`, cached Hugging Face revision
  `614241f622f53c4eeff9890bdc4f31cfecc418b3`, normalized 384-dimensional
  embeddings and cosine similarity, top 10.
- Indexed text is identical for both retrieval paths: subject name, predicate,
  object name, Assertion text and scope.  Source passages and Evidence are not
  indexed.
- E5 uses its documented asymmetric prefixes: `query: ` for fact probes and
  `passage: ` for Assertions.
- Union ordering preserves the original BM25 top 10, then appends E5-only
  candidates.  This avoids mixing candidate expansion with a reranking change.

## Retrieval-set comparison

| Metric across 48 probes | Result |
|---|---:|
| Mean BM25/E5 overlap within top 10 | 5.125 Assertions |
| Mean E5-only candidates | 4.875 Assertions |
| Mean union size | 14.875 Assertions |
| Union size range | 11–20 Assertions |
| Candidate-count increase over BM25 | 48.75% |

The two retrievers are complementary but not disjoint.  Most probes share four
to eight candidates; only one probe has zero overlap.

## Changed and unchanged failures

`d2l-v1-f035` changed from `uncertain` to `yes`.  The frozen fact states that
Adam brings together minibatch vectorization, historical-gradient momentum,
per-coordinate scaling and learning-rate adjustment.  BM25 found the momentum
part but missed most of the other Adam-specific links.  E5 added Assertions
covering explicit learning-rate control, momentum, RMSProp-like gradient
rescaling and moving-average gradient statistics.  Under the current CaRB
multi-match rule, the union covers the core fact.

E5 alone lost `d2l-v1-f031`, which BM25 covered.  Its dense candidates recover
the convention that optimization minimizes an objective, but omit the other
half of the probe: maximizing an objective can be converted by negating it and
then minimizing.  BM25's exact lexical match retrieves that transformation.

The three BM25 failures remained failures:

- `d2l-v1-f004`: E5 found facts about regression and independent variables but
  not the definition of regression as modelling their relationship to a
  dependent variable.
- `d2l-v1-f033`: E5 found minibatch-SGD properties but not the full trade-off
  among full-batch, single-sample and minibatch gradient descent.
- `d2l-v1-f014`: E5 did not retrieve the no-padding, stride-one convolution
  output-shape formula.

This pattern is useful: dense retrieval repaired a paraphrastic composition,
but it could not recover facts that the graph appears not to contain.

## Judgment boundary

The baseline labels are the existing MiniMax-M3 CaRB judgments.  Because CaRB
`covered` explicitly ignores unrelated extra candidates, the 44 baseline `yes`
labels are logically monotonic under candidate-set addition and were retained.
All four baseline non-`yes` probes were reviewed against the same source
evidence and rubric by a local Codex pass; the item-level decisions are frozen
in `local-delta-review.jsonl`.  The E5-only candidate sets were independently
reviewed for all 48 probes and frozen in `local-embedding-review.jsonl`.

A full MiniMax-M3 union rerun was attempted but network data egress was not
authorized; its error-only output is not evidence and is excluded.  Therefore
the 93.8% result is an engineering pilot, not a same-judge replicated headline
score.  It should not replace the frozen BM25 result until the union tasks are
judged under an authorized, common evaluator and repeated across the other
systems.

## Recommendation

Keep BM25 top 10 as the frozen comparison baseline and add
`BM25@10 + E5@10 union` as an experimental second retrieval track.  The current
gain is real but small, while candidate volume rises by almost half.  The next
decision point should be a pooled rerun over every completed system with the
same judge, accompanied by per-system lexical-only, dense-only and union
failure attribution.

## Reproduction

Generate candidates using the command in `README.md`, then aggregate the paired
pilot:

```bash
/home/likefallwind/miniconda3/bin/python \
  studies/d2l-hybrid-retrieval-20260903/analyze_results.py \
  --system-id llm-knowledge-graph-full1105-vnext \
  --baseline-pool-map outputs/d2l-fullbook-carb-a-20260827/pool-map.json \
  --baseline-judgments outputs/d2l-fullbook-carb-a-20260827/judgments.jsonl \
  --retrieval-summary outputs/d2l-hybrid-retrieval-20260903/llm-knowledge-graph-full1105-vnext/retrieval-summary.json \
  --delta-review studies/d2l-hybrid-retrieval-20260903/local-delta-review.jsonl \
  --embedding-task-key outputs/d2l-hybrid-retrieval-20260903/llm-knowledge-graph-full1105-vnext/embedding-task-key.jsonl \
  --embedding-review studies/d2l-hybrid-retrieval-20260903/local-embedding-review.jsonl \
  --out outputs/d2l-hybrid-retrieval-20260903/lkg-results.json
```

The ignored output directory contains the exact retrieval rows, union tasks,
submission and model manifest, overlap statistics and machine-readable result.
