#!/bin/bash
# U14 bridge M5/M6 variants on the baseline candidate e34de8ab (R1 R2 R3): three patch stacks, each built twice in
# fresh generation directories with ../2026-10-02-u14-bridge-r1r3/build_r1r3.sh (logs teed into each $GEN/logs/).
#   build_m5m6.sh                      -> $WORKSPACES/westlake-inputs/generations/u14-m5m6-{m5,m6,m5m6}-{a,b}
#   WITH_M1=1 [ONLY_M1=1] build_m5m6.sh -> also (or only) u14-m5m6-m1m5m6-{a,b} = + M1 + M5 + M6
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
WS=$(cd "$repo/.." && pwd)
[ -n "${WORKSPACES:-}" ] && WS=$WORKSPACES
P=$repo/benchmark/2026-10-02-u14-bridge-r1r3/patches
BASE=("$P/win-r1-focus-bridge.patch" "$P/win-r2-root-blast.patch" "$P/win-r3-rs-node-holder.patch")
M5=$P/win-m5-dialog-zlevel.patch
M6=$P/adapter-m6-finishing-background.patch
G=$WS/westlake-inputs/generations
for rep in ${ONLY_M1:+}a b; do
    [ -n "${ONLY_M1:-}" ] && break
    for v in m5 m6 m5m6; do
        case $v in
            m5) extra=("$M5") ;;
            m6) extra=("$M6") ;;
            m5m6) extra=("$M5" "$M6") ;;
        esac
        GEN=$G/u14-m5m6-$v-$rep bash "$repo/benchmark/2026-10-02-u14-bridge-r1r3/build_r1r3.sh" "${BASE[@]}" "${extra[@]}"
    done
done
[ -n "${ONLY_M1:-}" ] || for v in m5 m6 m5m6; do
    shasum -a 256 "$G/u14-m5m6-$v-a/out/liboh_adapter_bridge.so" "$G/u14-m5m6-$v-b/out/liboh_adapter_bridge.so"
done
# optional 4th (the dddmodel2 / dialog-Surface case needs M1 under M5): e34de8ab + M1 + M5 + M6, also built twice
if [ "${WITH_M1:-0}" = 1 ]; then
    for rep in a b; do
        GEN=$G/u14-m5m6-m1m5m6-$rep bash "$repo/benchmark/2026-10-02-u14-bridge-r1r3/build_r1r3.sh" "${BASE[@]}" \
            "$P/win-m1-session-slots.patch" "$M5" "$M6"
    done
    shasum -a 256 "$G/u14-m5m6-m1m5m6-a/out/liboh_adapter_bridge.so" "$G/u14-m5m6-m1m5m6-b/out/liboh_adapter_bridge.so"
fi
