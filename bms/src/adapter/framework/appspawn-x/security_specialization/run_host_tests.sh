#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd -P)
OUT=$SCRIPT_DIR/out/host
CC=${CC:-clang}

case "$SCRIPT_DIR" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: security specialization escaped project root" >&2; exit 1 ;;
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
    -I"$SCRIPT_DIR/include"
    "$SCRIPT_DIR/src/security_specialization.c"
    "$SCRIPT_DIR/tests/test_security_specialization.c"
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

MUTANTS=(
    WLSS_MUTANT_ALLOW_NO_SANDBOX
    WLSS_MUTANT_ALLOW_MISSING_DAC
    WLSS_MUTANT_ALLOW_MISSING_TOKEN
    WLSS_MUTANT_IGNORE_SANDBOX_RESULT
)
for mutant in "${MUTANTS[@]}"; do
    binary=$OUT/bin/test_$mutant
    build "$binary" -D"$mutant"
    if "$binary" >"$OUT/logs/$mutant.stdout" \
        2>"$OUT/logs/$mutant.stderr"; then
        echo "ERROR: dangerous security mutant survived: $mutant" >&2
        exit 1
    fi
done

{
    printf 'status=build_pass\n'
    printf 'classification=control_plane_fixture_not_product_binding\n'
    printf 'tests=29\n'
    printf 'mutants_killed=%s\n' "${#MUTANTS[@]}"
    printf 'asan_ubsan=pass\n'
    printf 'product_activation=false\n'
    printf 'device_verified=false\n'
} >"$OUT/result.env"

echo "PASS OH security specialization host tests=29 mutants_killed=${#MUTANTS[@]}"
