#!/usr/bin/env bash
# Developer-owned pinned Linux build/test for Fn01.A03. Never issues formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A03_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a03-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A03 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi

PACKAGE_MANAGER_REGRESSION_OUT="$OUT" \
    "$SCRIPT_DIR/run_project_local_regressions.sh"

[[ -s "$OUT/fn01-a03-run/receipts.jsonl" ]]
[[ -s "$OUT/fn01-a03-run/fixture-provenance.json" ]]
[[ -s "$OUT/fn01-a03-run/variants.sha256" ]]
grep -q '"verdict":"PARSED"' "$OUT/fn01-a03-run/receipts.jsonl"
grep -q '"verdict":"DECLARATION_CONFLICT"' \
    "$OUT/fn01-a03-run/receipts.jsonl"
grep -q '"verdict":"DIGEST_MISMATCH"' "$OUT/fn01-a03-run/receipts.jsonl"
grep -q '"verdict":"INTERRUPTED"' "$OUT/fn01-a03-run/receipts.jsonl"

echo "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A03 formal_verdict=NOT_ISSUED"
