#!/bin/bash
# U14 bridge with a patch stack: the oh61-v7 window cohort and master's bms/src/adapter are copied into the generation
# directory, the listed patches are applied in order, then the baseline recipe (../2026-10-02-u14-bridge-baseline/
# build_u14_bridge.sh, fn03 = the 846 reconstruction) builds it. Log teed by the baseline script into $GEN/logs/.
#
#   GEN=<dir> build_r1r3.sh <patch> [<patch> ...]
#   win-*.patch      applies inside the window cohort  (paths a/<file>)
#   adapter-*.patch  applies inside bms/src/adapter    (paths a/framework/...)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
WS=$(cd "$repo/.." && pwd)
[ -n "${WORKSPACES:-}" ] && WS=$WORKSPACES
: "${GEN:?set GEN to a fresh generation directory}"
[ ! -e "$GEN/src" ] || { echo "GEN $GEN already has sources; use a fresh directory" >&2; exit 2; }
INP=$WS/westlake-inputs
SNAPWIN=$INP/sources/oh61-v7-b2133b5b-f6a498d1/framework/window/jni
mkdir -p "$GEN/src" "$GEN/window-jni" "$GEN/logs"
git -C "$repo" archive "${REF:-master}" bms/src/adapter | tar -x -C "$GEN/src"
git -C "$repo" rev-parse "${REF:-master}" > "$GEN/src/COMMIT"
cp "$SNAPWIN"/* "$GEN/window-jni/"
rm -f "$GEN/window-jni/oh_anativewindow_shim.cpp.bak-unity"
{
    echo "[r1r3] $(date -Iseconds) source commit $(cat "$GEN/src/COMMIT")"
    for p in "$@"; do
        case "$(basename "$p")" in
            win-*) dir=$GEN/window-jni ;;
            adapter-*) dir=$GEN/src/bms/src/adapter ;;
            *) echo "[r1r3] unknown patch prefix: $p" >&2; exit 2 ;;
        esac
        echo "[r1r3] apply $(basename "$p") $(shasum -a 256 "$p" | cut -c1-16)"
        patch -p1 --forward --no-backup-if-mismatch -d "$dir" < "$p"
    done
} 2>&1 | tee "$GEN/logs/patches-$(date +%Y%m%dT%H%M%S).log"
GEN=$GEN WINDOW_ROOT=$GEN/window-jni FN03_ROOT=$INP/sources/fn03-core-846-recon-v1 \
    bash "$repo/benchmark/2026-10-02-u14-bridge-baseline/build_u14_bridge.sh"
