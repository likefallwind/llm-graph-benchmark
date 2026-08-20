#!/usr/bin/env bash
set -euo pipefail

study_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "$study_dir/../.." && pwd)"
run_dir="$study_dir/runs/graphrag-fast-exact27"
mkdir -p "$run_dir"

PYTHONPATH="$repo_dir/src" \
  "/home/likefallwind/code/llm-graph-baselines/graphrag/.venv/bin/python" \
  "$study_dir/run_graphrag_fast.py" \
  --corpus "$study_dir/corpus/chunks.jsonl" \
  --benchmark-id d2l-exact27-pilot-v1 \
  --document-id d2l-zh-official \
  --graphrag-repo /home/likefallwind/code/llm-graph-baselines/graphrag \
  --out-dir "$run_dir"

PYTHONPATH="$repo_dir/src" \
  "/home/likefallwind/code/llm-graph-baselines/graphrag/.venv/bin/python" \
  "$study_dir/evaluate_submission.py" \
  --benchmark "$study_dir/benchmark/benchmark.json" \
  --submission "$run_dir/submission.json" \
  --out-dir "$run_dir/evaluation"
