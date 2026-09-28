#!/usr/bin/env bash
# Developer-owned host build/test for Fn01.A12. Never issues formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A12_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a12-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A12 output escaped project: $OUT" >&2; exit 2 ;;
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
    -DFN01_ENABLE_REFERENCE_FIXTURES \
    -I"$PACKAGE_DIR/runtime_path_descriptor/include" \
    -I"$PACKAGE_DIR/package_transaction/include" \
    -I"$PACKAGE_DIR/install_plan/include" \
    "$PACKAGE_DIR/runtime_path_descriptor/src/runtime_path_descriptor_v1.cpp" \
    "$PACKAGE_DIR/package_transaction/src/package_transaction.cpp" \
    "$PACKAGE_DIR/runtime_path_descriptor/tests/runtime_path_descriptor_host_test.cpp" \
    "$OUT/sha256.o" \
    -o "$OUT/runtime_path_descriptor_host_test"

run_dir="$OUT/run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
if [[ "${FN01_A12_CASE_SCOPE:-full}" == "dependency-closure" ]]; then
    "$OUT/runtime_path_descriptor_host_test" \
        "$run_dir" --dependency-closure-smoke
else
    "$OUT/runtime_path_descriptor_host_test" "$run_dir"
fi
test -s "$run_dir/responses.jsonl"
test -s "$run_dir/consumer-dry-run.jsonl"
test -s "$run_dir/before-after.json"
test -s "$run_dir/summary.json"
grep -q '"caseId":"P01-alpha".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"F02-process-restart-replay".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"mutationObserved":false' "$run_dir/before-after.json"
if [[ "${FN01_A12_CASE_SCOPE:-full}" == "dependency-closure" ]]; then
    grep -q '"developerTest":"DEPENDENCY_CLOSURE_SMOKE"' \
        "$run_dir/summary.json"
    grep -q '"caseId":"N02-projection-prepared".*"verdict":"PACKAGE_NOT_READY"' \
        "$run_dir/responses.jsonl"
    test "$(wc -l < "$run_dir/responses.jsonl")" -eq 3
    echo "DEPENDENCY_CLOSURE_SMOKE action=Fn01.A12 formal_verdict=NOT_ISSUED evidence=$run_dir"
    exit 0
fi
grep -q '"developerTest":"READY_FOR_HANDOFF"' "$run_dir/summary.json"
grep -q '"caseId":"P02-second-package".*"verdict":"READY"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N01-split-profile".*"verdict":"NOT_SUPPORTED_ARTIFACT_PROFILE"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N02-caller-denied".*"verdict":"NOT_AUTHORIZED"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"N01-reachable-path-outside-policy".*"verdict":"PATH_OUTSIDE_PERMITTED_ROOT"' \
    "$run_dir/responses.jsonl"
grep -q '"caseId":"F01-elf-identity-mismatch".*"verdict":"ELF_IDENTITY_MISMATCH"' \
    "$run_dir/responses.jsonl"

echo "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A12 formal_verdict=NOT_ISSUED evidence=$run_dir"
