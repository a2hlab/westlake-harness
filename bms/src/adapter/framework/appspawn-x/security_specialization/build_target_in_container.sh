#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0

ROOT=/project
MODULE=$ROOT/adapter/framework/appspawn-x/security_specialization
OUT=$MODULE/out/target
TOOLCHAIN=$ROOT/.work/product-tls-generation/frozen/toolchain
SYSROOT=$ROOT/.work/product-tls-generation/frozen/sysroot
CC=$TOOLCHAIN/bin/clang-15
READELF=$TOOLCHAIN/bin/llvm-readelf
OBJDUMP=$TOOLCHAIN/bin/llvm-objdump

for input in \
    "$CC" \
    "$TOOLCHAIN/bin/ld.lld" \
    "$READELF" \
    "$OBJDUMP" \
    "$MODULE/include/westlake_oh_security_specialization.h" \
    "$MODULE/src/security_specialization.c" \
    "$MODULE/westlake_oh_security_specialization.map" \
    "$MODULE/verify_target_artifact.py"
do
    [[ -f "$input" ]] || {
        echo "ERROR missing project-local input: $input" >&2
        exit 1
    }
done

mkdir -p "$OUT/pass1" "$OUT/pass2" "$OUT/logs" "$OUT/tmp"
export TMPDIR=$OUT/tmp
: >"$OUT/logs/commands.txt"

run()
{
    printf '%q ' "$@" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$@"
}

build_pass()
{
    local pass=$1
    local dir=$OUT/$pass
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -std=c11 \
        -O2 \
        -Wall \
        -Wextra \
        -Werror \
        -pedantic \
        -ffreestanding \
        -fPIC \
        -fvisibility=hidden \
        -fno-stack-protector \
        -fno-unwind-tables \
        -fno-asynchronous-unwind-tables \
        -mno-outline-atomics \
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        -I"$MODULE/include" \
        -c "$MODULE/src/security_specialization.c" \
        -o "$dir/security_specialization.o"
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -fuse-ld=lld \
        -nostdlib \
        -shared \
        -Wl,-z,defs \
        -Wl,-z,now \
        -Wl,-z,relro \
        -Wl,--no-undefined \
        -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 \
        -Wl,--hash-style=both \
        -Wl,-soname,libwestlake_oh_security_specialization.so \
        -Wl,--version-script="$MODULE/westlake_oh_security_specialization.map" \
        "$dir/security_specialization.o" \
        -o "$dir/libwestlake_oh_security_specialization.so"
}

build_pass pass1
build_pass pass2
cmp "$OUT/pass1/libwestlake_oh_security_specialization.so" \
    "$OUT/pass2/libwestlake_oh_security_specialization.so"
cp "$OUT/pass1/libwestlake_oh_security_specialization.so" \
   "$OUT/libwestlake_oh_security_specialization.so"

python3 "$MODULE/verify_target_artifact.py" \
    --project-root "$ROOT" \
    --library "$OUT/libwestlake_oh_security_specialization.so" \
    --second-library "$OUT/pass2/libwestlake_oh_security_specialization.so" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/verification.json"

sha256sum \
    "$MODULE/include/westlake_oh_security_specialization.h" \
    "$MODULE/src/security_specialization.c" \
    "$MODULE/westlake_oh_security_specialization.map" \
    "$OUT/libwestlake_oh_security_specialization.so" \
    "$OUT/verification.json" >"$OUT/sha256.txt"

echo "PASS OH security specialization target control-plane deterministic=2 product_activation=false"
