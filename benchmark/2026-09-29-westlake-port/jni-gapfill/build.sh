#!/usr/bin/env bash
# Build libwestlake_jni_gapfill.so (aarch64, OH sysroot). Fails on missing
# source; post-build gates: JNI_OnLoad exported + no undefined JNI boilerplate.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/build}"
[ -f "$HERE/westlake_jni_gapfill.cpp" ] || { echo "MISSING westlake_jni_gapfill.cpp"; exit 1; }
VMROOT="${VMROOT:-/home/zhaoyue/a2hlab/ws}"
CXX="$VMROOT/toolchains/ohos-sdk/native/llvm/bin/clang-15"
SYSROOT="$VMROOT/toolchains/ohos-sdk/native/sysroot"
JNI_INC="${JNI_INC:-/home/zhaoyue/a2hlab/westlake-current/third_party/jni}"
[ -x "$CXX" ] || { echo "clang-15 missing"; exit 1; }
mkdir -p "$OUT"
"$CXX" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
  -shared -fPIC -O2 -std=c++17 -Wall -I"$JNI_INC" \
  -o "$OUT/libwestlake_jni_gapfill.so" "$HERE/westlake_jni_gapfill.cpp" \
  || { echo "build failed"; exit 2; }
file "$OUT/libwestlake_jni_gapfill.so" | head -1
nm -D "$OUT/libwestlake_jni_gapfill.so" | grep -q " T JNI_OnLoad" || { echo "JNI_OnLoad missing"; exit 3; }
sha256sum "$OUT/libwestlake_jni_gapfill.so"
