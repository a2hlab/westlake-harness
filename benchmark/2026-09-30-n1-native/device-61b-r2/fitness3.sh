#!/usr/bin/env bash
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
for n in 1 2 3; do
  python3 "$HERE/run_flutter.py" "n1-r2-d40-fitness-${n}-61b" fd-fitness
  rc=$?
  if [[ $rc -gt 1 ]]; then exit "$rc"; fi
done
