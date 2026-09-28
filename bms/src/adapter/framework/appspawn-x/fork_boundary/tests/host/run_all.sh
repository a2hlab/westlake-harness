#!/usr/bin/env bash
# Builds and runs the AppSpawnX fork-boundary protocol oracle's host test suite:
#   1. normal build: every test_*.c, run, summarize PASS/FAIL
#   2. ASan/UBSan build: same tests, must be clean
#   3. mutant matrix: for each MUTANT_* macro, rebuild the one test that targets it and
#      assert the result FLIPS from PASS to FAIL (i.e. the mutant is killed)
#
# Linux-only (prctl(PR_SET_PDEATHSIG) is a Linux syscall) — run inside the OrbStack VM:
#   orb -m westlake-build bash -c 'cd /opt/21.Game/02.unity.cardwords/adapter/framework/appspawn-x/fork_boundary && ./tests/host/run_all.sh'
# (this script resolves its own ROOT from BASH_SOURCE, so it also still works unmodified
#  from the original host-only model tree at /opt/21.Game/02e.AppSpawnX/L04.appspawn-process-birth/work)
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="$ROOT/src"
INC_DIR="$ROOT/include"
TEST_DIR="$ROOT/tests/host"
BUILD_DIR="$ROOT/tests/host/.build"
mkdir -p "$BUILD_DIR"

SRC_FILES=("$SRC_DIR"/epoch_registry.c "$SRC_DIR"/nonce.c "$SRC_DIR"/fork_capability.c \
           "$SRC_DIR"/child_entry.c "$SRC_DIR"/spawn_oracle.c "$TEST_DIR"/fixtures_games.c)

ALL_TESTS=(test_us1_success test_us2_reject_replay test_us2_reject_pidmismatch \
           test_us2_reject_doublefork test_us2_reject_fields test_us3_orphan_reconcile \
           test_us4_concurrent_spawn test_us5_same_request_concurrency \
           test_edge_timeout test_edge_child_error \
           test_edge_fd_leak test_edge_terminal_cleanup test_edge_private_channel)

CC=${CC:-gcc}
CFLAGS_BASE=(-std=c11 -D_GNU_SOURCE -Wall -Wextra -Werror -pthread -I"$INC_DIR" -I"$TEST_DIR")

TOTAL_PASS=0
TOTAL_FAIL=0
FAILED_NAMES=()

build_and_run() {
    local name="$1"; shift
    local extra_flags=("$@")
    local bin="$BUILD_DIR/${name}"
    if ! "$CC" "${CFLAGS_BASE[@]}" ${extra_flags[@]+"${extra_flags[@]}"} \
        "${SRC_FILES[@]}" "$TEST_DIR/${name}.c" -o "$bin" 2>"$BUILD_DIR/${name}.build.log"; then
        echo "[BUILD FAIL] $name"
        cat "$BUILD_DIR/${name}.build.log" >&2
        return 2
    fi
    "$bin" >"$BUILD_DIR/${name}.run.log" 2>&1
    return $?
}

echo "=== Phase 1: normal build ==="
for name in "${ALL_TESTS[@]}"; do
    if build_and_run "$name"; then
        echo "[PASS] $name"
        TOTAL_PASS=$((TOTAL_PASS+1))
    else
        echo "[FAIL] $name"
        cat "$BUILD_DIR/${name}.run.log" >&2
        TOTAL_FAIL=$((TOTAL_FAIL+1))
        FAILED_NAMES+=("$name")
    fi
done

