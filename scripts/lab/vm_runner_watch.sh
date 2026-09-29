#!/bin/bash
# Outer-loop sentinel for batch runners a lane left running in the a2hlab VM.
# Exits (so the outer loop wakes) as soon as a watched log gains a Traceback it did not have when the
# watch started, printing the log tail. Lanes that idle while "their monitor" waits have missed dead
# runners twice (B4 #32 lock hiccup, #38 FileExistsError/TypeError), so the outer loop watches too.
#   vm_runner_watch.sh [--interval S] '<glob under the VM, e.g. /home/zhaoyue/a2hlab/board/b4-*.log>'
set -euo pipefail
interval=60
[ "${1:-}" = --interval ] && { interval=$2; shift 2; }
glob=${1:?usage: vm_runner_watch.sh [--interval S] '<VM log glob>'}
count() { orb -m a2hlab bash -c "for f in $glob; do [ -f \"\$f\" ] && echo \"\$f \$(grep -c Traceback \"\$f\")\"; done" 2>/dev/null || true; }
base=$(count)
while sleep "$interval"; do
  cur=$(count)
  while read -r f n; do
    [ -n "$f" ] || continue
    b=$(printf '%s\n' "$base" | awk -v f="$f" '$1==f{print $2}')
    if [ "${n:-0}" -gt "${b:-0}" ]; then
      echo "VM-RUNNER-TRACEBACK $f ($(date +%H:%M:%S))"
      orb -m a2hlab tail -15 "$f"
      exit 0
    fi
  done <<< "$cur"
done
