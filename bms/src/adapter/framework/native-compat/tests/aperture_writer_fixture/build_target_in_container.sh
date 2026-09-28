#!/usr/bin/env bash
# Build the disabled PR-08A fixture twice from project-local frozen inputs.
# Invoked only inside the locked linux/amd64 tool container.

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1

ROOT=/project
FIXTURE=$ROOT/adapter/framework/native-compat/tests/aperture_writer_fixture
CORE=$ROOT/adapter/framework/native-compat
RESERVATION=$ROOT/adapter/framework/appspawn-x/tls_prefix/bionic_tls_prefix_reservation.cpp
OUT=$FIXTURE/out/target
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
    "$RESERVATION" \
    "$FIXTURE/include/wlnc_aperture_fixture.h" \
    "$FIXTURE/src/aperture_writer.c" \
    "$FIXTURE/src/aperture_store_readback_aarch64.S" \
    "$FIXTURE/fixture/test_fixture_signing.c" \
    "$FIXTURE/target/reservation_owner_aarch64.S" \
    "$FIXTURE/target/fixture_start_aarch64.S" \
    "$FIXTURE/target/fixture_getrandom_aarch64.S" \
    "$FIXTURE/target/fixture_main.c" \
    "$FIXTURE/wlnc_aperture_fixture.map" \
    "$FIXTURE/verify_target_artifacts.py" \
    "$CORE/include/westlake_native_compat.h" \
    "$CORE/src/native_compat_internal.h" \
    "$CORE/src/process_state.c" \
    "$CORE/tests/abi_layout_asserts.c" \
    "$CORE/westlake_native_compat.map"
do
    [[ -f "$input" ]] || {
        echo "ERROR missing project-local input: $input" >&2
        exit 1
    }
done

mkdir -p "$OUT/pass1" "$OUT/pass2" "$OUT/mutants" \
         "$OUT/core/pass1" "$OUT/core/pass2" "$OUT/logs" "$OUT/tmp"
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
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        -I"$FIXTURE/include" \
        -I"$FIXTURE/fixture" \
        -I"$CORE/include" \
        "$@" \
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
        -ffile-prefix-map="$ROOT"=. \
        -c "$source" \
        -o "$output"
}

link_backend()
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
        -Wl,-soname,libwestlake_aperture_fixture_backend.so \
        -Wl,--version-script="$FIXTURE/wlnc_aperture_fixture.map" \
        "$@" \
        -o "$output"
}

build_fixture_pass()
{
    local pass=$1
    local dir=$OUT/$pass
    compile_c "$FIXTURE/src/aperture_writer.c" "$dir/aperture_writer.o"
    compile_asm "$FIXTURE/src/aperture_store_readback_aarch64.S" \
        "$dir/aperture_store_readback.o"
    link_backend "$dir/libwestlake_aperture_fixture_backend.so" \
        "$dir/aperture_writer.o" "$dir/aperture_store_readback.o"

    compile_c "$FIXTURE/fixture/test_fixture_signing.c" \
        "$dir/test_fixture_signing.o"
    compile_c "$FIXTURE/target/fixture_main.c" "$dir/fixture_main.o" -fPIE
    compile_asm "$FIXTURE/target/reservation_owner_aarch64.S" \
        "$dir/reservation_owner.o"
    compile_asm "$FIXTURE/target/fixture_start_aarch64.S" \
        "$dir/fixture_start.o"
    compile_asm "$FIXTURE/target/fixture_getrandom_aarch64.S" \
        "$dir/fixture_getrandom.o"
    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -x c++ \
        -std=c++17 \
        -O2 \
        -Wall \
        -Wextra \
        -Werror \
        -fPIE \
        -fvisibility=hidden \
        -fno-stack-protector \
        -fno-exceptions \
        -fno-rtti \
        -fno-unwind-tables \
        -fno-asynchronous-unwind-tables \
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        -c "$RESERVATION" \
        -o "$dir/bionic_tls_prefix_reservation.o"

    run "$CC" \
        --target=aarch64-linux-ohos \
        --sysroot="$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -fuse-ld=lld \
        -nostdlib \
        -pie \
        -Wl,-e,_start \
        -Wl,-z,defs \
        -Wl,-z,now \
        -Wl,-z,relro \
        -Wl,--no-undefined \
        -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 \
        -Wl,--hash-style=both \
        -Wl,--dynamic-linker,/lib/ld-musl-aarch64.so.1 \
        "$dir/fixture_start.o" \
        "$dir/fixture_main.o" \
        "$dir/test_fixture_signing.o" \
        "$dir/reservation_owner.o" \
        "$dir/fixture_getrandom.o" \
        "$dir/bionic_tls_prefix_reservation.o" \
        "$dir/libwestlake_aperture_fixture_backend.so" \
        -o "$dir/wlaf_aperture_owner_fixture"
}

build_core_pass()
{
    local pass=$1
    local dir=$OUT/core/$pass
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
        -fPIC \
        -fvisibility=hidden \
        -fno-stack-protector \
        -fno-unwind-tables \
        -fno-asynchronous-unwind-tables \
        -ffile-prefix-map="$ROOT"=. \
        -fdebug-prefix-map="$ROOT"=. \
        -I"$CORE/include" \
        -I"$CORE/src" \
        -c "$CORE/src/process_state.c" \
        -o "$dir/process_state.o"
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
        -Wl,-soname,libwestlake_native_compat.so \
        -Wl,--version-script="$CORE/westlake_native_compat.map" \
        "$dir/process_state.o" \
        -o "$dir/libwestlake_native_compat.so"
}

