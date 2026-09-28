#!/usr/bin/env bash
# Developer-owned pinned Linux build/test for Fn01.A05. Never issues formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A05_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a05-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A05 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi

PACKAGE_MANAGER_REGRESSION_OUT="$OUT" \
    "$SCRIPT_DIR/run_project_local_regressions.sh"
[[ -s "$OUT/fn01-a05-run/responses.jsonl" ]]
[[ -s "$OUT/fn01-a05-run/expected-matrix.json" ]]
[[ -s "$OUT/fn01-a05-run/before-after.json" ]]
grep -q '"verdict":"READY"' "$OUT/fn01-a05-run/responses.jsonl"
grep -q '"verdict":"INTERRUPTED"' "$OUT/fn01-a05-run/responses.jsonl"
grep -q '"verdict":"PACKAGE_NOT_VISIBLE"' \
    "$OUT/fn01-a05-run/responses.jsonl"
python3 \
    "$PACKAGE_DIR/application_info/tests/application_info_entry_audit.py" \
    | tee "$OUT/fn01-a05-run/android-entry-audit.log"

echo "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A05 formal_verdict=NOT_ISSUED"
