#!/bin/sh
set -eu

RUN_NAME=${RUN_NAME:?RUN_NAME is required}
FROZEN=/project/.work/product-tls-generation/frozen
TOOLCHAIN="$FROZEN/toolchain"
SYSROOT="$FROZEN/sysroot"
TARGET=aarch64-linux-ohos
TARGET_LIB="$SYSROOT/lib/$TARGET"
SOURCE=/project/adapter/framework/appspawn-x/bionic_compat/src
OUT="/work/$RUN_NAME"

mkdir -p "$OUT"

COMMON="--target=$TARGET --sysroot=$SYSROOT -B$TOOLCHAIN/bin -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE -isystem $SYSROOT/include/$TARGET"

# shellcheck disable=SC2086
"$TOOLCHAIN/bin/clang-15" $COMMON -std=c11 \
    -fno-builtin-__sync_val_compare_and_swap_1 \
    -c "$SOURCE/sync_builtins.c" -o "$OUT/sync_builtins.o"

# shellcheck disable=SC2086
"$TOOLCHAIN/bin/clang-15" $COMMON -nostdinc++ \
    -isystem "$TOOLCHAIN/include/c++/v1" -std=gnu++17 \
    -c "$SOURCE/abort_message_compat.cpp" -o "$OUT/abort_message_compat.o"

"$TOOLCHAIN/bin/clang-15" --target="$TARGET" --sysroot="$SYSROOT" \
    -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" -fuse-ld=lld -shared -nostdlib++ \
    -Wl,-z,defs -Wl,-z,now -Wl,--build-id=sha1 \
    -o "$OUT/libcompat_regression.so" \
    "$OUT/sync_builtins.o" "$OUT/abort_message_compat.o" \
    -L"$TARGET_LIB" -lc -ldl -lpthread \
    "$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"

"$TOOLCHAIN/bin/llvm-readelf" -hW -lW -dW -sW \
    "$OUT/libcompat_regression.so" >"$OUT/readelf.txt"
"$TOOLCHAIN/bin/llvm-objdump" -d "$OUT/libcompat_regression.so" \
    >"$OUT/objdump.txt"

grep -q 'Machine:.*AArch64' "$OUT/readelf.txt"
grep -q 'android_set_abort_message' "$OUT/readelf.txt"
grep -q 'android_get_abort_message' "$OUT/readelf.txt"
grep -q 'adler32_combine' "$OUT/readelf.txt"
if grep -Eq '\((RPATH|RUNPATH|TEXTREL)\)' "$OUT/readelf.txt"; then
    echo "FAIL unsafe dynamic tag" >&2
    exit 1
fi
if grep -q ' TLS ' "$OUT/readelf.txt"; then
    echo "FAIL compatibility regression DSO unexpectedly owns PT_TLS" >&2
    exit 1
fi

sha256sum "$OUT/libcompat_regression.so" | awk '{print $1}' \
    >"$OUT/artifact.sha256"

