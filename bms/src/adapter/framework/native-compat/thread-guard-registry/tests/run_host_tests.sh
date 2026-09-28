#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
MODULE=$(cd "$SCRIPT_DIR/.." && pwd -P)
PROJECT_ROOT=$(cd "$MODULE/../../../.." && pwd -P)
OUT=$MODULE/out/host
CC=${CC:-clang}

case "$MODULE" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR module escaped project root" >&2; exit 1 ;;
esac

mkdir -p "$OUT/bin" "$OUT/logs" "$OUT/tmp"
export TMPDIR=$OUT/tmp
: >"$OUT/logs/commands.txt"

COMMON=(
    -std=c11
    -Wall
    -Wextra
    -Werror
    -pedantic
    -I"$MODULE/include"
    -I"$MODULE/src"
    "$MODULE/src/thread_guard_registry.c"
    "$MODULE/src/guard_store_host.c"
    "$MODULE/tests/abi_layout_asserts.c"
    "$MODULE/tests/test_thread_guard_registry.c"
    -pthread
)

build()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" "$@" -o "$output" \
        >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" "$@" -o "$output"
}

GOOD=$OUT/bin/test_good
build "$GOOD"
"$GOOD" >"$OUT/logs/good.stdout" 2>"$OUT/logs/good.stderr"

: >"$OUT/logs/stress.stdout"
: >"$OUT/logs/stress.stderr"
iteration=1
while [[ $iteration -le 20 ]]; do
    "$GOOD" >>"$OUT/logs/stress.stdout" 2>>"$OUT/logs/stress.stderr"
    iteration=$((iteration + 1))
done

ASAN_UBSAN=$OUT/bin/test_asan_ubsan
build "$ASAN_UBSAN" -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$ASAN_UBSAN" >"$OUT/logs/asan_ubsan.stdout" \
    2>"$OUT/logs/asan_ubsan.stderr"

TSAN=$OUT/bin/test_tsan
build "$TSAN" -fsanitize=thread -fno-omit-frame-pointer
TSAN_OPTIONS=halt_on_error=1 \
    "$TSAN" >"$OUT/logs/tsan.stdout" 2>"$OUT/logs/tsan.stderr"

MUTANTS=(
    WLTG_MUTANT_FIXED_FALLBACK
    WLTG_MUTANT_READY_BEFORE_RECEIPT
    WLTG_MUTANT_SKIP_OWNER_BOUNDS
    WLTG_MUTANT_ALLOW_TICKET_REPLAY
    WLTG_MUTANT_ALLOW_CREATOR_AS_GUEST
    WLTG_MUTANT_PER_THREAD_GUARD
    WLTG_MUTANT_AUDIT_CAP_512
)
for mutant in "${MUTANTS[@]}"; do
    binary=$OUT/bin/test_$mutant
    build "$binary" -D"$mutant"
    if "$binary" >"$OUT/logs/$mutant.stdout" \
        2>"$OUT/logs/$mutant.stderr"; then
        echo "ERROR dangerous mutant survived: $mutant" >&2
        exit 1
    fi
done

{
    printf 'status=build_pass\n'
    printf 'implementation=real_impl_not_product_activated\n'
    printf 'host=%s\n' "$(uname -srm)"
    printf 'compiler=%s\n' "$($CC --version | sed -n '1p')"
    printf 'good_suite_sha256=%s\n' \
        "$(shasum -a 256 "$GOOD" | awk '{print $1}')"
    printf 'tests=16\n'
    printf 'concurrent_threads=24\n'
    printf 'stress_iterations=20\n'
    printf 'mutants_killed=%s\n' "${#MUTANTS[@]}"
    printf 'asan_ubsan=pass\n'
    printf 'tsan=pass\n'
    printf 'device_verified=false\n'
    printf 'product_activation=false\n'
} >"$OUT/result.env"

echo "PASS thread-guard registry host tests=16 threads=24 mutants_killed=${#MUTANTS[@]} sanitizers=3"
