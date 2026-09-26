#!/usr/bin/env bash
# Build the hollow libnpth.so stub (#48). Run on the a2hlab VM.
# Regenerates the C from the ABI list, then compiles. Output SONAME libnpth.so,
# exports only JNI_OnLoad, NEEDED only libc — drops in over the app arm64 copy.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BENCH="$(dirname "$HERE")"
SDK="${OHOS_SDK:-$HOME/a2hlab/ws/toolchains/ohos-sdk/native}"
JNI="${JNI_INCLUDE:-$HOME/a2hlab/ws/toolchains/jdk21/jdk-21.0.6+7/include}"
OUT="${1:-$HERE/libnpth.so}"
python3 "$BENCH/scripts/gen_npth_stub.py" "$BENCH/evidence/npth-app-abi-48.txt" "$HERE/libnpth_stub.c"
"$SDK/llvm/bin/clang" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" \
  -I"$JNI" -I"$JNI/linux" -O2 -fPIC -fvisibility=hidden -shared -Wl,-z,defs \
  -Wl,-soname,libnpth.so -Wl,--build-id=sha1 -x c "$HERE/libnpth_stub.c" -o "$OUT"
echo "built: $OUT"; sha256sum "$OUT"
