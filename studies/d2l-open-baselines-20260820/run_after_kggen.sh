#!/usr/bin/env bash
set -uo pipefail

study_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kggen_dir="$study_dir/runs/kggen-deepseek-v4-flash-exact27"
queue_log="$study_dir/runs/sequential-queue.log"

printf '%s model=deepseek-v4-flash waiting_for=kggen\n' "$(date -Is)" >> "$queue_log"
while [[ ! -e "$kggen_dir/.exit" ]]; do
  sleep 30
done

if ! grep -q 'status=0$' "$kggen_dir/.exit"; then
  printf '%s skipped=autoschemakg reason=kggen_failed\n' "$(date -Is)" >> "$queue_log"
  exit 1
fi

printf '%s starting=autoschemakg\n' "$(date -Is)" >> "$queue_log"
bash "$study_dir/run_autoschemakg_exact27.sh" >> "$queue_log" 2>&1
queue_rc=$?
printf '%s finished=autoschemakg status=%s\n' "$(date -Is)" "$queue_rc" >> "$queue_log"
exit "$queue_rc"
