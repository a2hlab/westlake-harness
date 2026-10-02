#!/usr/bin/env bash
# Runs ON hw248. The compile/link commands of westlake-harness-bms-deploy benchmark/2026-09-30-n4-native/build-abi.sh
# (5d66488b, lines 6-24) verbatim, inside a mirror of that repo whose root path has the SAME LENGTH as the original
# (58 chars), with the frozen toolchain subset (clang-15 / lld feef13a3), sysroot, flutter/include and sources at their
# original relative paths. The original's first step, check_frozen.py, is a source gate, not part of the compile.
#   build_hw248.sh <mirror-root> <dest-dir> [extra .c file ...]
# extra .c files (the Gecko exports) are compiled with the same COMMON flags and linked after stdio.o; the version
# script is <mirror-root>/benchmark/2026-09-30-n4-native/src/native_abi.map unless NATIVE_ABI_MAP is set.
set -euo pipefail
REPO=${1:?mirror root}; DEST=${2:?dest}; shift 2
cd "$REPO"
HERE=$REPO/benchmark/2026-09-30-n4-native
ROOT=$REPO/bms/src/.work/b68-generation
FROZEN=$ROOT/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
POOL=$ROOT/platform-pool/system/lib64
OUT=${FLUTTER_BUILD_OUT:-$REPO/bms/src/.work/n4-native/abi}
SRC=$REPO/benchmark/2026-09-30-n3-native/flutter
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
CC=$TC/bin/clang-15
CXX=$TC/bin/clang++
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
MAP=${NATIVE_ABI_MAP:-$HERE/src/native_abi.map}
mkdir -p "$OUT" "$DEST"
echo "[hw248] $(date -Iseconds) root=$REPO ($(printf %s "$REPO" | wc -c) chars) clang: $($CC --version | head -1)"
"$CC" "${COMMON[@]}" -std=c11 -c "$HERE/src/native_abi.c" -o "$OUT/native_abi.o"
"$CC" "${COMMON[@]}" -std=c11 -fno-builtin -c "$HERE/src/bionic_stdio_compat.c" -o "$OUT/stdio.o"
EXTRA_O=()
for c in "$@"; do
    o="$OUT/$(basename "${c%.c}").o"
    "$CC" "${COMMON[@]}" -std=c11 -c "$c" -o "$o"
    EXTRA_O+=("$o")
done
"$CC" "${LINK[@]}" -Wl,-z,global,-soname,libwestlake_native_abi.so -Wl,--version-script=$MAP "$OUT/native_abi.o" "$OUT/stdio.o" ${EXTRA_O[@]+"${EXTRA_O[@]}"} -lc -lpthread -o "$OUT/libwestlake_native_abi.so"
sha256sum "$OUT/libwestlake_native_abi.so"
mv "$OUT/libwestlake_native_abi.so" "$DEST/"
rm -f "$OUT"/*.o
