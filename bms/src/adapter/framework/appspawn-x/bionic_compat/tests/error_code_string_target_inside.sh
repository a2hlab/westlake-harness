#!/bin/sh
set -eu

RUN_NAME=${RUN_NAME:?RUN_NAME is required}
FROZEN=/project/.work/product-tls-generation/frozen
TOOLCHAIN="$FROZEN/toolchain"
SYSROOT="$FROZEN/sysroot"
TARGET=aarch64-linux-ohos
TARGET_LIB="$SYSROOT/lib/$TARGET"
SOURCE=/project/adapter/framework/appspawn-x/bionic_compat/src
TEST=/project/adapter/framework/appspawn-x/bionic_compat/tests
REFERENCE=/project/adapter/frozen/references/aosp-libziparchive-error
OUT="/work/$RUN_NAME"
BUILTINS="$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"
export HOME="$OUT/home"
export TMPDIR="$OUT/tmp"

mkdir -p "$OUT" "$HOME" "$TMPDIR"

COMMON="--target=$TARGET --sysroot=$SYSROOT -B$TOOLCHAIN/bin -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE -isystem $SYSROOT/include/$TARGET"
CXX="-nostdinc++ -isystem $TOOLCHAIN/include/c++/v1 -std=gnu++17"

# Compile the byte-locked AOSP implementation as the one typed provider.
# shellcheck disable=SC2086
"$TOOLCHAIN/bin/clang-15" $COMMON $CXX \
    -I"$TEST/include" -I"$REFERENCE" \
    -c "$REFERENCE/zip_error.cpp" -o "$OUT/zip_error.o"

"$TOOLCHAIN/bin/clang-15" --target="$TARGET" --sysroot="$SYSROOT" \
    -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" -fuse-ld=lld -shared -nostdlib++ \
    -Wl,-z,defs -Wl,-z,now -Wl,--build-id=sha1 \
    -Wl,-soname,libziparchive.so \
    -o "$OUT/libziparchive_error_fixture.so" "$OUT/zip_error.o" \
    -L"$TARGET_LIB" -lc -ldl -lpthread "$BUILTINS"

# Compile the actual live misc compat source.  Its target DSO must not export
# either spelling of the ZIP ABI after the ownership correction.
# shellcheck disable=SC2086
"$TOOLCHAIN/bin/clang-15" $COMMON $CXX \
    -include /project/adapter/framework/appspawn-x/bionic_compat/include/libcxx_compat.h \
    -I/project/adapter/framework/appspawn-x/bionic_compat/include \
    -c "$SOURCE/misc_compat.cpp" -o "$OUT/misc_compat.o"

"$TOOLCHAIN/bin/clang-15" --target="$TARGET" --sysroot="$SYSROOT" \
    -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" -fuse-ld=lld -shared -nostdlib++ \
    -Wl,-z,defs -Wl,-z,now -Wl,--build-id=sha1 \
    -Wl,-soname,libbionic_compat_error_fixture.so \
    -o "$OUT/libbionic_compat_error_fixture.so" "$OUT/misc_compat.o" \
    -L"$TARGET_LIB" -lc -ldl -lpthread "$BUILTINS"

# A consumer with an explicit libziparchive.so edge proves the correct link
# shape independently from process-global or transitive lookup.
# shellcheck disable=SC2086
"$TOOLCHAIN/bin/clang-15" $COMMON $CXX \
    -c "$TEST/error_code_string_consumer.cpp" -o "$OUT/consumer.o"

"$TOOLCHAIN/bin/clang-15" --target="$TARGET" --sysroot="$SYSROOT" \
    -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" -fuse-ld=lld -shared -nostdlib++ \
    -Wl,-z,defs -Wl,-z,now -Wl,--build-id=sha1 \
    -Wl,-soname,liberror_code_consumer.so \
    -o "$OUT/liberror_code_consumer.so" "$OUT/consumer.o" \
    -L"$OUT" -Wl,--no-as-needed -l:libziparchive_error_fixture.so -Wl,--as-needed \
    -L"$TARGET_LIB" -lc -ldl -lpthread "$BUILTINS"

READELF="$TOOLCHAIN/bin/llvm-readelf"
"$READELF" --dyn-syms --wide "$OUT/libziparchive_error_fixture.so" >"$OUT/provider.dynsym"
"$READELF" --dyn-syms --wide "$OUT/libbionic_compat_error_fixture.so" >"$OUT/compat.dynsym"
"$READELF" -d --wide "$OUT/liberror_code_consumer.so" >"$OUT/consumer.dynamic"

defined_count()
{
    awk -v wanted="$2" '
        $1 ~ /^[0-9]+:$/ && NF >= 8 {
            name=$8; sub(/@.*/, "", name)
            if (name == wanted && $5 == "GLOBAL" && $7 != "UND") count++
        }
        END { print count + 0 }
    ' "$1"
}

[ "$(defined_count "$OUT/provider.dynsym" _Z15ErrorCodeStringi)" -eq 1 ]
[ "$(defined_count "$OUT/compat.dynsym" _Z15ErrorCodeStringi)" -eq 0 ]
[ "$(defined_count "$OUT/compat.dynsym" ErrorCodeString)" -eq 0 ]
[ "$(grep -c 'Shared library: \[libziparchive.so\]' "$OUT/consumer.dynamic")" -eq 1 ]

sha256sum \
    "$OUT/libziparchive_error_fixture.so" \
    "$OUT/libbionic_compat_error_fixture.so" \
    "$OUT/liberror_code_consumer.so" \
    | awk '{print $1}' | sha256sum | awk '{print $1}' >"$OUT/artifact.sha256"
