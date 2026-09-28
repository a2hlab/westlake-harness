#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1

ROOT=/project
MODULE=$ROOT/adapter/framework/native-compat/thread-guard-registry
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
    "$MODULE/include/westlake_thread_guard_registry.h" \
    "$MODULE/src/thread_guard_registry_internal.h" \
    "$MODULE/src/thread_guard_registry.c" \
    "$MODULE/src/guard_store_aarch64.S" \
    "$MODULE/tests/abi_layout_asserts.c" \
    "$MODULE/tests/target/main_reservation_owner_aarch64.S" \
    "$MODULE/tests/target/mutants/hardcoded_owner_aarch64.S" \
    "$MODULE/tests/target/mutants/backend_tls_mutant.S" \
    "$MODULE/tests/target/mutants/backend_constructor_mutant.S" \
    "$MODULE/westlake_thread_guard_registry.map" \
    "$MODULE/tests/verify_target_artifact.py"
do
    [[ -f "$input" ]] || {
        echo "ERROR missing project-local input: $input" >&2
        exit 1
    }
done

mkdir -p "$OUT/pass1" "$OUT/pass2" "$OUT/mutants" \
         "$OUT/logs" "$OUT/tmp"
export TMPDIR=$OUT/tmp
: >"$OUT/logs/commands.txt"

record()
{
    printf '%q ' "$@" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
}

run()
{
    record "$@"
    "$@"
}

compile_c()
{
    local source=$1
    local output=$2
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
        -I"$MODULE/src" \
        -c "$source" \
        -o "$output"
}

compile_asm()
{
    local source=$1
    local output=$2
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -ffreestanding \
        -fPIC \
        -fvisibility=hidden \
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        -c "$source" \
        -o "$output"
}

link_registry()
{
    local output=$1
    shift
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
        -Wl,-soname,libwestlake_thread_guard_registry.so \
        -Wl,--version-script="$MODULE/westlake_thread_guard_registry.map" \
        "$@" \
        -o "$output"
}

build_pass()
{
    local pass=$1
    local pass_dir=$OUT/$pass
    compile_c "$MODULE/src/thread_guard_registry.c" \
        "$pass_dir/thread_guard_registry.o"
    compile_asm "$MODULE/src/guard_store_aarch64.S" \
        "$pass_dir/guard_store_aarch64.o"
    compile_c "$MODULE/tests/abi_layout_asserts.c" \
        "$pass_dir/abi_layout_asserts.o"
    link_registry "$pass_dir/libwestlake_thread_guard_registry.so" \
        "$pass_dir/thread_guard_registry.o" \
        "$pass_dir/guard_store_aarch64.o"
}

build_pass pass1
build_pass pass2
cmp "$OUT/pass1/libwestlake_thread_guard_registry.so" \
    "$OUT/pass2/libwestlake_thread_guard_registry.so"
cp "$OUT/pass1/libwestlake_thread_guard_registry.so" \
   "$OUT/libwestlake_thread_guard_registry.so"

compile_asm "$MODULE/tests/target/main_reservation_owner_aarch64.S" \
    "$OUT/main_reservation_owner_aarch64.o"
compile_asm "$MODULE/tests/target/mutants/hardcoded_owner_aarch64.S" \
    "$OUT/mutants/hardcoded_owner_aarch64.o"
compile_asm "$MODULE/tests/target/mutants/backend_tls_mutant.S" \
    "$OUT/mutants/backend_tls_mutant.o"
compile_asm "$MODULE/tests/target/mutants/backend_constructor_mutant.S" \
    "$OUT/mutants/backend_constructor_mutant.o"

link_registry "$OUT/mutants/libregistry_with_tls.so" \
    "$OUT/pass1/thread_guard_registry.o" \
    "$OUT/pass1/guard_store_aarch64.o" \
    "$OUT/mutants/backend_tls_mutant.o"
link_registry "$OUT/mutants/libregistry_with_constructor.so" \
    "$OUT/pass1/thread_guard_registry.o" \
    "$OUT/pass1/guard_store_aarch64.o" \
    "$OUT/mutants/backend_constructor_mutant.o"

python3 "$MODULE/tests/verify_target_artifact.py" \
    --project-root "$ROOT" \
    --library "$OUT/libwestlake_thread_guard_registry.so" \
    --second-library "$OUT/pass2/libwestlake_thread_guard_registry.so" \
    --owner-object "$OUT/main_reservation_owner_aarch64.o" \
    --hardcoded-owner-object "$OUT/mutants/hardcoded_owner_aarch64.o" \
    --tls-mutant "$OUT/mutants/libregistry_with_tls.so" \
    --constructor-mutant "$OUT/mutants/libregistry_with_constructor.so" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/verification.json"

sha256sum \
    "$MODULE/include/westlake_thread_guard_registry.h" \
    "$MODULE/src/thread_guard_registry_internal.h" \
    "$MODULE/src/thread_guard_registry.c" \
    "$MODULE/src/guard_store_aarch64.S" \
    "$MODULE/tests/abi_layout_asserts.c" \
    "$MODULE/tests/target/main_reservation_owner_aarch64.S" \
    "$MODULE/westlake_thread_guard_registry.map" \
    "$OUT/libwestlake_thread_guard_registry.so" \
    "$OUT/verification.json" >"$OUT/sha256.txt"

echo "PASS target AArch64 registry deterministic=2 structural_mutants=3 product_activation=false"
