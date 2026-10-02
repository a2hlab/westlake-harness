#!/bin/bash
# U14 hardened-bridge baseline: build liboh_adapter_bridge.so from master's bms/src (fail-loud build scripts 9c14005a01)
# plus the persistent oh61-v7 window/fn03 snapshot (tree f6a498d1), on the Mac with the DevEco OH SDK toolchain
# (FORCE_OH_SDK=1, the route cc-wiki's B1 used). Nothing in a shared .work tree is read-write; every input is copied or
# linked into the generation directory, and the build log is teed there while it runs.
#
#   build_u14_bridge.sh [<master-ref>]        # default master; GEN defaults to $WORKSPACES/westlake-inputs/generations/u14-bridge-v1
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
WS=$(cd "$repo/.." && pwd)
[ -n "${WORKSPACES:-}" ] && WS=$WORKSPACES
REF=${1:-master}
GEN=${GEN:-$WS/westlake-inputs/generations/u14-bridge-v1}
INP=$WS/westlake-inputs
SNAP=$INP/sources/oh61-v7-b2133b5b-f6a498d1
OHR=$INP/oh61-oh-root
SYSLIB=$INP/oh61-link-inputs/system-lib64
KIT=$WS/oh61-bms-kit-b79
GEN_HDR_SRC=$WS/westlake-harness-bms-deploy/bms/src/.work/b68-generation/generated
WLTG_SRC=$WS/westlake-generation-v3-swap-84695d62/payload/android/lib64/libwestlake_thread_guard_registry.so
mkdir -p "$GEN/logs"
LOG=$GEN/logs/build-$(date +%Y%m%dT%H%M%S).log
exec > >(tee "$LOG") 2>&1
echo "[u14] start $(date -Iseconds) ref=$REF commit=$(git -C "$repo" rev-parse "$REF") gen=$GEN"

# 1. immutable source export (master bms/src/adapter) + the oh61-v7 snapshot as the window/fn03 cohort
SRC=$GEN/src
if [ ! -d "$SRC/bms/src/adapter" ]; then
    mkdir -p "$SRC"
    git -C "$repo" archive "$REF" bms/src/adapter | tar -x -C "$SRC"
    git -C "$repo" rev-parse "$REF" > "$SRC/COMMIT"
fi
echo "[u14] source commit $(cat "$SRC/COMMIT")"
( cd "$SNAP" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 ) | shasum -a 256 | cut -c1-16 | sed 's/^/[u14] oh61-v7 snapshot tree /'

# 2. OH_ROOT assembled from the persistent header roots (symlinks; headers only) + board libs as the product packages
OH=$GEN/oh-root
if [ ! -d "$OH" ]; then
    mkdir -p "$OH/third_party" "$OH/out/wukong100/packages/phone/system"
    # base/commonlibrary/foundation: the oh_mirror subsystem dirs, then oh61-bms-kit-b79's for subsystems the mirror
    # lacks (e.g. base/notification/eventhandler inner_api, which the recipe requires for libeventhandler.z)
    # recursive union: a path present in only one tree is linked; a directory present in both becomes a real directory
    # and is merged one level further (oh_mirror wins on file conflicts)
    python3 - "$OH" "$OHR/oh_mirror" "$KIT" <<'PY'
import os, sys
dst, a, b = sys.argv[1:]
def merge(d, x, y):
    os.makedirs(d, exist_ok=True)
    names = set(os.listdir(x)) | (set(os.listdir(y)) if y and os.path.isdir(y) else set())
    for n in sorted(names):
        px, py = os.path.join(x, n), (os.path.join(y, n) if y else None)
        hx, hy = os.path.exists(px), bool(py and os.path.exists(py))
        if hx and hy and os.path.isdir(px) and os.path.isdir(py):
            merge(os.path.join(d, n), px, py)
        elif not os.path.lexists(os.path.join(d, n)):
            os.symlink(px if hx else py, os.path.join(d, n))
for top in ('base', 'commonlibrary', 'foundation'):
    merge(os.path.join(dst, top), os.path.join(a, top), os.path.join(b, top))