build_fixture_pass pass1
build_fixture_pass pass2
build_core_pass pass1
build_core_pass pass2

cmp "$OUT/pass1/libwestlake_aperture_fixture_backend.so" \
    "$OUT/pass2/libwestlake_aperture_fixture_backend.so"
cmp "$OUT/pass1/wlaf_aperture_owner_fixture" \
    "$OUT/pass2/wlaf_aperture_owner_fixture"
cmp "$OUT/core/pass1/libwestlake_native_compat.so" \
    "$OUT/core/pass2/libwestlake_native_compat.so"

cp "$OUT/pass1/libwestlake_aperture_fixture_backend.so" \
   "$OUT/libwestlake_aperture_fixture_backend.so"
cp "$OUT/pass1/wlaf_aperture_owner_fixture" \
   "$OUT/wlaf_aperture_owner_fixture"
cp "$OUT/core/pass1/libwestlake_native_compat.so" \
   "$OUT/core/libwestlake_native_compat.so"

# Target negative ELF/instruction mutants.  They are never copied to a
# product output and the verifier must reject every one.
compile_asm "$FIXTURE/target/mutants/backend_tls_mutant.S" \
    "$OUT/mutants/backend_tls_mutant.o"
link_backend "$OUT/mutants/libbackend_with_tls.so" \
    "$OUT/pass1/aperture_writer.o" \
    "$OUT/pass1/aperture_store_readback.o" \
    "$OUT/mutants/backend_tls_mutant.o"

compile_asm "$FIXTURE/target/mutants/backend_constructor_mutant.S" \
    "$OUT/mutants/backend_constructor_mutant.o"
link_backend "$OUT/mutants/libbackend_with_constructor.so" \
    "$OUT/pass1/aperture_writer.o" \
    "$OUT/pass1/aperture_store_readback.o" \
    "$OUT/mutants/backend_constructor_mutant.o"

compile_asm "$FIXTURE/target/mutants/hardcoded_owner_aarch64.S" \
    "$OUT/mutants/hardcoded_owner.o"
run "$CC" \
    --target=aarch64-linux-ohos \
    --sysroot="$SYSROOT" \
    -B"$TOOLCHAIN/bin" \
    -fuse-ld=lld \
    -nostdlib \
    -pie \
    -Wl,-e,_start \
    -Wl,-z,defs \
    -Wl,-z,now \
    -Wl,-z,relro \
    -Wl,--no-undefined \
    -Wl,--fatal-warnings \
    -Wl,--build-id=sha1 \
    -Wl,--hash-style=both \
    -Wl,--dynamic-linker,/lib/ld-musl-aarch64.so.1 \
    "$OUT/pass1/fixture_start.o" \
    "$OUT/pass1/fixture_main.o" \
    "$OUT/pass1/test_fixture_signing.o" \
    "$OUT/mutants/hardcoded_owner.o" \
    "$OUT/pass1/fixture_getrandom.o" \
    "$OUT/pass1/bionic_tls_prefix_reservation.o" \
    "$OUT/pass1/libwestlake_aperture_fixture_backend.so" \
    -o "$OUT/mutants/wlaf_hardcoded_owner_fixture"

python3 "$CORE/tests/verify_target_artifact.py" \
    --project-root "$ROOT" \
    --library "$OUT/core/libwestlake_native_compat.so" \
    --second-library "$OUT/core/pass2/libwestlake_native_compat.so" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/core/verification.json"

python3 "$FIXTURE/verify_target_artifacts.py" \
    --project-root "$ROOT" \
    --backend "$OUT/libwestlake_aperture_fixture_backend.so" \
    --second-backend "$OUT/pass2/libwestlake_aperture_fixture_backend.so" \
    --main "$OUT/wlaf_aperture_owner_fixture" \
    --second-main "$OUT/pass2/wlaf_aperture_owner_fixture" \
    --owner-object "$OUT/pass1/reservation_owner.o" \
    --core "$OUT/core/libwestlake_native_compat.so" \
    --tls-mutant "$OUT/mutants/libbackend_with_tls.so" \
    --constructor-mutant "$OUT/mutants/libbackend_with_constructor.so" \
    --hardcoded-owner-mutant "$OUT/mutants/wlaf_hardcoded_owner_fixture" \
    --hardcoded-owner-object "$OUT/mutants/hardcoded_owner.o" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/verification.json"

sha256sum \
    "$FIXTURE/include/wlnc_aperture_fixture.h" \
    "$FIXTURE/src/aperture_writer.c" \
    "$FIXTURE/src/aperture_store_readback_aarch64.S" \
    "$FIXTURE/target/reservation_owner_aarch64.S" \
    "$RESERVATION" \
    "$OUT/libwestlake_aperture_fixture_backend.so" \
    "$OUT/wlaf_aperture_owner_fixture" \
    "$OUT/core/libwestlake_native_compat.so" \
    "$OUT/verification.json" >"$OUT/sha256.txt"

echo "PASS aperture target fixture deterministic=2 product_activation=false"
