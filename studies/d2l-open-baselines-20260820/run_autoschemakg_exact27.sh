#!/usr/bin/env bash
set -euo pipefail

study_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "$study_dir/../.." && pwd)"
run_dir="$study_dir/runs/autoschemakg-qwen3-8b-exact27"
autoschema_repo="/home/likefallwind/code/llm-graph-baselines/autoschemakg"
python_bin="/home/likefallwind/code/llm-graph-baselines/kg-gen/.venv/bin/python"
mkdir -p "$run_dir"

PYTHONPATH="$autoschema_repo:$repo_dir/src" "$python_bin" -u \
  "$study_dir/run_autoschemakg.py" \
  --corpus "$study_dir/corpus/chunks.jsonl" \
  --benchmark-id d2l-exact27-pilot-v1 \
  --document-id d2l-zh-official \
  --autoschemakg-repo "$autoschema_repo" \
  --out-dir "$run_dir" \
  --model qwen3:8b \
  --max-tokens 4096

PYTHONPATH="$repo_dir/src" "$python_bin" \
  "$study_dir/evaluate_submission.py" \
  --benchmark "$study_dir/benchmark/benchmark.json" \
  --submission "$run_dir/submission.json" \
  --out-dir "$run_dir/evaluation"
