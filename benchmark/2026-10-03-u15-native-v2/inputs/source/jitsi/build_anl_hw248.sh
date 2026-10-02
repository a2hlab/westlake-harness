#!/usr/bin/env bash
# Runs ON hw248. The two libapp_native_loader lines of westlake-harness-bms-deploy benchmark/2026-09-30-n3-native/
# build-flutter.sh verbatim (anl.o compile with COMMON + -std=c11 -Wall -Wextra -Werror -fvisibility=hidden; link with
# LINK + soname + app_native_loader.map), frozen clang feef13a3, inside the 58-char mirror root.
#   build_anl_hw248.sh <mirror-root> <src.c> <dest-dir>
# <src.c> = the n3-native original (faithful repro of eebd62f2) or this round's src/app_native_loader.c (+ jitsi).
set -euo pipefail
REPO=${1:?mirror root}; SRCC=${2:?source}; DEST=${3:?dest}
[ -n "$REPO" ] && [ -f "$SRCC" ] || exit 9
cd "$REPO"
HERE=$REPO/benchmark/2026-09-30-n3-native
ROOT=$REPO/bms/src/.work/b68-generation
FROZEN=$ROOT/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
OUT=$REPO/bms/src/.work/n3-native/flutter
SRC=$HERE/flutter
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
CC=$TC/bin/clang-15
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
mkdir -p "$OUT" "$DEST"
echo "[hw248] $(date -Iseconds) root=$REPO ($(printf %s "$REPO" | wc -c) chars) src=${SRCC#$REPO/} clang: $($CC --version | head -1)"
"$CC" "${COMMON[@]}" -std=c11 -Wall -Wextra -Werror -fvisibility=hidden -c "$SRCC" -o "$OUT/anl.o"
"$CC" "${LINK[@]}" -Wl,-soname,libapp_native_loader.so -Wl,--version-script=$SRC/app_native_loader.map "$OUT/anl.o" -lc -o "$OUT/libapp_native_loader.so"
sha256sum "$OUT/libapp_native_loader.so"
mv "$OUT/libapp_native_loader.so" "$DEST/"
rm -f "$OUT/anl.o"
