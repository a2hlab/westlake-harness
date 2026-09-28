#!/bin/sh
# Build liboh_inet_permit.so for OH arm64 (musl) using the DevEco OHOS NDK.
# Tiny LD_PRELOAD shim: only libc + libdl deps. No AOSP/OH adapter deps.
set -e
NDK="${NDK:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}"
CLANG="$NDK/llvm/bin/clang"
SYSROOT="$NDK/sysroot"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT:-$HERE/out}"
mkdir -p "$OUT"

"$CLANG" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
    -fPIC -shared -O2 -Wall -fvisibility=default \
    -o "$OUT/liboh_inet_permit.so" \
    "$HERE/jni/oh_inet_permit.c" \
    -ldl

echo "built: $OUT/liboh_inet_permit.so"
"$NDK/llvm/bin/llvm-nm" -D "$OUT/liboh_inet_permit.so" | grep -iE " socket| getaddrinfo" || true
