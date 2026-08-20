#!/usr/bin/env bash
set -uo pipefail

benchmark_root=/home/likefallwind/code/llm-graph-benchmark
baseline_root=/home/likefallwind/code/llm-graph-baselines/kg-gen
study_root="$benchmark_root/studies/d2l-open-baselines-20260820"
run_dir="$study_root/runs/kggen-qwen3-8b-exact27"
run_log="$run_dir/run.log"
run_started="$run_dir/.started"
run_finished="$run_dir/.finished"
run_exit="$run_dir/.exit"
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
cd "$benchmark_root" || exit 97

"$baseline_root/.venv/bin/python" -u \
    "$study_root/run_kggen.py" \
    --corpus "$study_root/corpus/chunks.jsonl" \
    --benchmark-id d2l-exact27-pilot-v1 \
    --document-id d2l-zh-official \
    --kggen-repo "$baseline_root" \
    --out-dir "$run_dir" \
    --model ollama_chat/qwen3:8b \
    --max-tokens 4096 >> "$run_log" 2>&1
run_rc=$?

if [[ "$run_rc" -eq 0 ]]; then
    "$benchmark_root/.venv/bin/python" \
        "$study_root/evaluate_submission.py" \
        --benchmark "$study_root/benchmark/benchmark.json" \
        --submission "$run_dir/submission.json" \
        --out-dir "$run_dir/evaluation" >> "$run_log" 2>&1
    run_rc=$?
fi
if [[ "$run_rc" -eq 0 ]]; then
    date -Is > "$run_finished"
fi
exit "$run_rc"
