#!/usr/bin/env bash
set -uo pipefail

benchmark_root=/home/likefallwind/code/llm-graph-benchmark
autoschema_repo=/home/likefallwind/code/llm-graph-baselines/autoschemakg
python_bin=/home/likefallwind/code/llm-graph-baselines/kg-gen/.venv/bin/python
runner_root="$benchmark_root/studies/d2l-open-baselines-20260820"
artifact_root="$benchmark_root/outputs/d2l-fullbook-open-baselines-20260826"
run_dir="$artifact_root/runs/autoschemakg-minimax-m3-official-full1105"
gateway_base="http://127.0.0.1:8111/v1"
gateway_env="/home/likefallwind/code/apigateway/.env"
run_log="$run_dir/run.log"
run_started="$run_dir/.started"
run_finished="$run_dir/.finished"
run_exit="$run_dir/.exit"
shards=6
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
    echo "AutoSchemaKG full-book run is already finished: $run_finished"
    run_rc=0
    exit 0
fi
# The direct MiniMax account hit its Token Plan rate limit and balance floor
# mid-run, so the remaining chunks go through the local API gateway, which
# passes `minimax-m3` through to the same model generation.
if ! curl -fsS "${gateway_base%/v1}/healthz" >/dev/null 2>&1; then
    echo "API gateway is not reachable at $gateway_base" >> "$run_log"
    run_rc=96
    exit "$run_rc"
fi
if [[ ! -e "$run_started" ]]; then
    date -Is > "$run_started"
fi

export PYTHONPATH="$autoschema_repo:$benchmark_root/src"
export XDG_CACHE_HOME="$run_dir/cache"
export HF_HOME="$run_dir/cache/huggingface"
export HF_DATASETS_CACHE="$run_dir/cache/huggingface/datasets"

common_args=(
    --corpus "$artifact_root/corpus/chunks.jsonl"
    --benchmark-id d2l-fullbook-v1
    --document-id d2l-zh-official
    --autoschemakg-repo "$autoschema_repo"
    --out-dir "$run_dir"
    --model minimax-m3
    --base-url "$gateway_base"
    --api-key-file "$gateway_env"
    --api-key-name GATEWAY_KEYS
    --system-id autoschemakg-minimax-m3-official
    --max-tokens 8192
)

success=0
for pass_index in $(seq 1 8); do
    printf '%s pass=%s starting\n' "$(date -Is)" "$pass_index" >> "$run_log"

    # A failed chunk still leaves a raw file, and the runner skips any chunk
    # whose file exists. Drop failures so the next pass actually retries them.
    #
    # An exhausted API retry is recorded as status=done with a truncated stage
    # output such as "[", so status alone does not separate success from
    # failure. Treat any stage whose output is not a parseable JSON list as a
    # failure. A stage that legitimately returns "[]" is a valid observation and
    # is kept: re-rolling zero-yield chunks would bias extraction rate upward.
    "$python_bin" - "$run_dir/chunks" <<'PY' >> "$run_log" 2>&1
import json, sys
from pathlib import Path

STAGES = ("entity_relation", "event_entity", "event_relation")


def is_complete(path: Path) -> bool:
    row = json.loads(path.read_text(encoding="utf-8"))
    if row.get("status") != "done":
        return False
    result = row.get("result", {})
    for stage in STAGES:
        output = result.get(f"{stage}_output")
        if not isinstance(output, str):
            return False
        try:
            if not isinstance(json.loads(output), list):
                return False
        except json.JSONDecodeError:
            return False
    return True


removed = 0
for path in sorted(Path(sys.argv[1]).glob("chunk-*.json")):
    try:
        if is_complete(path):
            continue
    except Exception:
        pass
    path.unlink()
    removed += 1
print(f"cleared {removed} incomplete chunk files")
PY

    shard_pids=()
    for shard_index in $(seq 0 $((shards - 1))); do
        "$python_bin" -u "$runner_root/run_autoschemakg.py" \
            "${common_args[@]}" \
            --shards "$shards" --shard-index "$shard_index" --no-assemble \
            >> "$run_dir/shard-$shard_index.log" 2>&1 &
        shard_pids+=($!)
    done
    shard_rc=0
    for pid in "${shard_pids[@]}"; do
        wait "$pid" || shard_rc=$?
    done

    "$python_bin" -u "$runner_root/run_autoschemakg.py" \
        "${common_args[@]}" --assemble-only >> "$run_log" 2>&1
    assemble_rc=$?

    failed_chunks=1105
    if [[ -e "$run_dir/run-report.json" ]]; then
        failed_chunks=$("$python_bin" -c \
            'import json,sys; report=json.load(open(sys.argv[1])); print(1105 - report["completed_chunks"])' \
            "$run_dir/run-report.json")
    fi
    printf '%s pass=%s shard_status=%s assemble_status=%s remaining_chunks=%s\n' \
        "$(date -Is)" "$pass_index" "$shard_rc" "$assemble_rc" "$failed_chunks" >> "$run_log"
    if [[ "$assemble_rc" -eq 0 && "$failed_chunks" -eq 0 ]]; then
        success=1
        break
    fi
    sleep 10
done

if [[ "$success" -ne 1 ]]; then
    run_rc=2
    exit "$run_rc"
fi

"$python_bin" "$runner_root/evaluate_submission.py" \
    --benchmark "$benchmark_root/outputs/d2l-full1105-vnext-20260826/benchmark.json" \
    --submission "$run_dir/submission.json" \
    --out-dir "$run_dir/evaluation" >> "$run_log" 2>&1
run_rc=$?
if [[ "$run_rc" -eq 0 ]]; then
    date -Is > "$run_finished"
fi
exit "$run_rc"
