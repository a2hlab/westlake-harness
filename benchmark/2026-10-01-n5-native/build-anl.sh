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
OUT=${FLUTTER_BUILD_OUT:-$REPO/bms/src/.work/n5-native/flutter}
SRC=$HERE/flutter
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
CC=$TC/bin/clang-15
CXX=$TC/bin/clang++
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
RUNTIME=$REPO/../westlake-generation-n4-order-216b68fb/payload/android/lib64/liboh_android_runtime.so
test -f "$RUNTIME" || { echo "Missing mounted runtime input: $RUNTIME" >&2; exit 2; }
mkdir -p "$OUT"
"$CC" "${COMMON[@]}" -std=c11 -Wall -Wextra -Werror -fvisibility=hidden -c "$SRC/app_native_loader.c" -o "$OUT/anl.o"
"$CC" "${LINK[@]}" -Wl,-soname,libapp_native_loader.so -Wl,--version-script=$SRC/app_native_loader.map "$OUT/anl.o" -lc -o "$OUT/libapp_native_loader.so"
sha256sum "$OUT/libapp_native_loader.so" "$CC" "$SYS/lib/$TARGET/libc.so" > "$OUT/build-identities.txt"
