#!/usr/bin/env bash
# Developer-owned host build/test for Fn01.A07. Never issues formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A07_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a07-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A07 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi
mkdir -p "$OUT"

CXX=${CXX:-c++}
CC=${CC:-cc}
"$CC" -std=c11 -Wall -Wextra -Werror -O2 \
    -I"$PACKAGE_DIR/install_plan/include" \
    -c "$PACKAGE_DIR/install_plan/src/sha256.c" \
    -o "$OUT/sha256.o"
"$CXX" -std=c++17 -Wall -Wextra -Werror -O2 \
    -I"$PACKAGE_DIR/package_layout/include" \
    -I"$PACKAGE_DIR/install_plan/include" \
    "$PACKAGE_DIR/package_layout/src/package_layout_v1.cpp" \
    "$PACKAGE_DIR/package_layout/tests/package_layout_host_test.cpp" \
    "$OUT/sha256.o" \
    -o "$OUT/package_layout_host_test"

run_dir="$OUT/run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
"$OUT/package_layout_host_test" "$run_dir"
test -s "$run_dir/responses.jsonl"
test -s "$run_dir/summary.json"
grep -q '"developerTest":"READY_FOR_HANDOFF"' "$run_dir/summary.json"
grep -q '"caseId":"P01-alpha".*"verdict":"FINALIZED"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N01-symlink-escape".*"verdict":"SYMLINK_ESCAPE"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N01-no-space".*"verdict":"NO_SPACE"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"F02-after-rename-interrupt".*"verdict":"INTERRUPTED"' \
    "$run_dir/responses.jsonl"
grep -q '"verdict":"TRANSACTION_CONFLICT"' "$run_dir/responses.jsonl"

echo "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A07 formal_verdict=NOT_ISSUED evidence=$run_dir"
