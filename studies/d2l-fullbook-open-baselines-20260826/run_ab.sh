#!/usr/bin/env bash
# Stage A then stage B of the revised assertion evaluation, serially.
#
# A: re-judge fact_recovery under CaRB split matching (covered / unsupported).
# B: judge a 200-assertion sample on three separate axes.
#
# Both judge scripts skip task_ids already present in their judgments.jsonl,
# so re-running this script resumes rather than duplicates.
set -uo pipefail

root=/home/likefallwind/code/llm-graph-benchmark
study="$root/studies/d2l-fullbook-open-baselines-20260826"
a_out="$root/outputs/d2l-fullbook-carb-a-20260827"
b_tasks="$root/outputs/d2l-fullbook-axes-20260827"
b_out="$root/outputs/d2l-fullbook-axes-b-20260827"
workers=2
log="$root/outputs/run-ab-20260827.log"

mkdir -p "$a_out" "$b_tasks" "$b_out"
say() { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$log"; }

if [[ -z "${MINIMAX_API_KEY:-}" ]]; then
    say "FATAL MINIMAX_API_KEY is required"
    exit 95
fi

cd "$root" || exit 97
export PYTHONPATH="$study"
py="$root/.venv/bin/python"

# ---------- Stage A ----------
say "STAGE A start (fact_recovery, CaRB split matching, workers=$workers)"
a_rc=1
for pass_index in 1 2 3 4 5 6; do
    say "  A pass=$pass_index"
    "$py" -u "$study/judge_carb.py" \
        --source "llm-knowledge-graph-full1105-vnext=$root/outputs/d2l-full1105-vnext-20260826/evaluation" \
        --source "kggen-minimax-m3-official=$root/outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105/evaluation" \
        --source "kggen-minimax-m3-exactdedup=$root/outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105-exactdedup/evaluation" \
        --source "graphrag-fast-default=$root/outputs/d2l-fullbook-open-baselines-20260826/runs/graphrag-fast-full1105/evaluation" \
        --out-dir "$a_out" --workers "$workers" >> "$log" 2>&1
    a_rc=$?
    say "  A pass=$pass_index status=$a_rc"
    [[ "$a_rc" -eq 0 ]] && break
    sleep 15
done
if [[ "$a_rc" -ne 0 ]]; then
    say "STAGE A did not reach a clean pass (status=$a_rc); stopping before B"
    exit 2
fi
say "STAGE A done"

# ---------- Stage B ----------
if [[ ! -s "$b_tasks/axis-tasks.jsonl" ]]; then
    say "STAGE B sampling (200 assertions/system x 3 axes)"
    "$py" -u "$study/sample_assertion_axes.py" \
        --benchmark "$root/outputs/d2l-full1105-vnext-20260826/benchmark.json" \
        --submission "llm-knowledge-graph-full1105-vnext=$root/outputs/d2l-full1105-vnext-20260826/submission.json" \
        --submission "kggen-minimax-m3-official=$root/outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105/submission.json" \
        --submission "kggen-minimax-m3-exactdedup=$root/outputs/d2l-fullbook-open-baselines-20260826/runs/kggen-minimax-m3-official-full1105-exactdedup/submission.json" \
        --submission "graphrag-fast-default=$root/outputs/d2l-fullbook-open-baselines-20260826/runs/graphrag-fast-full1105/submission.json" \
        --out-dir "$b_tasks" --assertions 200 >> "$log" 2>&1 || { say "STAGE B sampling failed"; exit 3; }
fi
say "STAGE B start ($(wc -l < "$b_tasks/axis-tasks.jsonl") tasks, workers=$workers)"
b_rc=1
for pass_index in 1 2 3 4 5 6; do
    say "  B pass=$pass_index"
    "$py" -u "$study/judge_axes.py" \
        --tasks "$b_tasks/axis-tasks.jsonl" \
        --out-dir "$b_out" --workers "$workers" >> "$log" 2>&1
    b_rc=$?
    say "  B pass=$pass_index status=$b_rc"
    [[ "$b_rc" -eq 0 ]] && break
    sleep 15
done
say "STAGE B done status=$b_rc"
exit "$b_rc"
