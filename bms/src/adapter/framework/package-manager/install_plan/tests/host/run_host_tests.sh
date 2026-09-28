#!/usr/bin/env bash
# run_host_tests.sh — build (ASan/UBSan) + run the HP-2 install-plan host
# oracle test suite.
#
# Usage:
#   ./run_host_tests.sh
#   HOST_CFLAGS="-DMUTANT_MULTI_APK" ./run_host_tests.sh     # mutant build (T022/T023)
#
# New fixture/test files (fixtures_us1.c, test_us1.c, fixtures_us2.c,
# test_us2.c, ...) are picked up automatically as long as they are placed
# directly in tests/host/ (this directory) — no edit to this script is
# needed when Phase 3/4 (tasks.md) add them.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"   # .../L03.install-package/work
INCLUDE_DIR="$WORK_DIR/include"
SRC_DIR="$WORK_DIR/src"
TEST_DIR="$SCRIPT_DIR"
BUILD_DIR="$TEST_DIR/.build"
BIN="$BUILD_DIR/install_plan_host_test"

CC="${CC:-cc}"

mkdir -p "$BUILD_DIR"

# All judgment-logic sources (install_plan.c, sha256.c, ...).
shopt -s nullglob
SRC_FILES=("$SRC_DIR"/*.c)
# All test-harness/fixture/scenario sources living directly in tests/host/
# (install_plan_host_test.c, fixtures.c, and later test_us1.c/test_us2.c/
# fixtures_us1.c/fixtures_us2.c).
TEST_FILES=("$TEST_DIR"/*.c)
shopt -u nullglob

if [ "${#SRC_FILES[@]}" -eq 0 ]; then
    echo "run_host_tests.sh: no sources found under $SRC_DIR" >&2
    exit 2
fi
if [ "${#TEST_FILES[@]}" -eq 0 ]; then
    echo "run_host_tests.sh: no test sources found under $TEST_DIR" >&2
    exit 2
fi

CFLAGS=(-std=c11 -Wall -Wextra -fsanitize=address,undefined -fno-omit-frame-pointer -g
        -I"$INCLUDE_DIR" -I"$TEST_DIR")

# HOST_CFLAGS lets callers pass extra compile-time flags (e.g. a mutant
# switch like -DMUTANT_MULTI_APK, research.md R6) without editing this
# script. Intentionally word-split (unquoted) so a space-separated flag
# list works.
if [ -n "${HOST_CFLAGS:-}" ]; then
    # shellcheck disable=SC2206
    EXTRA_FLAGS=(${HOST_CFLAGS})
    CFLAGS+=("${EXTRA_FLAGS[@]}")
fi

echo "+ $CC ${CFLAGS[*]} ${SRC_FILES[*]} ${TEST_FILES[*]} -o $BIN"
"$CC" "${CFLAGS[@]}" "${SRC_FILES[@]}" "${TEST_FILES[@]}" -o "$BIN"

echo "+ $BIN"
"$BIN"
