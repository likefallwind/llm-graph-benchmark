#!/usr/bin/env bash
set -uo pipefail

benchmark_root=/home/likefallwind/code/llm-graph-benchmark
baseline_root=/home/likefallwind/code/llm-graph-baselines/graphrag
runner_root="$benchmark_root/studies/d2l-open-baselines-20260820"
artifact_root="$benchmark_root/outputs/d2l-fullbook-open-baselines-20260826"
run_dir="$artifact_root/runs/graphrag-fast-full1105"
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
if [[ -e "$run_finished" ]]; then
    echo "GraphRAG Fast full-book run is already finished: $run_finished"
    run_rc=0
    exit 0
fi
date -Is > "$run_started"
cd "$benchmark_root"
PYTHONPATH="$benchmark_root/src" \
    "$baseline_root/.venv/bin/python" \
    "$runner_root/run_graphrag_fast.py" \
    --corpus "$artifact_root/corpus/chunks.jsonl" \
    --benchmark-id d2l-fullbook-v1 \
    --document-id d2l-zh-official \
    --graphrag-repo "$baseline_root" \
    --out-dir "$run_dir" >> "$run_log" 2>&1
run_rc=$?
if [[ "$run_rc" -ne 0 ]]; then
    exit "$run_rc"
fi

"$benchmark_root/.venv/bin/python" \
    "$runner_root/evaluate_submission.py" \
    --benchmark "$benchmark_root/outputs/d2l-full1105-vnext-20260826/benchmark.json" \
    --submission "$run_dir/submission.json" \
    --out-dir "$run_dir/evaluation" >> "$run_log" 2>&1
run_rc=$?
if [[ "$run_rc" -eq 0 ]]; then
    date -Is > "$run_finished"
fi
exit "$run_rc"
