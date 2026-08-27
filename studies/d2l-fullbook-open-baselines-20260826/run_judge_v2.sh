#!/usr/bin/env bash
set -uo pipefail

benchmark_root=/home/likefallwind/code/llm-graph-benchmark
study_root="$benchmark_root/studies/d2l-fullbook-open-baselines-20260826"
out_dir="$benchmark_root/outputs/d2l-fullbook-judge-v2-20260826"
run_log="$out_dir/judge.log"
run_started="$out_dir/.started"
run_finished="$out_dir/.finished"
run_exit="$out_dir/.exit"
run_rc=130

record_exit() {
    raw_status=$?
    if [[ "$run_rc" -eq 130 ]]; then
        run_rc=$raw_status
    fi
    printf '%s status=%s\n' "$(date -Is)" "$run_rc" > "$run_exit"
}
trap record_exit EXIT INT TERM HUP

mkdir -p "$out_dir"
if [[ -e "$run_finished" ]]; then
    echo "pooled judging is already finished: $run_finished"
    run_rc=0
    exit 0
fi
if [[ -z "${MINIMAX_API_KEY:-}" ]]; then
    echo "MINIMAX_API_KEY is required" >> "$run_log"
    run_rc=95
    exit "$run_rc"
fi
if [[ ! -e "$run_started" ]]; then
    date -Is > "$run_started"
fi

cd "$benchmark_root" || exit 97
success=0
for pass_index in $(seq 1 6); do
    printf '%s pass=%s starting\n' "$(date -Is)" "$pass_index" >> "$run_log"
    PYTHONPATH="$study_root" "$benchmark_root/.venv/bin/python" -u \
        "$study_root/judge_tasks.py" \
        --source "llm-knowledge-graph-full1105-vnext=$benchmark_root/outputs/d2l-full1105-vnext-20260826/evaluation" \
        --source "kggen-minimax-m3-official=$benchmark_root/outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105/evaluation" \
        --source "graphrag-fast-default=$benchmark_root/outputs/d2l-fullbook-open-baselines-20260826/runs/graphrag-fast-full1105/evaluation" \
        --source "kggen-minimax-m3-exactdedup=$benchmark_root/outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105-exactdedup/evaluation" \
        --out-dir "$out_dir" \
        --model MiniMax-M3 \
        --judge-id minimax-m3-source-grounded-v2 \
        --workers 6 >> "$run_log" 2>&1
    pass_rc=$?
    printf '%s pass=%s status=%s\n' "$(date -Is)" "$pass_index" "$pass_rc" >> "$run_log"
    if [[ "$pass_rc" -eq 0 ]]; then
        success=1
        break
    fi
    sleep 15
done

if [[ "$success" -ne 1 ]]; then
    run_rc=2
    exit "$run_rc"
fi
date -Is > "$run_finished"
run_rc=0
exit 0
