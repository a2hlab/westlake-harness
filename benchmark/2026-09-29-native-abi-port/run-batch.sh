#!/usr/bin/env bash
set -euo pipefail
T=/Users/zhaoyue/orca/workspaces/westlake-inputs/tools
M=/Users/zhaoyue/orca/workspaces/westlake-harness
python3 "$M/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py" --execute --serial 61b0657200000000000000000324012c --lane cx-t0 --keys anki,fd-netguard,fd-auxio --hdc-cmd "$T/hdc_mac.sh" --lock-cmd "mac $T/board_note.sh" --out /home/zhaoyue/a2hlab/board/b87-abi-vt-r1-61b --run-id b87-abi-vt-r1-61b --launch-only --hilog 20 --shots 5,20
