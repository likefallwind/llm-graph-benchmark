# Open-baseline results

## Completed: Microsoft GraphRAG Fast

The released Fast/NLP route completed all 27 frozen source chunks in 25.5
seconds. After upstream pruning and finalization it retained 8 entities and one
co-occurrence relationship. The submission and benchmark both pass schema and
provenance validation.

| Dimension | Pass / decided | Pass rate | 95% Wilson interval |
|---|---:|---:|---:|
| Entity admission | 4 / 8 | 0.500 | [0.215, 0.785] |
| Entity typing | 0 / 8 | 0.000 | [0.000, 0.324] |
| Entity definition grounding | 0 / 8 | 0.000 | [0.000, 0.324] |
| Assertion grounding | 1 / 1 | 1.000 | [0.207, 1.000] |
| Frozen fact recovery | 0 / 1 | 0.000 | [0.000, 0.793] |
| Book QA | 0 / 1 | 0.000 | [0.000, 0.793] |

The sole assertion is a correctly evidenced `Image`/`PIL` co-occurrence, so its
1/1 result must not be read as broad relation quality. The official
`regex_english` extractor retained only English fragments from this Chinese
book; four sampled entities were invalid command/link/passage-ID artifacts, and
all entities lacked definitions and semantic types.

## Excluded smoke run

The initial local KGGen `qwen3:8b` run was manually stopped after the model was
judged too weak for a persuasive comparison. Its partial raw artifacts are
retained for auditability but excluded from every headline comparison. No
AutoSchemaKG Qwen run was started.

## Formal LLM track

- Model: API Gateway `deepseek-v4-flash` for both KGGen and AutoSchemaKG.
- Scope: the same immutable 27 chunks and 164 source passages.
- Execution: sequential, to avoid cross-method contention and make the Gateway
  usage delta attributable to one method at a time.
- Credentials: loaded at runtime from the Gateway's untracked `.env`; no key is
  copied into this repository or run metadata.

The final comparison will add the same structural, blind entity/assertion,
identity, frozen fact-recovery, and Book-QA outputs for both LLM baselines.
