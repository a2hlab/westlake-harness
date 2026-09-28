#!/usr/bin/env bash
# Developer-owned P/N/F/restart suite for Fn01.A10. Never issues formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A10_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a10-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A10 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi
if [[ -e "$OUT" ]]; then
    echo "ERROR: Fn01.A10 host output must be fresh: $OUT" >&2
    exit 2
fi
mkdir -p "$OUT/build" "$OUT/raw"

CXX=${CXX:-c++}
CC=${CC:-cc}
"$CC" -std=c11 -Wall -Wextra -Werror -O2 \
    -I"$PACKAGE_DIR/install_plan/include" \
    -c "$PACKAGE_DIR/install_plan/src/sha256.c" \
    -o "$OUT/build/sha256.o"
"$CXX" -std=c++17 -Wall -Wextra -Werror -O2 -g \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$PACKAGE_DIR/bms_projection/include" \
    -I"$PACKAGE_DIR/install_plan/include" \
    "$PACKAGE_DIR/bms_projection/src/bms_projection_v1.cpp" \
    "$PACKAGE_DIR/bms_projection/tests/bms_projection_host_test.cpp" \
    "$OUT/build/sha256.o" \
    -o "$OUT/build/bms_projection_host_test"

"$OUT/build/bms_projection_host_test" "$OUT/raw/host"
test -s "$OUT/raw/host/responses.jsonl"
test -s "$OUT/raw/host/summary.json"
jq -e \
    '.actionId == "Fn01.A10" and .cases == 26 and .failed == 0 and
     .developerTest == "READY_FOR_VERIFY" and
     .formalVerdict == "NOT_ISSUED"' \
    "$OUT/raw/host/summary.json" >/dev/null
grep -q '"caseId":"P01a-p4-prepared-readback".*"verdict":"PREPARED"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"P01b-controlled-activation".*"verdict":"ACTIVATED"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N01-host-collision".*"verdict":"HOST_COLLISION"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N03-pre-p5-activation-rejected".*"verdict":"ACTIVATION_NOT_AUTHORIZED"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-activation-transaction-owner".*"verdict":"TRANSACTION_MISMATCH"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"F02-post-token-cas-restart".*"verdict":"ACTIVATED"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"F02-interrupted-prepare-intent-bound".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"F02-interrupted-activation-intent-bound".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"F02-concurrent-first-intent-single-winner".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"F02-legacy-receipt-fails-closed".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-closed-replay-caller-input-bound".*"verdict":"CALLER_SCOPE_MISMATCH"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-closed-replay-full-payload-bound".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-closed-activation-replay-bound".*"verdict":"CALLER_SCOPE_MISMATCH"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-request-id-operation-bound".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-policy-version-bound".*"verdict":"INVALID_REQUEST"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-a08-provenance-owner-bound".*"verdict":"TRANSACTION_MISMATCH"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-closed-prepare-receipt-tamper".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"
grep -q '"caseId":"N02-closed-activate-receipt-tamper".*"verdict":"IDEMPOTENCY_CONFLICT"' \
    "$OUT/raw/host/responses.jsonl"

{
    printf 'action=Fn01.A10\n'
    printf 'scope=developer_host_pnf_restart\n'
    printf 'compiler='
    "$CXX" --version | head -n 1
    printf 'package=NOT_RUN\n'
    printf 'deploy=NOT_RUN\n'
    printf 'device=NOT_RUN\n'
    printf 'formal_verdict=NOT_ISSUED\n'
} >"$OUT/raw/environment.txt"
shasum -a 256 \
    "$PACKAGE_DIR/bms_projection/include/bms_projection_v1.h" \
    "$PACKAGE_DIR/bms_projection/src/bms_projection_v1.cpp" \
    "$PACKAGE_DIR/bms_projection/tests/bms_projection_host_test.cpp" \
    "$PACKAGE_DIR/install_plan/src/sha256.c" \
    "$OUT/build/bms_projection_host_test" \
    "$OUT/raw/host/responses.jsonl" \
    "$OUT/raw/host/summary.json" \
    >"$OUT/raw/artifacts.sha256"

echo "DEVELOPER_TEST_READY_FOR_VERIFY action=Fn01.A10 formal_verdict=NOT_ISSUED evidence=$OUT"
