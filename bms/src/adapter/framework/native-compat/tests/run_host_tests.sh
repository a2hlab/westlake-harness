#!/usr/bin/env bash
# Run the state-machine suite and require each dangerous mutant to be killed.

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
MODULE=$(cd "$SCRIPT_DIR/.." && pwd -P)
PROJECT_ROOT=$(cd "$MODULE/../../.." && pwd -P)
OUT=$MODULE/out/host
CC=${CC:-clang}

case "$MODULE" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: module escaped project root" >&2; exit 1 ;;
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
    -DWLNC_TESTING
    -I"$MODULE/include"
    -I"$MODULE/src"
    "$MODULE/src/process_state.c"
    "$MODULE/tests/abi_layout_asserts.c"
    "$MODULE/tests/test_process_state.c"
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
    WLNC_MUTANT_PUBLISH_READY_FIRST
    WLNC_MUTANT_INHERIT_PARENT_READY
    WLNC_MUTANT_ALLOW_LOAD_BEFORE_READY
)
for mutant in "${MUTANTS[@]}"; do
    binary=$OUT/bin/test_$mutant
    build "$binary" -D"$mutant"
    if "$binary" >"$OUT/logs/$mutant.stdout" \
        2>"$OUT/logs/$mutant.stderr"; then
        echo "ERROR: dangerous mutant survived: $mutant" >&2
        exit 1
    fi
done

{
    printf 'status=build_pass\n'
    printf 'host=%s\n' "$(uname -srm)"
    printf 'compiler=%s\n' "$($CC --version | sed -n '1p')"
    printf 'good_suite_sha256=%s\n' "$(shasum -a 256 "$GOOD" | awk '{print $1}')"
    printf 'tests=10\n'
    printf 'mutants_killed=%s\n' "${#MUTANTS[@]}"
    printf 'asan_ubsan=pass\n'
    printf 'tsan=pass\n'
    printf 'device_verified=false\n'
} >"$OUT/result.env"

echo "PASS host state-machine tests=10 mutants_killed=${#MUTANTS[@]} sanitizers=3"
