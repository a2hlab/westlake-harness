#!/usr/bin/env bash
set -euo pipefail

MODULE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
PROJECT=$(cd "$MODULE/../../.." && pwd -P)
OUT=${WL_PALETTE_HOST_OUT:-$PROJECT/.work/art-palette-oh/host}
case "$OUT" in "$PROJECT"/*) ;; *) echo "output escaped project" >&2; exit 2;; esac
mkdir -p "$OUT"

CC=${CC:-clang}
COMMON=(-std=c11 -O2 -Wall -Wextra -Werror)
"$CC" "${COMMON[@]}" "$MODULE/src/palette_oh.c" \
    "$MODULE/tests/test_palette_oh.c" -o "$OUT/test_palette_oh"
"$OUT/test_palette_oh"

"$CC" "${COMMON[@]}" -DWL_PALETTE_MUTANT_FAKE_SCHED_SUCCESS \
    "$MODULE/src/palette_oh.c" "$MODULE/tests/test_palette_oh.c" \
    -o "$OUT/test_mutant_fake_sched"
set +e
"$OUT/test_mutant_fake_sched" >"$OUT/mutant.stdout" 2>"$OUT/mutant.stderr"
mutant_rc=$?
set -e
test "$mutant_rc" -ne 0
grep -q 'real setpriority/getpriority mapping failed' "$OUT/mutant.stderr"

echo "PASS art_palette_oh_host mutant_fake_success_rejected=1"
