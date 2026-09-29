#!/usr/bin/env bash
set -euo pipefail
ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b68-generation
APP_LOADER=$ROOT/adapter/framework/app-native-loader
PTHREAD_BRIDGE=$ROOT/adapter/framework/native-compat/bionic-pthread-bridge
TOOLCHAIN=$ROOT/.work/product-tls-generation/frozen/toolchain
SYSROOT=$ROOT/.work/product-tls-generation/frozen/sysroot
TARGET=aarch64-linux-ohos
TARGET_LIB=$SYSROOT/lib/$TARGET
CC=$TOOLCHAIN/bin/clang-15
OUT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b92-stack/anl-build
export LD_LIBRARY_PATH=$TOOLCHAIN/runtime
COMMON=(--target=$TARGET --sysroot=$SYSROOT -B$TOOLCHAIN/bin -fPIC -O2 -g -fvisibility=hidden -ffunction-sections -fdata-sections -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE -ffile-prefix-map=$ROOT=. -fdebug-prefix-map=$ROOT=. -isystem $SYSROOT/include/$TARGET)
record() { "$@"; }
mkdir -p "$OUT/pass1/app-loader" "$OUT/pass2/app-loader"
build_app_loader()
{
    local pass=$1
    local dir=$OUT/$pass/app-loader
    record "$CC" "${COMMON[@]}" \
        -std=c11 -Wall -Wextra -Werror \
        -I"$APP_LOADER/include" \
        -I"$PTHREAD_BRIDGE/include" \
        -c "$APP_LOADER/src/app_native_loader.c" \
        -o "$dir/app_native_loader.o"
    record "$CC" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" \
        -fuse-ld=lld -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-undefined -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libapp_native_loader.so \
        -Wl,--version-script="$APP_LOADER/app_native_loader.map" \
        -L"$TARGET_LIB" \
        "$dir/app_native_loader.o" -lc \
        -o "$dir/libapp_native_loader.so"
}

build_app_loader pass1
build_app_loader pass2
cmp "$OUT/pass1/app-loader/libapp_native_loader.so" "$OUT/pass2/app-loader/libapp_native_loader.so"
sha256sum "$OUT/pass1/app-loader/libapp_native_loader.so"
