#!/usr/bin/env bash
set -uo pipefail

benchmark_root=/home/likefallwind/code/llm-graph-benchmark
baseline_root=/home/likefallwind/code/llm-graph-baselines/kg-gen
study_root="$benchmark_root/studies/d2l-open-baselines-20260820"
run_dir="$study_root/runs/kggen-deepseek-v4-flash-exact27"
run_log="$run_dir/run.log"
run_started="$run_dir/.started"
run_finished="$run_dir/.finished"
run_exit="$run_dir/.exit"
gateway_repo=/home/likefallwind/code/apigateway
gateway_port=18111
gateway_base="http://127.0.0.1:${gateway_port}/v1"
gateway_pid=""
run_rc=130

record_exit() {
    raw_status=$?
    if [[ -n "$gateway_pid" ]] && kill -0 "$gateway_pid" 2>/dev/null; then
        kill -TERM "$gateway_pid" 2>/dev/null || true
        wait "$gateway_pid" 2>/dev/null || true
    fi
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

(
    cd "$gateway_repo" || exit 96
    exec env HOST=127.0.0.1 PORT="$gateway_port" \
        UV_CACHE_DIR="$run_dir/cache/uv" \
        STATS_FILE="$run_dir/gateway-usage-live.json" \
        uv run python -m app
) >> "$run_dir/gateway.log" 2>&1 &
gateway_pid=$!
for _ in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:${gateway_port}/healthz" >/dev/null 2>&1; then
        break
    fi
    if ! kill -0 "$gateway_pid" 2>/dev/null; then
        echo "dedicated gateway exited during startup" >> "$run_log"
        exit 96
    fi
    sleep 0.5
done
if ! curl -fsS "http://127.0.0.1:${gateway_port}/healthz" >/dev/null 2>&1; then
    echo "dedicated gateway did not become healthy" >> "$run_log"
    exit 96
fi

"$baseline_root/.venv/bin/python" -u \
    "$study_root/run_kggen.py" \
    --corpus "$study_root/corpus/chunks.jsonl" \
    --benchmark-id d2l-exact27-pilot-v1 \
    --document-id d2l-zh-official \
    --kggen-repo "$baseline_root" \
    --out-dir "$run_dir" \
    --model openai/deepseek-v4-flash \
    --api-base "$gateway_base" \
    --api-key-file /home/likefallwind/code/apigateway/.env \
    --api-key-name GATEWAY_KEYS \
    --system-id kggen-deepseek-v4-flash \
    --max-tokens 8192 >> "$run_log" 2>&1
run_rc=$?

if [[ "$run_rc" -eq 0 ]]; then
    "$benchmark_root/.venv/bin/python" \
        "$study_root/capture_gateway_usage.py" \
        --base-url "$gateway_base" \
        --api-key-file /home/likefallwind/code/apigateway/.env \
        --api-key-name GATEWAY_KEYS \
        --submission "$run_dir/submission.json" \
        --out "$run_dir/gateway-usage.json" >> "$run_log" 2>&1
    run_rc=$?
fi
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