echo ""
echo "=== Phase 2: ASan/UBSan build ==="
ASAN_FAIL=0
for name in "${ALL_TESTS[@]}"; do
    bin="$BUILD_DIR/${name}_asan"
    if ! "$CC" "${CFLAGS_BASE[@]}" -fsanitize=address,undefined -g "${SRC_FILES[@]}" "$TEST_DIR/${name}.c" -o "$bin" 2>"$BUILD_DIR/${name}_asan.build.log"; then
        echo "[ASAN BUILD FAIL] $name"
        cat "$BUILD_DIR/${name}_asan.build.log" >&2
        ASAN_FAIL=$((ASAN_FAIL+1))
        continue
    fi
    if "$bin" >"$BUILD_DIR/${name}_asan.run.log" 2>&1; then
        echo "[ASAN PASS] $name"
    else
        echo "[ASAN FAIL] $name"
        cat "$BUILD_DIR/${name}_asan.run.log" >&2
        ASAN_FAIL=$((ASAN_FAIL+1))
    fi
done

echo ""
echo "=== Phase 3: mutant matrix (each mutant must flip its target test PASS->FAIL) ==="
# mutant_define:target_test
MUTANTS=(
  "MUTANT_FR002_SKIP_NONCE_CHECK:test_us2_reject_replay"
  "MUTANT_FR003_SKIP_EPOCH_RECONCILE:test_us3_orphan_reconcile"
  "MUTANT_FR004_SKIP_PID_RECHECK:test_us3_orphan_reconcile"
  "MUTANT_FR005_SKIP_FIELD_epoch:test_us3_orphan_reconcile"
  "MUTANT_FR005_SKIP_FIELD_pid:test_us2_reject_pidmismatch"
  "MUTANT_FR005_SKIP_FIELD_generation:test_us2_reject_fields"
  "MUTANT_FR005_SKIP_FIELD_specialization:test_us2_reject_fields"
  "MUTANT_FR005_SKIP_FIELD_adapter_entry:test_us2_reject_fields"
  "MUTANT_FR006_REPORT_SUCCESS_ON_FORK:test_us1_success"
  "MUTANT_FR007_ALLOW_DOUBLE_FORK:test_us2_reject_doublefork"
  "MUTANT_FR009_NO_TIMEOUT:test_edge_timeout"
  "MUTANT_FR001_SHARED_CHANNEL:test_edge_private_channel"
  "MUTANT_FR008_LEAK_CHILD_FD_IN_PARENT:test_edge_fd_leak"
)

MUTANT_UNKILLED=0
for entry in "${MUTANTS[@]}"; do
    define="${entry%%:*}"
    target="${entry##*:}"
    bin="$BUILD_DIR/mutant_${define}"
    if ! "$CC" "${CFLAGS_BASE[@]}" -D"${define}" "${SRC_FILES[@]}" "$TEST_DIR/${target}.c" -o "$bin" 2>"$BUILD_DIR/mutant_${define}.build.log"; then
        echo "[MUTANT BUILD FAIL] $define (target $target)"
        cat "$BUILD_DIR/mutant_${define}.build.log" >&2
        MUTANT_UNKILLED=$((MUTANT_UNKILLED+1))
        continue
    fi
    if "$bin" >"$BUILD_DIR/mutant_${define}.run.log" 2>&1; then
        echo "[MUTANT NOT KILLED] $define -> $target still PASSES (should have FAILED)"
        MUTANT_UNKILLED=$((MUTANT_UNKILLED+1))
    else
        echo "[MUTANT KILLED] $define -> $target now fails as expected"
    fi
done

echo ""
echo "=== Summary ==="
echo "normal build: $TOTAL_PASS passed, $TOTAL_FAIL failed (${FAILED_NAMES[*]:-none})"
echo "asan/ubsan:   $((${#ALL_TESTS[@]}-ASAN_FAIL))/${#ALL_TESTS[@]} clean"
echo "mutants:      $((${#MUTANTS[@]}-MUTANT_UNKILLED))/${#MUTANTS[@]} killed"

if [ "$TOTAL_FAIL" -eq 0 ] && [ "$ASAN_FAIL" -eq 0 ] && [ "$MUTANT_UNKILLED" -eq 0 ]; then
    echo "=== ALL GREEN (host-only; device Enforcing/truly-cold DEFER) ==="
    exit 0
else
    echo "=== NOT GREEN ==="
    exit 1
fi
