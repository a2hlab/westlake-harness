#!/bin/bash
# Faithful re-build of the deployed libwestlake_native_abi.so d2053066 with its own committed recipe:
# westlake-harness-bms-deploy benchmark/2026-09-30-n4-native/build-abi.sh (commit 44b8e0b0ad), run from that repo's root
# (the DWARF comp_dir of d2053066), output redirected with FLUTTER_BUILD_OUT. The bms-deploy tree is only read.
#   repro_d2053066.sh <out-dir>      (log teed to <out-dir>/build.log)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
WS=$(cd "$here/../../.." && pwd)
[ -n "${WORKSPACES:-}" ] && WS=$WORKSPACES
BD=$WS/westlake-harness-bms-deploy
OUT=${1:?out dir}
mkdir -p "$OUT"
{
    echo "[repro] $(date -Iseconds) bms-deploy HEAD $(git -C "$BD" rev-parse HEAD) build-abi.sh $(shasum -a 256 "$BD/benchmark/2026-09-30-n4-native/build-abi.sh" | cut -c1-16)"
    for f in native_abi.c bionic_stdio_compat.c native_abi.map; do
        echo "[repro] src $f $(shasum -a 256 "$BD/benchmark/2026-09-30-n4-native/src/$f" | cut -c1-16) git-status:$(git -C "$BD" status --short "benchmark/2026-09-30-n4-native/src/$f" | wc -l | tr -d ' ')"
    done
    cd "$BD" && FLUTTER_BUILD_OUT="$OUT" bash benchmark/2026-09-30-n4-native/build-abi.sh
} 2>&1 | tee "$OUT/build.log"
