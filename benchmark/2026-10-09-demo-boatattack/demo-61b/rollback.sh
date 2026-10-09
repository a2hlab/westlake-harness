#!/bin/bash
set -eu
# Requires cx-t0 lock on exact 61b; restores only this journal.
WORKSPACES=${WORKSPACES:?source scripts/lab/env-mac.sh first}
python3 "${WORKSPACES}/westlake-harness-tools-inventory/benchmark/2026-10-09-demo-boatattack/demo-61b/window_hook.py" rollback
