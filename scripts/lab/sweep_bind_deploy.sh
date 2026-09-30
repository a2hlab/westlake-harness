#!/usr/bin/env bash
# Reusable bind-overlay sweep harness (U6-derived, for U7+). Thin wrapper over the Python core so the
# logic stays unit-testable. On the Mac, `source westlake-inputs/env-mac.sh` first (sha256sum shim).
#   sweep_bind_deploy.sh --self-test                          # off-board unit tests
#   sweep_bind_deploy.sh --dry-run --bind <local>:/dest ...   # print the plan, touch no board
#   sweep_bind_deploy.sh --serial <sn> --bind ... --images-dir <dir> --expected <expected-run.json> \
#       --bms-batch <master bms_batch.py> --manifest <apps.json> --keys <csv|file> --input-root <dir> \
#       --note-cmd <board_note.sh> --board-md <app-lighting.md> \
#       --rollback-runtime-fp 73ecf422dba2 --rollback-boot-fp 0876029078e2 --out <dir>
exec python3 "$(cd -- "$(dirname -- "$0")" && pwd)/sweep_bind_deploy.py" "$@"
