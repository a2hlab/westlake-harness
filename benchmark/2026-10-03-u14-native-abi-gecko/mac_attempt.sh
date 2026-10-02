#!/bin/bash
# Mac attempt at d2053066 (NOT the original toolchain): the same build-abi.sh flags, cwd, sources, sysroot and clang
# resource dir (frozen toolchain lib/clang/15.0.4), but the compiler/linker are the Mac DevEco OH SDK clang/lld 15.0.4
# (llvm-project 99548401) because the frozen clang-15 (feef13a3) is a Linux x86-64 binary.
#   mac_attempt.sh <out-dir>        (log teed to <out-dir>/build.log)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
WS=$(cd "$here/../../.." && pwd)
[ -n "${WORKSPACES:-}" ] && WS=$WORKSPACES
BD=$WS/westlake-harness-bms-deploy
OUT=${1:?out dir}
mkdir -p "$OUT"
LLVM=${DEVECO_LLVM:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm}
cd "$BD"
FROZEN=bms/src/.work/b68-generation/.work/product-tls-generation/frozen
TC=$BD/$FROZEN/toolchain
SYS=$BD/$FROZEN/sysroot
SRC=$BD/benchmark/2026-09-30-n3-native/flutter
HERE=$BD/benchmark/2026-09-30-n4-native
TARGET=aarch64-linux-ohos
CC=$LLVM/bin/clang
RES=(-resource-dir "$TC/lib/clang/15.0.4")
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$SYS/lib/$TARGET -fuse-ld=$LLVM/bin/ld.lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
{
    echo "[mac-attempt] $(date -Iseconds) clang: $($CC --version | head -1)"
    "$CC" "${RES[@]}" "${COMMON[@]}" -std=c11 -c "$HERE/src/native_abi.c" -o "$OUT/native_abi.o"
    "$CC" "${RES[@]}" "${COMMON[@]}" -std=c11 -fno-builtin -c "$HERE/src/bionic_stdio_compat.c" -o "$OUT/stdio.o"
    "$CC" "${RES[@]}" "${LINK[@]}" -Wl,-z,global,-soname,libwestlake_native_abi.so -Wl,--version-script=$HERE/src/native_abi.map "$OUT/native_abi.o" "$OUT/stdio.o" -lc -lpthread -o "$OUT/libwestlake_native_abi.so"
    shasum -a 256 "$OUT/libwestlake_native_abi.so"
} 2>&1 | tee "$OUT/build.log"
