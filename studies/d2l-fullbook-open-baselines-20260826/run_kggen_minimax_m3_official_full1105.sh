#!/usr/bin/env bash
set -uo pipefail

benchmark_root=/home/likefallwind/code/llm-graph-benchmark
baseline_root=/home/likefallwind/code/llm-graph-baselines/kg-gen
runner_root="$benchmark_root/studies/d2l-open-baselines-20260820"
study_root="$benchmark_root/studies/d2l-fullbook-open-baselines-20260826"
artifact_root="$benchmark_root/outputs/d2l-fullbook-open-baselines-20260826"
run_dir="$artifact_root/runs/kggen-minimax-m3-official-full1105"
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
    echo "KGGen full-book run is already finished: $run_finished"
    run_rc=0
    exit 0
fi
if [[ -z "${MINIMAX_API_KEY:-}" ]]; then
    echo "MINIMAX_API_KEY is required for the official MiniMax API" >> "$run_log"
    run_rc=95
    exit "$run_rc"
fi
if [[ ! -e "$run_started" ]]; then
    date -Is > "$run_started"
fi

cd "$benchmark_root" || exit 97
success=0
for pass_index in $(seq 1 8); do
    printf '%s pass=%s starting\n' "$(date -Is)" "$pass_index" >> "$run_log"
    "$baseline_root/.venv/bin/python" -u \
        "$runner_root/run_kggen.py" \
        --corpus "$artifact_root/corpus/chunks.jsonl" \
        --benchmark-id d2l-fullbook-v1 \
        --document-id d2l-zh-official \
        --kggen-repo "$baseline_root" \
        --out-dir "$run_dir" \
        --model openai/MiniMax-M3 \
        --api-base https://api.minimaxi.com/v1 \
        --api-key-env MINIMAX_API_KEY \
        --system-id kggen-minimax-m3-official \
        --max-tokens 8192 \
        --workers 6 >> "$run_log" 2>&1
    pass_rc=$?
    failed_chunks=1105
    if [[ -e "$run_dir/run-report.json" ]]; then
        failed_chunks=$("$benchmark_root/.venv/bin/python" -c \
            'import json,sys; print(json.load(open(sys.argv[1]))["failed_chunks"])' \
            "$run_dir/run-report.json")
    fi
    printf '%s pass=%s status=%s failed_chunks=%s\n' \
        "$(date -Is)" "$pass_index" "$pass_rc" "$failed_chunks" >> "$run_log"
    if [[ "$pass_rc" -eq 0 && "$failed_chunks" -eq 0 ]]; then
        success=1
        break
    fi
    sleep 10
done

if [[ "$success" -ne 1 ]]; then
    run_rc=2
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

