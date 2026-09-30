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
OUT=${FLUTTER_BUILD_OUT:-$REPO/bms/src/.work/n7-native}
SRC=$HERE/flutter
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
CC=$TC/bin/clang-15
CXX=$TC/bin/clang++
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
mkdir -p "$OUT"

"$CC" "${COMMON[@]}" -std=c11 -Wall -Wextra -Werror -c "$HERE/src/flutter_egl.c" -o "$OUT/egl.o"
"$CC" "${LINK[@]}" -Wl,-Bsymbolic-functions,-soname,libEGL.so -Wl,--version-script=$HERE/src/egl.map "$OUT/egl.o" -lc -o "$OUT/libEGL.so"
"$CC" "${COMMON[@]}" -std=c11 -Wall -Wextra -Werror -fvisibility=hidden -c "$SRC/app_native_loader.c" -o "$OUT/anl.o"
"$CC" "${LINK[@]}" -Wl,-soname,libapp_native_loader.so -Wl,--version-script=$SRC/app_native_loader.map "$OUT/anl.o" -lc -o "$OUT/libapp_native_loader.so"
sha256sum "$OUT/libEGL.so" "$OUT/libapp_native_loader.so"
