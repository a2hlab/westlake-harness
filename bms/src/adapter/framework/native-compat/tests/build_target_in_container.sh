#!/usr/bin/env bash
# Build the audit-only target DSO twice from project-local frozen inputs.
# This file is invoked only inside the locked linux/amd64 tool container.

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1

ROOT=/project
MODULE=$ROOT/adapter/framework/native-compat
OUT=$MODULE/out/target
TOOLCHAIN=$ROOT/.work/product-tls-generation/frozen/toolchain
SYSROOT=$ROOT/.work/product-tls-generation/frozen/sysroot
CC=$TOOLCHAIN/bin/clang-15

for input in \
    "$CC" \
    "$TOOLCHAIN/bin/ld.lld" \
    "$TOOLCHAIN/bin/llvm-readelf" \
    "$TOOLCHAIN/bin/llvm-objdump" \
    "$MODULE/include/westlake_native_compat.h" \
    "$MODULE/src/native_compat_internal.h" \
    "$MODULE/src/process_state.c" \
    "$MODULE/tests/abi_layout_asserts.c" \
    "$MODULE/westlake_native_compat.map"
do
    [[ -f "$input" ]] || { echo "ERROR missing project-local input: $input" >&2; exit 1; }
done

mkdir -p "$OUT/pass1" "$OUT/pass2" "$OUT/tmp" "$OUT/logs"
export TMPDIR=$OUT/tmp
: >"$OUT/logs/commands.txt"

record()
{
    printf '%q ' "$@" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
}

build_one()
{
    local pass=$1
    local pass_dir=$OUT/$pass
    local object=$pass_dir/process_state.o
    local abi_object=$pass_dir/abi_layout_asserts.o
    local library=$pass_dir/libwestlake_native_compat.so
    local compile=(
        "$CC"
        --target=aarch64-linux-ohos
        --sysroot="$SYSROOT"
        -B"$TOOLCHAIN/bin"
        -std=c11
        -O2
        -Wall
        -Wextra
        -Werror
        -pedantic
        -fPIC
        -fvisibility=hidden
        -fno-stack-protector
        -fno-unwind-tables
        -fno-asynchronous-unwind-tables
        -ffile-prefix-map="$ROOT"=.
        -fdebug-prefix-map="$ROOT"=.
        -I"$MODULE/include"
        -I"$MODULE/src"
        -c "$MODULE/src/process_state.c"
        -o "$object"
    )
    local link=(
        "$CC"
        --target=aarch64-linux-ohos
        --sysroot="$SYSROOT"
        -B"$TOOLCHAIN/bin"
        -fuse-ld=lld
        -nostdlib
        -shared
        -Wl,-z,defs
        -Wl,-z,now
        -Wl,-z,relro
        -Wl,--no-undefined
        -Wl,--fatal-warnings
        -Wl,--build-id=sha1
        -Wl,--hash-style=both
        -Wl,-soname,libwestlake_native_compat.so
        -Wl,--version-script="$MODULE/westlake_native_compat.map"
        "$object"
        -o "$library"
    )
    record "${compile[@]}"
    "${compile[@]}" >"$OUT/logs/$pass.compile.stdout" \
        2>"$OUT/logs/$pass.compile.stderr"
    local abi_compile=(
        "$CC"
        --target=aarch64-linux-ohos
        --sysroot="$SYSROOT"
        -B"$TOOLCHAIN/bin"
        -std=c11
        -Wall
        -Wextra
        -Werror
        -pedantic
        -fPIC
        -fvisibility=hidden
        -I"$MODULE/include"
        -c "$MODULE/tests/abi_layout_asserts.c"
        -o "$abi_object"
    )
    record "${abi_compile[@]}"
    "${abi_compile[@]}" >"$OUT/logs/$pass.abi.compile.stdout" \
        2>"$OUT/logs/$pass.abi.compile.stderr"
    record "${link[@]}"
    "${link[@]}" >"$OUT/logs/$pass.link.stdout" \
        2>"$OUT/logs/$pass.link.stderr"
}

build_one pass1
build_one pass2

cmp "$OUT/pass1/libwestlake_native_compat.so" \
    "$OUT/pass2/libwestlake_native_compat.so"
cp "$OUT/pass1/libwestlake_native_compat.so" \
   "$OUT/libwestlake_native_compat.so"

python3 "$MODULE/tests/verify_target_artifact.py" \
    --project-root "$ROOT" \
    --library "$OUT/libwestlake_native_compat.so" \
    --second-library "$OUT/pass2/libwestlake_native_compat.so" \
    --readelf "$TOOLCHAIN/bin/llvm-readelf" \
    --objdump "$TOOLCHAIN/bin/llvm-objdump" \
    --report "$OUT/verification.json"

sha256sum \
    "$MODULE/include/westlake_native_compat.h" \
    "$MODULE/src/native_compat_internal.h" \
    "$MODULE/src/process_state.c" \
    "$MODULE/tests/abi_layout_asserts.c" \
    "$MODULE/westlake_native_compat.map" \
    "$OUT/libwestlake_native_compat.so" \
    "$OUT/verification.json" >"$OUT/sha256.txt"

echo "PASS target_aarch64_audit_only deterministic=2 no_tls=true no_init=true"
