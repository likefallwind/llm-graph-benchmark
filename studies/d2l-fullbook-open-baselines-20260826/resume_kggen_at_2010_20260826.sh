#!/usr/bin/env bash
set -euo pipefail

target_epoch=$(date -d '2026-08-26 20:10:00 +0800' +%s)
now_epoch=$(date +%s)
delay=$((target_epoch - now_epoch))
if [[ "$delay" -gt 0 ]]; then
    sleep "$delay"
fi

exec bash /home/likefallwind/code/llm-graph-benchmark/studies/d2l-fullbook-open-baselines-20260826/run_kggen_minimax_m3_official_full1105.sh
