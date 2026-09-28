#!/usr/bin/env bash
# Targeted developer test for the Fn01.A08 F01 remediation. Never issues PASS.
set -euo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A08_REMEDIATION_OUT:-$ADAPTER_ROOT/.work/fn01-a08-remediation}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A08 remediation output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi
mkdir -p "$OUT"

CC=${CC:-cc}
CXX=${CXX:-c++}
"$CC" -std=c11 -Wall -Wextra -Werror -O2 \
    -I"$PACKAGE_DIR/install_plan/include" \
    -c "$PACKAGE_DIR/install_plan/src/sha256.c" \
    -o "$OUT/sha256.o"
"$CXX" -std=c++17 -Wall -Wextra -Werror -O2 \
    -pthread \
    -I"$PACKAGE_DIR/resource_projection/include" \
    -I"$PACKAGE_DIR/package_layout/include" \
    -I"$PACKAGE_DIR/install_plan/include" \
    "$PACKAGE_DIR/resource_projection/src/resource_projection_v1.cpp" \
    "$PACKAGE_DIR/resource_projection/tests/resource_projection_cleanup_remediation_host_test.cpp" \
    "$OUT/sha256.o" \
    -o "$OUT/resource_projection_cleanup_remediation_host_test"

run_dir="$OUT/run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
"$OUT/resource_projection_cleanup_remediation_host_test" "$run_dir"
test -s "$run_dir/results.jsonl"
test -s "$run_dir/summary.json"
grep -q '"developerTest":"READY_FOR_REVERIFY"' "$run_dir/summary.json"
grep -q '"caseId":"F01-foreign-transaction-rejected".*"verdict":"TRANSACTION_CONFLICT"' \
    "$run_dir/results.jsonl"
grep -q '"caseId":"N02-foreign-request-rejected".*"verdict":"TRANSACTION_CONFLICT"' \
    "$run_dir/results.jsonl"
grep -q '"caseId":"N02-foreign-caller-rejected".*"verdict":"CALLER_SCOPE_MISMATCH"' \
    "$run_dir/results.jsonl"
grep -q '"caseId":"N02-foreign-payload-rejected".*"verdict":"DATA_INCONSISTENT"' \
    "$run_dir/results.jsonl"
grep -q '"caseId":"F01-missing-plan-fail-closed".*"verdict":"DATA_INCONSISTENT"' \
    "$run_dir/results.jsonl"
grep -q '"caseId":"F02-restart-owner-replay".*"verdict":"READY"' \
    "$run_dir/results.jsonl"
grep -q '"caseId":"F01-owner-cleanup".*"verdict":"CLEANED"' \
    "$run_dir/results.jsonl"

echo "A08_REMEDIATION_READY_FOR_REVERIFY formal_verdict=NOT_ISSUED evidence=$run_dir"
