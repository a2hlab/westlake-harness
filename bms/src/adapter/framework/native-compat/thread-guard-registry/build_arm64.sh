#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
MODULE=$SCRIPT_DIR
ADAPTER_ROOT=${ADAPTER_ROOT:?ADAPTER_ROOT is required}
OUT=${ADAPTER_OUT_DIR:?ADAPTER_OUT_DIR is required}
OBJ=${WLTG_OBJ_DIR:?WLTG_OBJ_DIR is required}
SYSROOT=${OH_SYSROOT:?OH_SYSROOT is required}
CC=${L03_A12_CC:?L03_A12_CC is required}
READELF=${L03_A12_READELF:?L03_A12_READELF is required}
OBJDUMP=${L03_A12_OBJDUMP:-$(dirname "$READELF")/llvm-objdump}
PYTHON=${L03_A12_PYTHON:-python3}
VERIFY=$MODULE/tests/verify_product_artifact.py
OUTPUT=$OUT/libwestlake_thread_guard_registry.so

[ "$MODULE" = "$ADAPTER_ROOT/framework/native-compat/thread-guard-registry" ] || {
    echo "ERROR: registry producer is outside ADAPTER_ROOT: $MODULE" >&2
    exit 2
}
for tool in "$CC" "$READELF" "$OBJDUMP"; do
    [ -x "$tool" ] || {
        echo "ERROR: missing executable registry tool: $tool" >&2
        exit 2
    }
done
for input in \
    "$VERIFY" \
    "$MODULE/include/westlake_thread_guard_registry.h" \
    "$MODULE/src/thread_guard_registry_internal.h" \
    "$MODULE/src/thread_guard_registry.c" \
    "$MODULE/src/guard_store_aarch64.S" \
    "$MODULE/westlake_thread_guard_registry.map"
do
    [ -f "$input" ] && [ ! -L "$input" ] || {
        echo "ERROR: missing regular registry input: $input" >&2
        exit 2
    }
done
[ -d "$SYSROOT" ] && [ ! -L "$SYSROOT" ] || {
    echo "ERROR: registry sysroot is missing or a symlink: $SYSROOT" >&2
    exit 2
}
if [ "${L03_A12_STRICT_BUILD:-0}" = 1 ]; then
    [ -n "${L03_A12_GENERATION_ID:-}" ] || {
        echo "ERROR: strict registry build requires L03_A12_GENERATION_ID" >&2
        exit 2
    }
fi

rm -rf "$OBJ"
mkdir -p "$OUT" "$OBJ/pass1" "$OBJ/pass2" "$OBJ/meta"

compile_pass()
{
    local pass=$1 pass_dir=$OBJ/$1
    "$CC" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
        -B"$(dirname "$CC")" -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
        -ffreestanding -fPIC -fvisibility=hidden -fno-stack-protector \
        -fno-unwind-tables -fno-asynchronous-unwind-tables -mno-outline-atomics \
        -ffile-prefix-map="$ADAPTER_ROOT"=/westlake/adapter \
        -fdebug-prefix-map="$ADAPTER_ROOT"=/westlake/adapter \
        -I"$MODULE/include" -I"$MODULE/src" \
        -c "$MODULE/src/thread_guard_registry.c" \
        -o "$pass_dir/thread_guard_registry.o"
    "$CC" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
        -B"$(dirname "$CC")" -ffreestanding -fPIC -fvisibility=hidden \
        -ffile-prefix-map="$ADAPTER_ROOT"=/westlake/adapter \
        -fdebug-prefix-map="$ADAPTER_ROOT"=/westlake/adapter \
        -c "$MODULE/src/guard_store_aarch64.S" \
        -o "$pass_dir/guard_store_aarch64.o"
    "$CC" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \
        -B"$(dirname "$CC")" -fuse-ld=lld -nostdlib -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro -Wl,--no-undefined \
        -Wl,--fatal-warnings -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libwestlake_thread_guard_registry.so \
        -Wl,--version-script="$MODULE/westlake_thread_guard_registry.map" \
        "$pass_dir/thread_guard_registry.o" "$pass_dir/guard_store_aarch64.o" \
        -o "$pass_dir/libwestlake_thread_guard_registry.so"
}

compile_pass pass1
compile_pass pass2
"$PYTHON" "$VERIFY" \
    --library "$OBJ/pass1/libwestlake_thread_guard_registry.so" \
    --second-library "$OBJ/pass2/libwestlake_thread_guard_registry.so" \
    --readelf "$READELF" --objdump "$OBJDUMP" \
    --report "$OBJ/meta/verification.json"
cp "$OBJ/pass1/libwestlake_thread_guard_registry.so" "$OUTPUT"

SHA256=$(sha256sum "$OUTPUT" | awk '{print $1}')
BUILD_ID=$("$READELF" --notes --wide "$OUTPUT" | awk '/Build ID:/ {print tolower($NF)}')
printf 'REGISTRY_BUILD_PASS generation=%s artifact=%s sha256=%s build_id=%s\n' \
    "${L03_A12_GENERATION_ID:-standalone}" "$OUTPUT" "$SHA256" "$BUILD_ID"
