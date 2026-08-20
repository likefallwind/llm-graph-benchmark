# D2L open-baseline study (2026-08-20)

This study compares public document-to-graph implementations on exactly the same
27 processed D2L chunks (164 immutable Source Passages) as `d2l-exact27-pilot-v1`.

| Method | Upstream | Role in this study |
|---|---|---|
| KGGen (NeurIPS 2025) | `stair-lab/kg-gen` | entity/relation extraction plus released SemHash deduplication |
| AutoSchemaKG (2025) | `HKUST-KnowComp/AutoSchemaKG` | Chinese entity/event triples and schema-oriented construction |
| Microsoft GraphRAG (2024) | `microsoft/graphrag` | Fast/NLP and local-LLM graph extraction |
| EDC (EMNLP 2024) | `clear-nus/edc` | compatibility audit; relation-only canonicalization and legacy stack |

All upstream repositories live under `/home/likefallwind/code/llm-graph-baselines`.
Commit hashes are recorded in run artifacts. No D2L text is sent to an external
API: local Ollama models are used.

Fairness rules: freeze input first, retain raw outputs and provenance, do not
synthesize missing definitions/types/aliases, report deterministic rejection of
invalid triples, and use the same benchmark dimensions for every submission.

## Runnable baselines

- `run_kggen_exact27.sh`: KGGen with local `qwen3:8b`, followed by its released
  SemHash deduplication.
- `run_autoschemakg_exact27.sh`: AutoSchemaKG's three Chinese extraction stages
  with local `qwen3:8b`. Schema conceptualization is deliberately reported as
  out of scope for this extraction-stage comparison.
- `run_graphrag_fast_exact27.sh`: GraphRAG Fast through graph finalization. Its
  released `regex_english` extractor is preserved, so Chinese applicability is
  measured rather than hidden by an evaluator-side substitution.

Each LLM runner writes one durable raw result per frozen source chunk and can be
resumed. `evaluate_submission.py` validates a normalized submission and creates
structural, blind quality, identity, fact-recovery, and book-QA artifacts.
