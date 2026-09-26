#!/usr/bin/env bash
# Build the hollow libmetasec_ml.so stub (#48). Run on the a2hlab VM.
# Output: libmetasec_ml.so exporting only JNI_OnLoad + Java_ms_bd_c_m_a, SONAME
# libmetasec_ml.so, so it drops in over the app's arm64-v8a copy.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SDK="${OHOS_SDK:-$HOME/a2hlab/ws/toolchains/ohos-sdk/native}"
CLANG="$SDK/llvm/bin/clang"
JNIINC="${JNI_INCLUDE:-$HOME/a2hlab/ws/toolchains/jdk21/jdk-21.0.6+7/include}"
OUT="${1:-$HERE/libmetasec_ml.so}"

"$CLANG" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" \
  -I"$JNIINC" -I"$JNIINC/linux" \
  -O2 -fPIC -fvisibility=hidden -shared \
  -Wl,-z,defs -Wl,-soname,libmetasec_ml.so -Wl,--build-id=sha1 \
  "$HERE/libmetasec_ml_stub.c" -o "$OUT"
echo "built: $OUT"
"$SDK/llvm/bin/llvm-readelf" -d -W "$OUT" | grep -E "SONAME"
echo "exports:"
"$SDK/llvm/bin/llvm-readelf" --dyn-syms -W "$OUT" | awk '$4~/FUNC|OBJECT/ && $5=="GLOBAL" && $7!="UND"{print "  "$4,$8}'
