#!/bin/bash
# build_probes.sh — cross-compile Z01 native-window probe and netprobe for D600.
#
# Mirrors the toolchain recipe from the adapter arm64 build and from
# 16.13-Yue/_rs_display_diag/build_rs_display_probe.sh.
#
# Run this in the Linux cross-compile container that holds the OH source tree.
#
# Required env (or defaults):
#   OH_ROOT      - OpenHarmony source root (default /data/oh61-wukong100)
#   AOSP_ROOT    - AOSP source root (default /data/aosp-arm64-d600)
#   ADAPTER_ROOT - this adapter tree (auto-detected)
#   OH_PRODUCT   - OH product name (default wukong100)
#
# Usage:
#   bash build_probes.sh              # full build
#   bash build_probes.sh --dry-run    # print commands and preflight only

set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
OH="${OH_ROOT:-/data/oh61-wukong100}"
AOSP="${AOSP_ROOT:-/data/aosp-arm64-d600}"
PROD="${OH_PRODUCT:-wukong100}"

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/out"
TMP="$OUT/.build"
mkdir -p "$OUT" "$TMP"

# ---- Toolchain ----
SR="$OH/out/$PROD/obj/third_party/musl"
USR="$SR/usr"
ML="$USR/lib/aarch64-linux-ohos"
CC="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang"
CXX="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++"
BUILTINS="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"

# OH system lib dirs
PSDK="$OH/out/$PROD/packages/phone/system/lib64/platformsdk"
SDKSP="$OH/out/$PROD/packages/phone/system/lib64/chipset-sdk-sp"
SDK="$OH/out/$PROD/packages/phone/system/lib64/chipset-sdk"
SYSLIB="$OH/out/$PROD/packages/phone/system/lib64"
NDK="$OH/out/$PROD/packages/phone/system/lib64/ndk"

log_info()  { echo -e "\033[0;34m[INFO]\033[0m  $*"; }
log_ok()    { echo -e "\033[0;32m[OK]\033[0m    $*"; }
log_warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }

# ---------------------------------------------------------------------------
# Preflight: verify the OH build environment exists.
# ---------------------------------------------------------------------------
preflight() {
    local fail=0
    log_info "Preflight for OH=$OH PROD=$PROD"

    for f in "$CC" "$CXX"; do
        if [ -x "$f" ]; then log_ok "toolchain $f"; else log_error "missing $f"; fail=1; fi
    done

    if [ -d "$SR" ]; then log_ok "musl sysroot $SR"; else log_error "missing sysroot $SR"; fail=1; fi
    if [ -d "$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_client/core" ]; then
        log_ok "RS client headers"
    else
        log_error "missing RS client headers"; fail=1
    fi
    if [ -f "$OH/interface/sdk_c/graphic/graphic_2d/native_window/external_window.h" ]; then
        log_ok "native_window NDK headers"
    else
        log_error "missing native_window headers"; fail=1
    fi

    # Probe libraries that must exist for z01 link.
    local lib
    for lib in "$SYSLIB/librender_service_client.z.so" "$SYSLIB/libsurface.z.so" "$NDK/libnative_window.so"; do
        if [ -f "$lib" ]; then log_ok "lib $(basename "$lib")"; else log_warn "missing $lib"; fi
    done

    if [ "$fail" -ne 0 ]; then
        echo ""
        log_error "Preflight FAILED. This script must run in the OH cross-compile container."
        exit 1
    fi
    log_ok "Preflight passed"
}

