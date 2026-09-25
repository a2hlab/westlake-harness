#!/usr/bin/env bash
# #46: rebuild libwebview_bionic_shim.so alone (#36 incremental rule) with the exact
# out-sp20 compile/link commands. $1 = westlake source tree, $2 = output dir.
set -euo pipefail
SRC=$1
OUT=$2
V=/home/dspfac/a2hlab/source-closure/verify
TC=$V/toolchains/ohos-sdk/native
RT=$TC/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos
CC="$TC/llvm/bin/clang --target=aarch64-linux-ohos --sysroot=$TC/sysroot"
SHIM=$SRC/framework/webview-shim
mkdir -p "$OUT/obj"
$CC -fPIC -O2 -Wall -Wextra -Werror -c "$SHIM/webview_bionic_shim.c" -o "$OUT/obj/webview_bionic_shim.c.o"
$CC -fPIC -c "$SHIM/webview_setjmp_arm64.S" -o "$OUT/obj/webview_setjmp_arm64.S.o"
$CC -fuse-ld=lld -nostdlib -shared -Wl,-z,defs -Wl,--build-id=sha1 \
    -Wl,-soname,libwebview_bionic_shim.so \
    -Wl,--version-script="$SHIM/webview_bionic_shim.map" \
    "$RT/clang_rt.crtbegin.o" "$OUT/obj/webview_bionic_shim.c.o" "$OUT/obj/webview_setjmp_arm64.S.o" \
    -Wl,--as-needed -ldl -lc "$RT/libclang_rt.builtins.a" "$RT/clang_rt.crtend.o" \
    -o "$OUT/libwebview_bionic_shim.so"
sha256sum "$OUT/libwebview_bionic_shim.so"
