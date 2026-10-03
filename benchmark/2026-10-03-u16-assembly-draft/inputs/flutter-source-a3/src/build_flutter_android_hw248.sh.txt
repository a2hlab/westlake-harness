#!/usr/bin/env bash
# Runs ON hw248. The libandroid lines of westlake-harness-bms-deploy benchmark/2026-09-30-n1-native/build-flutter.sh
# (commit 0b8588216c; the build that produced westlake_flutter/libandroid.so ee2fb82c, receipt build-identities.txt:2)
# verbatim, inside a same-length (58-char) mirror of that repo with the frozen clang-15 feef13a3, sysroot,
# platform-pool inputs and the v3c runtime at its original relative path ($REPO/../westlake-generation-v3c-candidate).
# The recipe's other outputs (ANL, native_abi, GLESv2, jnigraphics) and its check_frozen gate are not part of this file.
#   build_flutter_android_hw248.sh <mirror-root> <dest-dir> [extra .cpp ...]
# Extra .cpp objects are compiled with N6's C++ line (2026-10-01-n6-native/build.sh) and linked after bionic.o with
# N6's `--no-as-needed $POOL/chipset-sdk-sp/libc++.so`; ANDROID_MAP overrides the version script. With extras, the
# toolchain's own libclang_rt.builtins.a is put on the link line BEFORE libc++.so so that the original objects' TLS
# keeps the statically linked compiler-rt emutls the original build had (libc++.so also exports __emutls_get_address
# and would otherwise win, moving the old code's TLS to a shared emutls instance).
set -euo pipefail
REPO=${1:?mirror root}; DEST=${2:?dest}; shift 2
cd "$REPO"
HERE=$REPO/benchmark/2026-09-30-n1-native
ROOT=$REPO/bms/src/.work/b68-generation
FROZEN=$ROOT/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
POOL=$ROOT/platform-pool/system/lib64
OUT=${FLUTTER_BUILD_OUT:-$REPO/bms/src/.work/n1-native/flutter}
SRC=$HERE/flutter
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
CC=$TC/bin/clang-15
CXX=$TC/bin/clang++
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$SRC/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET -L$OUT)
RUNTIME=$REPO/../westlake-generation-v3c-candidate/payload/android/lib64/liboh_android_runtime.so
test -f "$RUNTIME" || { echo "Missing mounted runtime input: $RUNTIME" >&2; exit 2; }
MAP=${ANDROID_MAP:-$SRC/android.map}
mkdir -p "$OUT" "$DEST"
echo "[hw248] $(date -Iseconds) root=$REPO ($(printf %s "$REPO" | wc -c) chars) clang: $($CC --version | head -1) runtime-input: $(sha256sum "$RUNTIME" | cut -c1-16)"
"$CC" "${COMMON[@]}" -std=c11 -c "$SRC/libandroid_webview_shim.c" -o "$OUT/android.o"
"$CC" "${COMMON[@]}" -std=c11 -c "$SRC/bionic_extra.c" -o "$OUT/bionic.o"
EXTRA_O=(); EXTRA_L=()
for c in "$@"; do
    o="$OUT/$(basename "${c%.*}").o"
    "$CXX" "${COMMON[@]}" -std=c++17 -nostdinc++ -isystem "$TC/include/c++/v1" -fno-exceptions -fno-rtti -c "$c" -o "$o"
    EXTRA_O+=("$o")
done
[ ${#EXTRA_O[@]} -gt 0 ] && EXTRA_L=("$TC/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a" "$POOL/chipset-sdk-sp/libc++.so")
# R155-compatible current runtime; keep it a dependency, not a copied instance.
"$CC" "${LINK[@]}" -Wl,-soname,libandroid.so -Wl,--version-script=$MAP "$OUT/android.o" "$OUT/bionic.o" ${EXTRA_O[@]+"${EXTRA_O[@]}"} -Wl,--no-as-needed "$RUNTIME" "$POOL/chipset-sdk-sp/libnative_window.so" "$POOL/platformsdk/libnative_buffer.so" ${EXTRA_L[@]+"${EXTRA_L[@]}"} -Wl,--as-needed -lc -o "$OUT/libwestlake_flutter_android.so"
sha256sum "$OUT/libwestlake_flutter_android.so"
mv "$OUT/libwestlake_flutter_android.so" "$DEST/"
rm -f "$OUT"/*.o