# Runner that honors DRY_RUN.
run() {
    if [ "$DRY_RUN" = "1" ]; then
        printf '[DRY]'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

preflight
if [ "$DRY_RUN" = "1" ]; then
    log_info "Dry-run mode: printing build plan and exiting"
fi

COMMON="--target=aarch64-linux-ohos --sysroot=$SR"
COMMON="$COMMON -I$USR/include/aarch64-linux-ohos"
COMMON="$COMMON -fPIC -O2 -D__OHOS__ -D__MUSL__ -D_GNU_SOURCE"
COMMON="$COMMON -Wno-everything"

INCS="\
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_client/core \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_base/core \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_base/include \
  -I$OH/foundation/graphic/graphic_2d/interfaces/inner_api/common \
  -I$OH/foundation/graphic/graphic_2d/interfaces/inner_api \
  -I$OH/foundation/graphic/graphic_2d/utils/color_manager/export \
  -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/include \
  -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface \
  -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/utils \
  -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/buffer_handle \
  -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api \
  -I$OH/foundation/graphic/graphic_surface/interfaces \
  -I$OH/commonlibrary/c_utils/base/include \
  -I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_core/include \
  -I$OH/foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include \
  -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include \
  -I$OH/interface/sdk_c/graphic/graphic_2d/native_window \
  -I$OH/interface/sdk_c/graphic/graphic_2d/native_buffer \
  -I$AOSP/system/logging/liblog/include"

# Try to harvest RS-client include dirs from ninja for completeness.
NINJA="$OH/out/$PROD/obj/foundation/graphic/graphic_2d/rosen/modules/render_service_client/render_service_client_src.ninja"
if [ -f "$NINJA" ]; then
  harvested_inc=$(grep -m1 '^include_dirs' "$NINJA" | tr ' ' '\n' | grep -E '^-I' \
      | sed "s|^-I\.\./\.\./|-I$OH/|" | sed "s|^-I\.\./|-I$OH/out/$PROD/|" | tr '\n' ' ')
  harvested_def=$(grep -m1 '^defines' "$NINJA" | tr ' ' '\n' | grep -E '^-D' \
      | grep -v 'FFRT_' | grep -v '\\' | tr '\n' ' ')
  INCS="$INCS $harvested_inc"
  COMMON="$COMMON $harvested_def"
  log_info "Harvested RS-client ninja include dirs"
else
  log_warn "RS-client ninja not found at $NINJA"
fi

# ---------------------------------------------------------------------------
# 1. netprobe (C)
# ---------------------------------------------------------------------------
log_info "Build netprobe.c"
read -r -a common_args <<< "$COMMON"
read -r -a inc_args <<< "$INCS"

run "$CC" "${common_args[@]}" -B"$ML" -L"$ML" -O2 -o "$OUT/netprobe" "$HERE/netprobe.c"
log_ok "netprobe -> $OUT/netprobe"

# ---------------------------------------------------------------------------
# 2. z01_native_window_probe (C++)
# ---------------------------------------------------------------------------
log_info "Build z01_native_window_probe.cpp"
Z01_CXXFLAGS="-std=c++17 -fno-rtti -include sys/types.h"
Z01_LINK="$CXX --target=aarch64-linux-ohos -B$ML -L$ML -fPIC"
Z01_LIBS="\
  -L$PSDK -L$SDKSP -L$SDK -L$SYSLIB -L$NDK \
  -Wl,--enable-new-dtags -Wl,--allow-shlib-undefined \
  -Wl,-rpath,/system/lib64 -Wl,-rpath,/system/lib64/platformsdk -Wl,-rpath,/system/lib64/chipset-sdk \
  -lrender_service_client.z -lrender_service_base.z \
  -lsurface.z -lsync_fence.z -lnative_window \
  -lutils.z -lipc_core.z -lsamgr_proxy.z -lhilog -lbegetutil.z \
  -ldl -lpthread"

read -r -a z01_cxx_args <<< "$Z01_CXXFLAGS"
read -r -a z01_link_args <<< "$Z01_LINK"
read -r -a z01_lib_args <<< "$Z01_LIBS"

run "$CXX" "${common_args[@]}" "${inc_args[@]}" "${z01_cxx_args[@]}" -c "$HERE/z01_native_window_probe.cpp" -o "$TMP/z01.o"
run "${z01_link_args[@]}" -o "$OUT/z01_native_window_probe" "$TMP/z01.o" "${z01_lib_args[@]}" "$BUILTINS"
log_ok "z01_native_window_probe -> $OUT/z01_native_window_probe"

if [ "$DRY_RUN" = "1" ]; then
    echo ""
    log_info "Dry-run complete; no files were modified."
    exit 0
fi

echo ""
echo "=== file / NEEDED ==="
file "$OUT/z01_native_window_probe" 2>/dev/null || true
file "$OUT/netprobe" 2>/dev/null || true
readelf -d "$OUT/z01_native_window_probe" 2>/dev/null | grep -E 'NEEDED|RPATH|RUNPATH' || true
echo ""
echo "Build complete. Output: $OUT/"
