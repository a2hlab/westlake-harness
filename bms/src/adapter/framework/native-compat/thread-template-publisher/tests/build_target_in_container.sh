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
MODULE=$ROOT/adapter/framework/native-compat/thread-template-publisher
OUT=$MODULE/out/target
TOOLCHAIN=$ROOT/.work/product-tls-generation/frozen/toolchain
SYSROOT=$ROOT/.work/product-tls-generation/frozen/sysroot
CC=$TOOLCHAIN/bin/clang-15
READELF=$TOOLCHAIN/bin/llvm-readelf
OBJDUMP=$TOOLCHAIN/bin/llvm-objdump
HEADER=$MODULE/include/westlake_thread_template_publisher.h
PUBLISHER=$MODULE/src/thread_template_publisher.c
TARGET=$MODULE/tests/target/template_publisher_target.c
TLS_ASM=$MODULE/tests/target/main_tls_template_aarch64.S
VERIFY=$MODULE/tests/verify_target_fixture.py

for input in \
    "$CC" \
    "$TOOLCHAIN/bin/ld.lld" \
    "$READELF" \
    "$OBJDUMP" \
    "$SYSROOT/lib/aarch64-linux-ohos/Scrt1.o" \
    "$SYSROOT/lib/aarch64-linux-ohos/libc.so" \
    "$HEADER" \
    "$PUBLISHER" \
    "$TARGET" \
    "$TLS_ASM" \
    "$VERIFY"
do
    [[ -f "$input" ]] || {
        echo "ERROR missing project-local target input: $input" >&2
        exit 2
    }
done

mkdir -p \
    "$OUT/pass1" "$OUT/pass2" \
    "$OUT/mutants/unpatched" \
    "$OUT/mutants/wrong-offset" \
    "$OUT/mutants/wrong-image" \
    "$OUT/mutants/no-restore" \
    "$OUT/mutants/conflict" \
    "$OUT/mutants/no-exact-once" \
    "$OUT/mutants/skip-child-reset" \
    "$OUT/mutants/reuse-parent-template" \
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
    shift 2
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -I"$SYSROOT/include/aarch64-linux-ohos" \
        -I"$MODULE/include" \
        -std=c11 \
        -O2 \
        -Wall \
        -Wextra \
        -Werror \
        -fPIE \
        -fvisibility=hidden \
        -fno-stack-protector \
        -fno-unwind-tables \
        -fno-asynchronous-unwind-tables \
        -mno-outline-atomics \
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        "$@" \
        -c "$source" \
        -o "$output"
}

compile_asm()
{
    local output=$1
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -fPIE \
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        -c "$TLS_ASM" \
        -o "$output"
}

link_fixture()
{
    local output=$1
    local directory=$2
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -B"$SYSROOT/lib/aarch64-linux-ohos" \
        -L"$SYSROOT/lib/aarch64-linux-ohos" \
        -fuse-ld=lld \
        -fPIE \
        -pie \
        -Wl,-z,defs \
        -Wl,-z,now \
        -Wl,-z,relro \
        -Wl,--no-undefined \
        -Wl,--no-allow-shlib-undefined \
        -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 \
        -Wl,--hash-style=both \
        -Wl,--dynamic-linker,/lib/ld-musl-aarch64.so.1 \
        "$directory/target.o" \
        "$directory/publisher.o" \
        "$directory/main_tls.o" \
        -ldl \
        -lpthread \
        -lc \
        -o "$output"
}

build_variant()
{
    local directory=$1
    shift
    compile_c "$TARGET" "$directory/target.o"
    compile_c "$PUBLISHER" "$directory/publisher.o" "$@"
    compile_asm "$directory/main_tls.o"
    link_fixture "$directory/thread-template-target" "$directory"
}

build_variant "$OUT/pass1"
build_variant "$OUT/pass2"
cmp "$OUT/pass1/thread-template-target" "$OUT/pass2/thread-template-target"
cp "$OUT/pass1/thread-template-target" "$OUT/thread-template-target"

build_variant "$OUT/mutants/unpatched" -DWLTP_MUTANT_UNPATCHED
build_variant "$OUT/mutants/wrong-offset" -DWLTP_MUTANT_WRONG_OFFSET
build_variant "$OUT/mutants/wrong-image" -DWLTP_MUTANT_WRONG_IMAGE
build_variant "$OUT/mutants/no-restore" -DWLTP_MUTANT_NO_RESTORE
build_variant "$OUT/mutants/conflict" -DWLTP_MUTANT_COMPETING_WRITER
build_variant "$OUT/mutants/no-exact-once" -DWLTP_MUTANT_NO_EXACT_ONCE
build_variant "$OUT/mutants/skip-child-reset" \
    -DWLTP_MUTANT_SKIP_CHILD_RESET
build_variant "$OUT/mutants/reuse-parent-template" \
    -DWLTP_MUTANT_REUSE_PARENT_TEMPLATE

python3 "$VERIFY" \
    --valid "$OUT/thread-template-target" \
    --second-valid "$OUT/pass2/thread-template-target" \
    --unpatched "$OUT/mutants/unpatched/thread-template-target" \
    --wrong-offset "$OUT/mutants/wrong-offset/thread-template-target" \
    --wrong-image "$OUT/mutants/wrong-image/thread-template-target" \
    --protection-not-restored \
        "$OUT/mutants/no-restore/thread-template-target" \
    --conflict "$OUT/mutants/conflict/thread-template-target" \
    --no-exact-once "$OUT/mutants/no-exact-once/thread-template-target" \
    --skip-child-reset \
        "$OUT/mutants/skip-child-reset/thread-template-target" \
    --reuse-parent-template \
        "$OUT/mutants/reuse-parent-template/thread-template-target" \
    --output "$OUT/target-verification.json"

sha256sum \
    "$HEADER" \
    "$PUBLISHER" \
    "$TARGET" \
    "$TLS_ASM" \
    "$VERIFY" \
    "$OUT/thread-template-target" \
    "$OUT/target-verification.json" \
    >"$OUT/build-inputs.sha256"

echo "PASS AArch64 product-publisher build deterministic=2 structural_mutants=9"