PY
    for d in "$OHR/oh_mirror/third_party"/*; do ln -s "$d" "$OH/third_party/$(basename "$d")"; done
    [ -e "$OH/third_party/skia" ] || ln -s "$OHR/oh610_lts_source/third_party/skia" "$OH/third_party/skia"
    for d in gen obj window; do ln -s "$OHR/oh610_lts_source/out/wukong100/$d" "$OH/out/wukong100/$d"; done
    ln -s "$SYSLIB" "$OH/out/wukong100/packages/phone/system/lib64"
fi

# 3. flat link inputs (real files; libc.so = the board's ld-musl-aarch64.so.1, which defines __cfi_slowpath)
LI=$GEN/linkinputs
if [ ! -d "$LI" ]; then
    mkdir -p "$LI"
    cp "$SYSLIB/ld-musl-aarch64.so.1" "$LI/libc.so"
    cp "$SYSLIB/chipset-sdk-sp/libc++.so" "$LI/libc++.so"
    for f in libappkit_native.z.so libsession_manager.z.so libwmutil.z.so libwmutil_base.z.so libeventhandler.z.so; do
        cp "$SYSLIB/platformsdk/$f" "$LI/$f"
    done
fi
GH=$GEN/generated-headers
[ -d "$GH" ] || { mkdir -p "$GH"; cp "$GEN_HDR_SRC/imock_session_manager_interface.h" "$GH/"; }
OUT=$GEN/out
mkdir -p "$OUT"
[ -f "$OUT/libwestlake_thread_guard_registry.so" ] || cp "$WLTG_SRC" "$OUT/"
shasum -a 256 "$LI"/* "$GH"/* "$OUT/libwestlake_thread_guard_registry.so" | sed 's/^/[u14] input /'

# 4. the hardened recipe, verbatim
export BUILD_INNER_INVOKED=1
export ADAPTER_ROOT=$SRC/bms/src/adapter
# WINDOW_ROOT: the window/jni cohort (default the oh61-v7 snapshot; probes point it at a copied b68 cohort)
export OH61_WINDOW_SOURCE_ROOT=${WINDOW_ROOT:-$SNAP/framework/window/jni}
# FN03_ROOT: v1 used the oh61-v7 snapshot's fn03 (dd57a00b); v2 uses the b6-r155 fn03 that matches 84695d62 (1f5986de)
export OH61_ACTIVITY_CORE_ROOT=${FN03_ROOT:-$SNAP/framework/activity/core}
export OH_HEADER_MIRROR=$SNAP/local_oh_headers/oh_mirror
export OH_ROOT=$OH
export OH_SDK=$OHOS_SDK
export FORCE_OH_SDK=1
export OH_LIBCXX_INCLUDE=$KIT/prebuilts/clang/ohos/linux-x86_64/llvm/include/libcxx-ohos/include/c++/v1
export OH61_LINK_INPUTS=$LI
export OH61_GENERATED_HEADERS=$GH
export OVL_OVERRIDE=$SRC/bms/src/adapter/build/oh_headers_631_overlay
export ADAPTER_OUT_DIR=$OUT
export BRIDGE_OBJ_DIR=$GEN/obj
export AOSP_ROOT=$HOME/aosp
export BRIDGE_MINIZIP_DIR=$OHR/minizip
export BRIDGE_LIBZ_A=$OHR/minizip/libz.a
export OH_RESOURCE_MANAGEMENT_ROOT=$KIT/base/global/resource_management
export AOSP_LIB_DIR=$OHR/aosplib
( cd "$OH61_WINDOW_SOURCE_ROOT" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 ) | shasum -a 256 | cut -c1-16 | sed 's/^/[u14] window cohort tree /'
echo "[u14] fn03 $(shasum -a 256 "$OH61_ACTIVITY_CORE_ROOT/fn03_lifecycle_core.cpp" | cut -c1-16)"
echo "[u14] compile script $(shasum -a 256 "$ADAPTER_ROOT/build/inner/compile_oh_adapter_bridge_arm64.sh" | cut -c1-16)"
set +e
bash "$ADAPTER_ROOT/build/inner/compile_oh_adapter_bridge_arm64.sh"
rc=$?
set -e
echo "[u14] recipe rc=$rc"
[ -f "$OUT/liboh_adapter_bridge.so" ] && shasum -a 256 "$OUT/liboh_adapter_bridge.so" | sed 's/^/[u14] artifact /'
echo "[u14] end $(date -Iseconds)"
exit $rc
