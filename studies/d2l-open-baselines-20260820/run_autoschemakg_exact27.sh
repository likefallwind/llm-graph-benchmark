#!/usr/bin/env bash
set -uo pipefail

study_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "$study_dir/../.." && pwd)"
run_dir="$study_dir/runs/autoschemakg-qwen3-8b-exact27"
run_log="$run_dir/run.log"
run_started="$run_dir/.started"
run_finished="$run_dir/.finished"
run_exit="$run_dir/.exit"
autoschema_repo="/home/likefallwind/code/llm-graph-baselines/autoschemakg"
python_bin="/home/likefallwind/code/llm-graph-baselines/kg-gen/.venv/bin/python"
run_rc=130

record_exit() {
  raw_status=$?
  if [[ "$run_rc" -eq 130 ]]; then
    run_rc=$raw_status
  fi
  printf '%s status=%s\n' "$(date -Is)" "$run_rc" > "$run_exit"
}
trap record_exit EXIT INT TERM HUP

mkdir -p "$run_dir"
if [[ -e "$run_started" || -e "$run_finished" || -e "$run_exit" ]]; then
  echo "refusing to overwrite an existing run; use the Python runner directly to resume" >&2
  exit 98
fi
date -Is > "$run_started"

PYTHONPATH="$autoschema_repo:$repo_dir/src" "$python_bin" -u \
  "$study_dir/run_autoschemakg.py" \
  --corpus "$study_dir/corpus/chunks.jsonl" \
  --benchmark-id d2l-exact27-pilot-v1 \
  --document-id d2l-zh-official \
  --autoschemakg-repo "$autoschema_repo" \
  --out-dir "$run_dir" \
  --model qwen3:8b \
  --max-tokens 4096 >> "$run_log" 2>&1
run_rc=$?

if [[ "$run_rc" -eq 0 ]]; then
  PYTHONPATH="$repo_dir/src" "$python_bin" \
    "$study_dir/evaluate_submission.py" \
    --benchmark "$study_dir/benchmark/benchmark.json" \
    --submission "$run_dir/submission.json" \
    --out-dir "$run_dir/evaluation" >> "$run_log" 2>&1
  run_rc=$?
fi
if [[ "$run_rc" -eq 0 ]]; then
  date -Is > "$run_finished"
fi
exit "$run_rc"
