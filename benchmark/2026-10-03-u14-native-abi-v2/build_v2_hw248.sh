#!/usr/bin/env bash
# Runs ON hw248. native_abi v2 = the 7605812c recipe (benchmark/2026-10-03-u14-native-abi-gecko/build_hw248.sh 29303e3c,
# itself build-abi.sh's compile/link lines verbatim) plus ONE extra object: the U13 compat-ctype source
# (benchmark/2026-10-03-u13-compat-ctype/ctype_compat.c, which #includes AOSP 14 r1 bionic e4df46f2 ctype_.c unmodified),
# compiled with the same COMMON flags plus the two include dirs compat used (empty shim ctype.h, openbsd libc/include).
# Only the ctype object gets those -I flags, so no other object's header resolution changes.
#   build_v2_hw248.sh <mirror-root> <dest-dir> <ctype-src-dir> [extra .c file ...]
# NATIVE_ABI_MAP selects the version script (v2: native_abi_v2.map = the Gecko map + `_ctype_` in LIBC).
set -euo pipefail
REPO=${1:?mirror root}; DEST=${2:?dest}; CTYPE_DIR=${3:?ctype src dir}; shift 3
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
"$CC" "${COMMON[@]}" -std=c11 -I"$CTYPE_DIR/inputs/shim" -I"$CTYPE_DIR/inputs/aosp/libc/upstream-openbsd/lib/libc/include" -c "$CTYPE_DIR/ctype_compat.c" -o "$OUT/ctype_compat.o"
EXTRA_O+=("$OUT/ctype_compat.o")
"$CC" "${LINK[@]}" -Wl,-z,global,-soname,libwestlake_native_abi.so -Wl,--version-script=$MAP "$OUT/native_abi.o" "$OUT/stdio.o" ${EXTRA_O[@]+"${EXTRA_O[@]}"} -lc -lpthread -o "$OUT/libwestlake_native_abi.so"
sha256sum "$OUT/libwestlake_native_abi.so"
mv "$OUT/libwestlake_native_abi.so" "$DEST/"
rm -f "$OUT"/*.o
