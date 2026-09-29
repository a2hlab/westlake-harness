#!/usr/bin/env bash
# Build liboh_egl_boundary.so (EGL optional-damage fallback, verbatim Westlake
# oh_egl_boundary.cpp) for v3c — the only hwui-family piece that compiles
# standalone (pure EGL/dlfcn deps; the 13-file hwui-shim family needs the OH
# drawing/EGL build env, left to cx-t0 per the copylist).
# Fails if the source is missing (contract).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/build}"
[ -f "$HERE/oh_egl_boundary.cpp" ] || { echo "MISSING oh_egl_boundary.cpp"; exit 1; }
VMROOT="${VMROOT:-/home/zhaoyue/a2hlab/ws}"
CXX="$VMROOT/toolchains/ohos-sdk/native/llvm/bin/clang-15"
SYSROOT="$VMROOT/toolchains/ohos-sdk/native/sysroot"
[ -x "$CXX" ] || { echo "clang-15 not found"; exit 1; }
mkdir -p "$OUT"
"$CXX" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
  -shared -fPIC -O2 -std=c++17 -Wall \
  -o "$OUT/liboh_egl_boundary.so" "$HERE/oh_egl_boundary.cpp" -ldl \
  || { echo "build failed"; exit 2; }
file "$OUT/liboh_egl_boundary.so" | head -1
N=$(nm -D "$OUT/liboh_egl_boundary.so" | grep -cE "eglQueryString|eglInitialize" || true)
[ "$N" -ge 1 ] || { echo "EGL symbols missing"; exit 3; }
sha256sum "$OUT/liboh_egl_boundary.so"
