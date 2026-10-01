#!/usr/bin/env bash
set -u
here=$(cd "$(dirname "$0")" && pwd)
for attempt in 1 2 3; do
  "$here/run-batch.sh" "noice-$attempt" --keys noice --input-root "$HOME/a2hlab/app-inputs-u6" --launch-only
  result=$?
  if [ "$result" -gt 1 ]; then exit "$result"; fi
  # Exit 1 retains observed white/unconfirmed UI; Noice is explicitly not a hard gate.
done
