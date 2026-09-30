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


BC=$HERE/bionic
objects=()
for name in system_properties.cpp malloc_compat.cpp fdsan_stubs.cpp misc_compat.cpp abort_message_compat.cpp liblog_android_supplement.cpp sync_builtins.c strerror_r_compat.cpp dlopen_ext_compat.cpp; do
 obj=$OUT/${name%.*}.o
 objects+=("$obj")
 if [[ $name == *.c ]]; then
  "$CC" "${COMMON[@]}" -std=c11 -fvisibility=default -D__ANDROID_API__=34 -DPAGE_SIZE=4096 -I"$BC/include" -c "$BC/src/$name" -o "$obj"
 else
  "$CXX" "${COMMON[@]}" -std=gnu++17 -nostdinc++ -isystem "$TC/include/c++/v1" -fvisibility=default -DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1 -include "$BC/include/libcxx_compat.h" -I"$BC/include" -DPARAM_VALUE_LEN_MAX=96 -Wno-constant-conversion -c "$BC/src/$name" -o "$obj"
 fi
done
"$CC" "${LINK[@]}" -Wl,-soname,libbionic_compat.so -Wl,--version-script=$HERE/src/bionic.map "${objects[@]}" -Wl,--no-as-needed "$POOL/platformsdk/libbegetutil.z.so" "$POOL/chipset-sdk-sp/libc++.so" -Wl,--as-needed -lc -ldl -lpthread -o "$OUT/libbionic_compat.so"
sha256sum "$OUT/libbionic_compat.so"
