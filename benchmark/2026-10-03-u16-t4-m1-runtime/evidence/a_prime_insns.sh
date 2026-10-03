#!/bin/bash
# A-prime instruction-level proof (bash; uses process substitution).
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
BASE=/Users/zhaoyue/orca/workspaces/westlake-inputs/generations/u15-runtime-m3-v1/payload/android/lib64/liboh_android_runtime.so
CAND=$HERE/payload/liboh_android_runtime.so
OD=/opt/homebrew/bin/llvm-objdump

norm(){ $OD -d --no-show-raw-insn --start-address=$2 --stop-address=$3 "$1" \
        | tail -n +8 \
        | sed -E 's/^[[:space:]]*[0-9a-f]+:[[:space:]]*//; s/0x[0-9a-f]+/0xADDR/g; s/<[^>]*>//g'; }

echo "== m1_find_own: base 0x1981cc-0x1982ac vs cand 0x198e00-0x198ee0 (normalized)"
diff <(norm "$BASE" 0x1981cc 0x1982ac) <(norm "$CAND" 0x198e00 0x198ee0) \
  && echo "  -> IDENTICAL (addresses/relocations masked)"

echo
echo "== m1_collect_others: base 0x1982ac-0x1983a0 vs cand 0x198ee0-0x198fa8 (normalized)"
diff <(norm "$BASE" 0x1982ac 0x1983a0) <(norm "$CAND" 0x198ee0 0x198fa8) \
  && echo "  -> IDENTICAL (addresses/relocations masked)"
