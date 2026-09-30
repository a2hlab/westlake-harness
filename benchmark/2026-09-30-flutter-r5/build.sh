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
OUT=${FLUTTER_BUILD_OUT:-$REPO/bms/src/.work/flutter-candidate}
SRC=$HERE/src
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
CC=$TC/bin/clang-15
CXX=$TC/bin/clang++
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
RUNTIME=$REPO/../westlake-generation-v3c-candidate/payload/android/lib64/liboh_android_runtime.so
test -f "$RUNTIME" || { echo "Missing mounted runtime input: $RUNTIME" >&2; exit 2; }
mkdir -p "$OUT"
"$CC" "${COMMON[@]}" -std=c11 -Wall -Wextra -Werror -fvisibility=hidden -c "$SRC/app_native_loader.c" -o "$OUT/anl.o"
"$CC" "${LINK[@]}" -Wl,-soname,libapp_native_loader.so -Wl,--version-script=$SRC/app_native_loader.map "$OUT/anl.o" -lc -o "$OUT/libapp_native_loader.so"
if [[ "${1:-}" == "--anl-only" ]]; then
    sha256sum "$OUT/libapp_native_loader.so"
    exit 0
fi
"$CC" "${COMMON[@]}" -std=c11 -c "$SRC/libandroid_webview_shim.c" -o "$OUT/android.o"
"$CC" "${COMMON[@]}" -std=c11 -c "$SRC/bionic_extra.c" -o "$OUT/bionic.o"
# R155-compatible current runtime; keep it a dependency, not a copied instance.
"$CC" "${LINK[@]}" -Wl,-soname,libandroid.so -Wl,--version-script=$SRC/android.map "$OUT/android.o" "$OUT/bionic.o" -Wl,--no-as-needed "$RUNTIME" "$POOL/chipset-sdk-sp/libnative_window.so" "$POOL/platformsdk/libnative_buffer.so" -Wl,--as-needed -lc -o "$OUT/libwestlake_flutter_android.so"
"$CC" "${COMMON[@]}" -c "$SRC/gles2.c" -o "$OUT/gles2.o"
"$CC" "${LINK[@]}" -Wl,-soname,libGLESv2.so "$OUT/gles2.o" -Wl,--no-as-needed "$POOL/platformsdk/libGLESv3.so" -lc -o "$OUT/libwestlake_flutter_gles2.so"
"$CXX" "${COMMON[@]}" -std=c++17 -nostdinc++ -fno-exceptions -fno-rtti -c "$SRC/libjnigraphics_webview_shim.cpp" -o "$OUT/jnigraphics.o"
"$CC" "${LINK[@]}" -Wl,-soname,libjnigraphics.so -Wl,--version-script=$SRC/jnigraphics.map "$OUT/jnigraphics.o" -lc -o "$OUT/libwestlake_flutter_jnigraphics.so"
sha256sum "$OUT"/*.so "$CC" "$SYS/lib/$TARGET/libc.so" > "$HERE/build-identities.txt"
