#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
python3 "$REPO/scripts/lab/check_frozen.py" --source-root "$REPO"
ROOT=$REPO/bms/src/.work/b68-generation
FROZEN=$ROOT/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
OUT=$REPO/bms/src/.work/n1-native/soundpool
NATIVE=$HERE/native-loader
TARGET=aarch64-linux-ohos
export LD_LIBRARY_PATH=$TC/runtime
mkdir -p "$OUT"
COMMON=(--target=$TARGET --sysroot=$SYS -B$TC/bin -isystem $SYS/include/$TARGET -fPIC -O2 -g -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -I$HERE/flutter/include)
LINK=(--target=$TARGET --sysroot=$SYS -B$TC/bin -B$SYS/lib/$TARGET -fuse-ld=lld -shared -Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--build-id=sha1,--hash-style=both -L$SYS/lib/$TARGET)
"$TC/bin/clang-15" "${COMMON[@]}" -std=gnu11 -c "$HERE/src/oh_soundpool_jni.c" -o "$OUT/soundpool.o"
"$TC/bin/clang-15" "${LINK[@]}" -Wl,-soname,libsoundpool.so "$OUT/soundpool.o" -lc -ldl -lpthread -o "$OUT/libsoundpool.so"
objs=()
for source in native_loader.cpp native_loader_registry.cpp system_loader.cpp; do
  obj=$OUT/${source%.cpp}.o
  "$TC/bin/clang-15" "${COMMON[@]}" -fvisibility=hidden -DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1 -nostdinc++ -isystem "$TC/include/c++/v1" -std=gnu++17 -fno-exceptions -fno-rtti -include "$FROZEN/sources/bionic_compat/include/libcxx_compat.h" -I"$NATIVE/include" -I"$NATIVE/src" -c "$NATIVE/src/$source" -o "$obj"
  objs+=("$obj")
done
"$TC/bin/clang-15" "${LINK[@]}" -nostdlib++ -Wl,-soname,libnativeloader.so -Wl,--version-script="$NATIVE/native_loader.map" -L"$REPO/bms/src/.work/n1-native/flutter" -L"$ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/frozen/runtime_provider/libraries/oh" -o "$OUT/libnativeloader.so" "${objs[@]}" -Wl,--no-as-needed -lapp_native_loader -Wl,--as-needed -lc++ -lc -ldl -lpthread "$TC/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"
sha256sum "$OUT"/*.so
