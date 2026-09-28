#!/usr/bin/env bash
# Developer-owned host build/test for Fn01.A08. Never issues formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A08_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a08-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A08 output escaped project: $OUT" >&2; exit 2 ;;
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
    -pthread \
    -I"$PACKAGE_DIR/resource_projection/include" \
    -I"$PACKAGE_DIR/package_layout/include" \
    -I"$PACKAGE_DIR/install_plan/include" \
    "$PACKAGE_DIR/resource_projection/src/resource_projection_v1.cpp" \
    "$PACKAGE_DIR/resource_projection/tests/resource_projection_host_test.cpp" \
    "$OUT/sha256.o" \
    -o "$OUT/resource_projection_host_test"

run_dir="$OUT/run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
"$OUT/resource_projection_host_test" "$run_dir"
test -s "$run_dir/responses.jsonl"
test -s "$run_dir/summary.json"
grep -q '"developerTest":"READY_FOR_HANDOFF"' "$run_dir/summary.json"
grep -q '"caseId":"P01-distinct-label-alpha".*"label":"Alpha".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"P01-distinct-label-beta".*"label":"Beta".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"P01-empty-ready".*"payloadKind":"EMPTY".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"P01-policy-limit-readback".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N01-resource-not-found".*"verdict":"RESOURCE_NOT_FOUND"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N01-unsupported-configuration".*"verdict":"UNSUPPORTED_CONFIGURATION"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N01-invalid-payload".*"verdict":"INVALID_RESOURCE_PAYLOAD"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"F02-recover-prepared".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"F01-readback-corruption-clean".*"verdict":"DATA_INCONSISTENT"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N02-cleanup-caller-scope".*"verdict":"CALLER_SCOPE_MISMATCH"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"F01-generation-scoped-cleanup".*"verdict":"CLEANED"' \
    "$run_dir/responses.jsonl"

echo "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A08 formal_verdict=NOT_ISSUED evidence=$run_dir"
