#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
python3 "$REPO/scripts/lab/check_frozen.py" --source-root "$REPO"
ROOT=$REPO/bms/src/.work/b68-generation
FROZEN=$ROOT/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
POOL=$ROOT/platform-pool/system/lib64
OUT=${FLUTTER_BUILD_OUT:-$REPO/bms/src/.work/n6-native/abi}
SRC=$REPO/benchmark/2026-09-30-n3-native/flutter
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
CC=$TC/bin/clang-15
CXX=$TC/bin/clang++
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
mkdir -p "$OUT"
"$CXX" "${COMMON[@]}" -std=c++17 -nostdinc++ -isystem "$TC/include/c++/v1" -fno-exceptions -fno-rtti -c "$HERE/src/flutter_egl.cpp" -o "$OUT/flutter_egl.o"
"$CC" "${COMMON[@]}" -std=c11 -c "$HERE/src/native_abi.c" -o "$OUT/native_abi.o"
"$CC" "${COMMON[@]}" -std=c11 -fno-builtin -c "$HERE/src/bionic_stdio_compat.c" -o "$OUT/stdio.o"
"$CC" "${LINK[@]}" -Wl,-z,global,-soname,libwestlake_native_abi.so -Wl,--version-script=$HERE/src/native_abi.map "$OUT/native_abi.o" "$OUT/stdio.o" "$OUT/flutter_egl.o" -Wl,--no-as-needed "$POOL/chipset-sdk-sp/libc++.so" -Wl,--as-needed -lc -lpthread -o "$OUT/libwestlake_native_abi.so"
sha256sum "$OUT/libwestlake_native_abi.so"
