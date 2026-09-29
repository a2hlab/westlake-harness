#!/usr/bin/env bash
# Build libwestlake_html_compat.so (aarch64, OH sysroot). Fails on missing
# source (contract). Post-build gate: JNI_OnLoad exported, dlopen-only face.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/build}"
[ -f "$HERE/westlake_html_compat.cpp" ] || { echo "MISSING westlake_html_compat.cpp"; exit 1; }
VMROOT="${VMROOT:-/home/zhaoyue/a2hlab/ws}"
CXX="$VMROOT/toolchains/ohos-sdk/native/llvm/bin/clang-15"
SYSROOT="$VMROOT/toolchains/ohos-sdk/native/sysroot"
JNI_INC="${JNI_INC:-/home/zhaoyue/a2hlab/westlake-current/third_party/jni}"
[ -x "$CXX" ] || { echo "clang-15 missing"; exit 1; }
mkdir -p "$OUT"
"$CXX" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
  -shared -fPIC -O2 -std=c++17 -Wall -I"$JNI_INC" \
  -o "$OUT/libwestlake_html_compat.so" "$HERE/westlake_html_compat.cpp" -ldl \
  || { echo "build failed"; exit 2; }
file "$OUT/libwestlake_html_compat.so" | head -1
nm -D "$OUT/libwestlake_html_compat.so" | grep -q " T JNI_OnLoad" || { echo "JNI_OnLoad missing"; exit 3; }
sha256sum "$OUT/libwestlake_html_compat.so"
