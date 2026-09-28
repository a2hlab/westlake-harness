#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1

ROOT=${ROUTE_A_PROJECT_ROOT:-/project}
PLUGIN=$ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin
ADAPTER=$ROOT/adapter/framework/appspawn-x
REGISTRY=$ROOT/adapter/framework/native-compat/thread-guard-registry
JNI_ATTACH=$ROOT/adapter/framework/native-compat/jni-attach-admission
PTHREAD_BRIDGE=$ROOT/adapter/framework/native-compat/bionic-pthread-bridge
PUBLISHER=$ROOT/adapter/framework/native-compat/thread-template-publisher
COMPAT_SRC=$ADAPTER/bionic_compat/src
COMPAT_INC=$ADAPTER/bionic_compat/include
APP_LOADER=$ROOT/adapter/framework/app-native-loader
NATIVE_LOADER=$ROOT/adapter/framework/native-loader-oh
ART_PALETTE=$ROOT/adapter/framework/art-palette-oh
OH_ZLIB=$ROOT/upstream/openharmony-6.1.0.31/third_party/zlib
OH=$ROOT/adapter/frozen/references/oh-appspawn-security-v7
TARGET_COHORT_HEADER=$ROOT/upstream/openharmony-6.1.0.31/base/startup/appspawn/standard/appspawn_manager.h
COHORT_OVERLAY_DIR=$PLUGIN/out/abi-cohort/OpenHarmony-6.1.0.31/standard
COHORT_OVERLAY=$COHORT_OVERLAY_DIR/appspawn_manager.h
STOCK_COMMON=$PLUGIN/frozen/stock_host/abi/libappspawn_common.z.so
BASE_GENERATION_ROOT=${WESTLAKE_GENERATION_ROOT:-$ROOT/.work/product-tls-generation}
BASE_GEN=$BASE_GENERATION_ROOT/frozen
FROZEN=$PLUGIN/frozen/runtime_provider
R45_DYNAMIC_ROOTS=$ROOT/adapter/frozen/r45-dynamic-roots
BASE_PROVIDER_ROOT=${WESTLAKE_ROUTE_A_BASE_PROVIDER_ROOT:-$FROZEN/provider-v12}
V12=$BASE_PROVIDER_ROOT/providers
V12_DEPS=${WESTLAKE_ROUTE_A_BASE_PROVIDER_DEPENDENCIES:-$FROZEN/provider-v12/dependencies}
OUT=$PLUGIN/out/route-a-generation
TOOLCHAIN=$BASE_GEN/toolchain
SYSROOT=$BASE_GEN/sysroot
TARGET=aarch64-linux-ohos
TARGET_LIB=$SYSROOT/lib/$TARGET
CXX=$TOOLCHAIN/bin/clang-15
CC=$TOOLCHAIN/bin/clang-15
READELF=$TOOLCHAIN/bin/llvm-readelf
OBJDUMP=$TOOLCHAIN/bin/llvm-objdump
BUILTINS=$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a

for identity_name in \
    WLAR_ADAPTER_BRIDGE_PATH \
    WLAR_ADAPTER_BRIDGE_SHA256_HEX \
    WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX \
    WLAR_ANDROID_RUNTIME_PATH \
    WLAR_ANDROID_RUNTIME_SHA256_HEX \
    WLAR_ANDROID_RUNTIME_BUILD_ID_HEX \
    WLASC_P0_TYPED_REJECT_CAPABILITIES
do
    [[ -n ${!identity_name:-} ]] || {
        echo "ERROR missing mandatory R45 identity: $identity_name" >&2
        exit 1
    }
done
[[ $WLASC_P0_TYPED_REJECT_CAPABILITIES == 1 ]] || {
    echo "ERROR this P0 generation requires typed-reject hook isolation" >&2
    exit 1
}
[[ $WLAR_ADAPTER_BRIDGE_PATH == /* && $WLAR_ANDROID_RUNTIME_PATH == /* ]] || {
    echo "ERROR R45 runtime identities require absolute deploy paths" >&2
    exit 1
}
for identity_sha in \
    "$WLAR_ADAPTER_BRIDGE_SHA256_HEX" \
    "$WLAR_ANDROID_RUNTIME_SHA256_HEX"
do
    [[ $identity_sha =~ ^[0-9a-f]{64}$ ]] || {
        echo "ERROR invalid R45 SHA-256 identity: $identity_sha" >&2
        exit 1
    }
done
for identity_build_id in \
    "$WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX" \
    "$WLAR_ANDROID_RUNTIME_BUILD_ID_HEX"
do
    [[ $identity_build_id =~ ^[0-9a-f]{40}$ ]] || {
        echo "ERROR invalid R45 Build-ID identity: $identity_build_id" >&2
        exit 1
    }
done

for input in \
    "$ROOT/adapter/out/aosp_lib_arm64/libsigchain.so" \
    "$CXX" \
    "$TOOLCHAIN/bin/ld.lld" \
    "$READELF" \
    "$OBJDUMP" \
    "$TOOLCHAIN/bin/llvm-dwarfdump" \
    "$BUILTINS" \
    "$PLUGIN/SOURCE_CLOSURE.json" \
    "$PLUGIN/ROUTE_A_INPUTS.json" \
	    "$PLUGIN/build_target_in_container.sh" \
	    "$PLUGIN/generate_generation_metadata.py" \
    "$PLUGIN/r45_adapter_identity.env" \
    "$R45_DYNAMIC_ROOTS/SHA256SUMS" \
    "$R45_DYNAMIC_ROOTS/liboh_adapter_bridge.so" \
    "$R45_DYNAMIC_ROOTS/liboh_android_runtime.so" \
    "$PLUGIN/include/westlake_android_child_plugin.h" \
    "$PLUGIN/include/host_runtime_services.h" \
    "$PLUGIN/include/runtime_loader_phase.h" \
	    "$PLUGIN/include/sealed_child_provider_loader.h" \
	    "$PLUGIN/include/westlake_generation_identity_facts.h" \
	    "$PLUGIN/include/westlake_generation_identity_ops.h" \
	    "$PLUGIN/include/westlake_generation_identity_producer.h" \
    "$PLUGIN/include/westlake_child_hook_table_v1.h" \
    "$PLUGIN/include/westlake_elf_identity.h" \
    "$PLUGIN/include/westlake_sha256.h" \
    "$PLUGIN/include/westlake_stock_host_services.h" \
    "$PLUGIN/src/host_runtime_services.c" \
    "$PLUGIN/src/runtime_loader_phase.c" \
    "$PLUGIN/src/sealed_child_provider_loader.c" \
    "$PLUGIN/src/westlake_generation_identity_facts.c" \
    "$PLUGIN/src/westlake_generation_identity_ops.c" \
    "$PLUGIN/src/child_hook_table_v1.c" \
    "$PLUGIN/src/westlake_elf_identity.c" \
    "$PLUGIN/src/westlake_sha256.c" \
    "$PLUGIN/src/westlake_android_runtime_provider.cpp" \
    "$PLUGIN/westlake_android_runtime_provider.map" \
    "$PLUGIN/westlake_stock_host.map" \
    "$PLUGIN/verify_route_a_generation.py" \
    "$PLUGIN/verify_appspawn_host_abi.py" \
    "$PLUGIN/generate_appspawn_manager_abi_overlay.py" \
    "$OH/base/startup/appspawn/standard/appspawn_manager.h" \
    "$TARGET_COHORT_HEADER" \
    "$STOCK_COMMON" \
    "$ADAPTER/src/appspawnx_runtime.cpp" \
    "$ADAPTER/src/adapter_bridge_identity.cpp" \
    "$ADAPTER/src/adapter_bridge_identity.h" \
    "$ADAPTER/src/child_main_after_stock.cpp" \
    "$ADAPTER/src/native_compat_prepare.cpp" \
    "$ADAPTER/src/native_compat_prepare.h" \
    "$ADAPTER/src/native_compat_prepare_owner_aarch64.S" \
    "$ADAPTER/tls_prefix/bionic_tls_prefix_reservation.cpp" \
    "$REGISTRY/include/westlake_thread_guard_registry.h" \
    "$REGISTRY/src/thread_guard_registry.c" \
    "$REGISTRY/src/thread_guard_registry_internal.h" \
    "$REGISTRY/src/guard_store_aarch64.S" \
    "$REGISTRY/westlake_thread_guard_registry.map" \
    "$JNI_ATTACH/include/westlake_jni_attach_admission.h" \
    "$JNI_ATTACH/src/jni_attach_admission.cpp" \
    "$JNI_ATTACH/tests/verify_compile_closure.py" \
    "$PTHREAD_BRIDGE/include/westlake_bionic_pthread_bridge.h" \
    "$PTHREAD_BRIDGE/src/bionic_pthread_bridge.c" \
    "$PTHREAD_BRIDGE/westlake_bionic_pthread_bridge.map" \
    "$PUBLISHER/include/westlake_thread_template_publisher.h" \
    "$PUBLISHER/src/thread_template_publisher.c" \
    "$COMPAT_SRC/system_properties.cpp" \
    "$COMPAT_SRC/malloc_compat.cpp" \
    "$COMPAT_SRC/fdsan_stubs.cpp" \
    "$COMPAT_SRC/misc_compat.cpp" \
    "$COMPAT_SRC/abort_message_compat.cpp" \
    "$COMPAT_SRC/liblog_android_supplement.cpp" \
    "$COMPAT_SRC/sync_builtins.c" \
    "$COMPAT_INC/libcxx_compat.h" \
    "$APP_LOADER/include/app_native_loader.h" \
    "$APP_LOADER/include/oh_dlns_abi.h" \
    "$APP_LOADER/src/app_native_loader.c" \
    "$APP_LOADER/app_native_loader.map" \
    "$NATIVE_LOADER/include/nativeloader/native_loader.h" \
    "$NATIVE_LOADER/include/nativeloader/native_bridge_policy.h" \
    "$NATIVE_LOADER/src/native_loader.cpp" \
    "$NATIVE_LOADER/src/native_loader_registry.cpp" \
    "$NATIVE_LOADER/src/native_loader_registry.h" \
    "$NATIVE_LOADER/src/system_loader.cpp" \
    "$NATIVE_LOADER/src/system_loader.h" \
    "$NATIVE_LOADER/native_loader.map" \
    "$NATIVE_LOADER/policy/native_bridge_policy.v1.json" \
    "$ART_PALETTE/src/palette_oh.c" \
    "$ART_PALETTE/art_palette_oh.map" \
    "$OH_ZLIB/BUILD.gn" \
    "$OH_ZLIB/adler32.c" \
    "$OH_ZLIB/compress.c" \
    "$OH_ZLIB/contrib/minizip/ioapi.c" \
    "$OH_ZLIB/contrib/minizip/unzip.c" \
    "$OH_ZLIB/contrib/minizip/zip.c" \
    "$OH_ZLIB/crc32.c" \
    "$OH_ZLIB/deflate.c" \
    "$OH_ZLIB/gzclose.c" \
    "$OH_ZLIB/gzlib.c" \
    "$OH_ZLIB/gzread.c" \
    "$OH_ZLIB/gzwrite.c" \
    "$OH_ZLIB/infback.c" \
    "$OH_ZLIB/inffast.c" \
    "$OH_ZLIB/inflate.c" \
    "$OH_ZLIB/inftrees.c" \
    "$OH_ZLIB/trees.c" \
    "$OH_ZLIB/uncompr.c" \
    "$OH_ZLIB/zutil.c" \
    "$OH_ZLIB/zconf.h" \
    "$OH_ZLIB/zlib.h" \
    "$BASE_PROVIDER_ROOT/base-providers.sha256" \
    "$BASE_PROVIDER_ROOT/base-verification.json" \
    "$V12/libart.so" \
    "$V12/liblog.so" \
    "$V12/libnativehelper.so" \
    "$V12/libnativeloader.so" \
    "$V12/libapp_native_loader.so" \
    "$V12_DEPS/libshared_libz.z.so" \
    "$FROZEN/libraries/oh/libc++.so" \
    "$FROZEN/libraries/oh/libhilog.so"
do
    [[ -f "$input" ]] || {
        echo "ERROR missing frozen Route A input: $input" >&2
        exit 1
    }
done

BASE_PROVIDER_COUNT=$(wc -l <"$BASE_PROVIDER_ROOT/base-providers.sha256" | tr -d ' ')
V12_PROVIDER_COUNT=$(find "$V12" -maxdepth 1 -type f -name '*.so' | wc -l | tr -d ' ')
[[ "$V12_PROVIDER_COUNT" == "$((BASE_PROVIDER_COUNT - 1))" ]] || {
    echo "ERROR expected $((BASE_PROVIDER_COUNT - 1)) frozen non-compat providers, found $V12_PROVIDER_COUNT" >&2
    exit 1
}

python3 "$PLUGIN/generate_source_closure.py" --verify
python3 "$PLUGIN/generate_route_a_inputs.py" --verify
python3 "$JNI_ATTACH/tests/verify_compile_closure.py" \
    --adapter-root "$ROOT/adapter"
(
    cd "$BASE_GEN"
    sha256sum -c "$BASE_GENERATION_ROOT/frozen.sha256" >/dev/null
)

mkdir -p \
    "$OUT/pass1/provider" "$OUT/pass2/provider" \
    "$OUT/pass1/compat" "$OUT/pass2/compat" \
    "$OUT/pass1/registry" "$OUT/pass2/registry" \
    "$OUT/pass1/pthread-bridge" "$OUT/pass2/pthread-bridge" \
    "$OUT/pass1/app-loader" "$OUT/pass2/app-loader" \
    "$OUT/pass1/native-loader" "$OUT/pass2/native-loader" \
    "$OUT/pass1/palette" "$OUT/pass2/palette" \
    "$OUT/pass1/zlib" "$OUT/pass2/zlib" \
    "$OUT/logs" "$OUT/tmp"
export TMPDIR=$OUT/tmp
: >"$OUT/logs/commands.txt"

record()
{
    printf '%q ' "$@" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$@"
}

COMMON=(
    "--target=$TARGET"
    "--sysroot=$SYSROOT"
    -B"$TOOLCHAIN/bin"
    -fPIC
    -O2
    -g
    -fvisibility=hidden
    -ffunction-sections
    -fdata-sections
    -D__OHOS__
    -D_GNU_SOURCE
    -D_POSIX_SOURCE
    -ffile-prefix-map="$ROOT"=.
    -fdebug-prefix-map="$ROOT"=.
    -isystem "$SYSROOT/include/$TARGET"
    -Wno-unused-parameter
    -Wno-format
    -Wno-sign-compare
    -Wno-missing-field-initializers
    -Wno-c99-designator
    -Wno-gnu-designator
    -Wno-extern-c-compat
    -Wno-deprecated-declarations
    -Wno-c++11-narrowing
    -Wno-error
)

# libcxx_compat.h auto-detects whether this libc++ already provides the math /
# abs / span compatibility blocks, but the probe (<__math/traits.h>) is only a
# heuristic.  A build that knows its exact toolchain generation may state the
# answer instead; leaving the variable unset keeps the historical behaviour.
if [[ -n ${WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT:-} ]]; then
    COMMON+=("-DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=$WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT")
fi

CXX_STD=(
    -nostdinc++
    -isystem "$TOOLCHAIN/include/c++/v1"
    -std=gnu++17
)

INCLUDES=(
    -I"$PLUGIN/include"
    -I"$ADAPTER/src"
    -I"$JNI_ATTACH/include"
    -I"$BASE_GEN/includes/oh/hilog"
    -I"$BASE_GEN/includes/aosp/libnativehelper/include_jni"
    -I"$BASE_GEN/includes/aosp/libnativehelper/include"
    -I"$BASE_GEN/includes/aosp/libnativehelper/include_platform_header_only"
    -I"$BASE_GEN/includes/aosp/libnativehelper/include_platform"
    -I"$BASE_GEN/sources/bionic_compat/include"
    -I"$APP_LOADER/include"
    -I"$NATIVE_LOADER/include"
    -I"$PTHREAD_BRIDGE/include"
    -I"$REGISTRY/include"
)

GENERATION_SHA=$(sha256sum "$PLUGIN/ROUTE_A_INPUTS.json" | awk '{print $1}')
[[ $GENERATION_SHA =~ ^[0-9a-f]{64}$ ]] || {
    echo "ERROR invalid provider generation identity" >&2
    exit 1
}

PLUGIN_BUILD_ID_HEX=${GENERATION_SHA:0:40}
[[ $PLUGIN_BUILD_ID_HEX =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR invalid deterministic plugin Build-ID" >&2
    exit 1
}

build_registry()
{
    local pass=$1
    local dir=$OUT/$pass/registry
    record "$CC" "${COMMON[@]}" \
        -std=c11 -Wall -Wextra -Werror -pedantic \
        -ffreestanding -fno-stack-protector -fno-unwind-tables \
        -fno-asynchronous-unwind-tables -mno-outline-atomics \
        -I"$REGISTRY/include" -I"$REGISTRY/src" \
        -c "$REGISTRY/src/thread_guard_registry.c" \
        -o "$dir/thread_guard_registry.o"
    record "$CC" "${COMMON[@]}" \
        -ffreestanding -fno-stack-protector \
        -c "$REGISTRY/src/guard_store_aarch64.S" \
        -o "$dir/guard_store_aarch64.o"
    record "$CC" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -fuse-ld=lld -nostdlib -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-undefined -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libwestlake_thread_guard_registry.so \
        -Wl,--version-script="$REGISTRY/westlake_thread_guard_registry.map" \
        "$dir/thread_guard_registry.o" "$dir/guard_store_aarch64.o" \
        -o "$dir/libwestlake_thread_guard_registry.so"
}

build_pthread_bridge()
{
    local pass=$1
    local dir=$OUT/$pass/pthread-bridge
    record "$CC" "${COMMON[@]}" \
        -std=c11 -Wall -Wextra -Werror -pedantic \
        -ffreestanding -fno-stack-protector -fno-unwind-tables \
        -fno-asynchronous-unwind-tables -mno-outline-atomics \
        -I"$PTHREAD_BRIDGE/include" \
        -c "$PTHREAD_BRIDGE/src/bionic_pthread_bridge.c" \
        -o "$dir/bionic_pthread_bridge.o"
    record "$CC" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -fuse-ld=lld -nostdlib -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-undefined -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libwestlake_bionic_pthread_bridge.so \
        -Wl,--version-script="$PTHREAD_BRIDGE/westlake_bionic_pthread_bridge.map" \
        "$dir/bionic_pthread_bridge.o" \
        -o "$dir/libwestlake_bionic_pthread_bridge.so"
}

build_compat()
{
    local pass=$1
    local dir=$OUT/$pass/compat
    local objects=()
    local source_name
    for source_name in \
        system_properties.cpp \
        malloc_compat.cpp \
        fdsan_stubs.cpp \
        misc_compat.cpp \
        abort_message_compat.cpp \
        liblog_android_supplement.cpp \
        sync_builtins.c
    do
        local source=$COMPAT_SRC/$source_name
        local object=$dir/${source_name%.*}.o
        objects+=("$object")
        if [[ $source_name == *.c ]]; then
            record "$CC" "${COMMON[@]}" -std=c11 \
                -fvisibility=default \
                -D__ANDROID_API__=34 -DPAGE_SIZE=4096 \
                -I"$COMPAT_INC" -c "$source" -o "$object"
        else
            record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
                -fvisibility=default \
                -include "$COMPAT_INC/libcxx_compat.h" \
                -I"$COMPAT_INC" -DPARAM_VALUE_LEN_MAX=96 \
                -Wno-constant-conversion \
                -c "$source" -o "$object"
        fi
    done
    record "$CXX" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" \
        -fuse-ld=lld -shared -nostdlib++ \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-undefined -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libbionic_compat.so \
        -L"$PLUGIN/frozen/stock_host/libraries" -L"$TARGET_LIB" \
        -o "$dir/libbionic_compat.so" \
        "${objects[@]}" \
        -Wl,--no-as-needed -lbegetutil.z -lc++ \
        -Wl,--as-needed -lc -ldl -lpthread "$BUILTINS"
}

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

build_native_loader()
{
    local pass=$1
    local dir=$OUT/$pass/native-loader
    local objects=()
    local source
    local object
    for source in native_loader.cpp native_loader_registry.cpp system_loader.cpp; do
        object=$dir/${source%.cpp}.o
        record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
            -fno-exceptions -fno-rtti \
            -include "$BASE_GEN/sources/bionic_compat/include/libcxx_compat.h" \
            -I"$NATIVE_LOADER/include" -I"$NATIVE_LOADER/src" \
            -I"$APP_LOADER/include" -I"$PTHREAD_BRIDGE/include" \
            -I"$BASE_GEN/includes/aosp/libnativehelper/include_jni" \
            -c "$NATIVE_LOADER/src/$source" -o "$object"
        objects+=("$object")
    done
    record "$CXX" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" \
        -fuse-ld=lld -shared -nostdlib++ \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-allow-shlib-undefined -Wl,--no-undefined \
        -Wl,--fatal-warnings -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libnativeloader.so \
        -Wl,--version-script="$NATIVE_LOADER/native_loader.map" \
        -L"$OUT/$pass/app-loader" -L"$FROZEN/libraries/oh" -L"$TARGET_LIB" \
        -o "$dir/libnativeloader.so" \
        "${objects[@]}" -Wl,--no-as-needed -lapp_native_loader \
        -Wl,--as-needed -lc++ -lc -ldl -lpthread "$BUILTINS"
}

build_art_palette()
{
    local pass=$1
    local dir=$OUT/$pass/palette
    record "$CC" "${COMMON[@]}" \
        -std=c11 -Wall -Wextra -Werror -fvisibility=default \
        -c "$ART_PALETTE/src/palette_oh.c" \
        -o "$dir/palette_oh.o"
    record "$CC" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" \
        -fuse-ld=lld -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-undefined -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libartpalette-system.so \
        -Wl,--version-script="$ART_PALETTE/art_palette_oh.map" \
        -L"$V12" -L"$TARGET_LIB" \
        "$dir/palette_oh.o" \
        -Wl,--no-as-needed -llog -lc \
        -o "$dir/libartpalette-system.so"
}

build_route_a_zlib()
{
    local pass=$1
    local dir=$OUT/$pass/zlib
    local source
    local object
    local objects=()
    local sources=(
        adler32.c
        compress.c
        contrib/minizip/ioapi.c
        contrib/minizip/unzip.c
        contrib/minizip/zip.c
        crc32.c
        deflate.c
        gzclose.c
        gzlib.c
        gzread.c
        gzwrite.c
        infback.c
        inffast.c
        inflate.c
        inftrees.c
        trees.c
        uncompr.c
        zutil.c
    )
    for source in "${sources[@]}"; do
        object=$dir/${source//\//_}.o
        record "$CC" "${COMMON[@]}" -std=gnu11 \
            -fvisibility=default -mbranch-protection=pac-ret \
            -I"$OH_ZLIB" -I"$OH_ZLIB/contrib/minizip" \
            -c "$OH_ZLIB/$source" -o "$object"
        objects+=("$object")
    done
    record "$CC" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" \
        -fuse-ld=lld -nostdlib -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-undefined -Wl,--fatal-warnings \
        -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libshared_libz.z.so \
        -L"$TARGET_LIB" \
        "${objects[@]}" -Wl,--no-as-needed -lc "$BUILTINS" \
        -o "$dir/libshared_libz.z.so"
}

verify_route_a_zlib_abi()
{
    local rebuilt=$1
    local reference=$V12_DEPS/libshared_libz.z.so
    local prefix=$2
    "$READELF" -dW "$reference" |
        awk '/\(NEEDED\)|\(SONAME\)/ {tag=$2; value=$NF; print tag, value}' |
        sort -u >"$OUT/logs/$prefix.reference.dynamic.txt"
    "$READELF" -dW "$rebuilt" |
        awk '/\(NEEDED\)|\(SONAME\)/ {tag=$2; value=$NF; print tag, value}' |
        sort -u >"$OUT/logs/$prefix.rebuilt.dynamic.txt"
    cmp "$OUT/logs/$prefix.reference.dynamic.txt" \
        "$OUT/logs/$prefix.rebuilt.dynamic.txt"
    "$READELF" -Ws "$reference" |
        awk '$7 != "UND" && $5 == "GLOBAL" && $8 !~ /^(|_init|_fini)$/ {sub(/@.*/, "", $8); print $8}' |
        sort -u >"$OUT/logs/$prefix.reference.exports.txt"
    "$READELF" -Ws "$rebuilt" |
        awk '$7 != "UND" && $5 == "GLOBAL" && $8 !~ /^(|_init|_fini)$/ {sub(/@.*/, "", $8); print $8}' |
        sort -u >"$OUT/logs/$prefix.rebuilt.exports.txt"
    cmp "$OUT/logs/$prefix.reference.exports.txt" \
        "$OUT/logs/$prefix.rebuilt.exports.txt"
    "$READELF" -nW "$rebuilt" |
        awk '/Build ID:/ {print $3; exit}' |
        grep -Eq '^[0-9a-f]{40}$'
}

build_registry pass1
build_registry pass2
cmp "$OUT/pass1/registry/libwestlake_thread_guard_registry.so" \
    "$OUT/pass2/registry/libwestlake_thread_guard_registry.so"
cp "$OUT/pass1/registry/libwestlake_thread_guard_registry.so" \
   "$OUT/libwestlake_thread_guard_registry.so"

build_pthread_bridge pass1
build_pthread_bridge pass2
cmp "$OUT/pass1/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
    "$OUT/pass2/pthread-bridge/libwestlake_bionic_pthread_bridge.so"
cp "$OUT/pass1/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
   "$OUT/libwestlake_bionic_pthread_bridge.so"

build_compat pass1
build_compat pass2
cmp "$OUT/pass1/compat/libbionic_compat.so" \
    "$OUT/pass2/compat/libbionic_compat.so"
cp "$OUT/pass1/compat/libbionic_compat.so" "$OUT/libbionic_compat.so"

build_app_loader pass1
build_app_loader pass2
cmp "$OUT/pass1/app-loader/libapp_native_loader.so" \
    "$OUT/pass2/app-loader/libapp_native_loader.so"
cp "$OUT/pass1/app-loader/libapp_native_loader.so" \
   "$OUT/libapp_native_loader.so"

build_native_loader pass1
build_native_loader pass2
cmp "$OUT/pass1/native-loader/libnativeloader.so" \
    "$OUT/pass2/native-loader/libnativeloader.so"
cp "$OUT/pass1/native-loader/libnativeloader.so" \
   "$OUT/libnativeloader.so"

build_art_palette pass1
build_art_palette pass2
cmp "$OUT/pass1/palette/libartpalette-system.so" \
    "$OUT/pass2/palette/libartpalette-system.so"
cp "$OUT/pass1/palette/libartpalette-system.so" \
   "$OUT/libartpalette-system.so"

build_route_a_zlib pass1
build_route_a_zlib pass2
cmp "$OUT/pass1/zlib/libshared_libz.z.so" \
    "$OUT/pass2/zlib/libshared_libz.z.so"
verify_route_a_zlib_abi "$OUT/pass1/zlib/libshared_libz.z.so" zlib
cp "$OUT/pass1/zlib/libshared_libz.z.so" \
   "$OUT/libshared_libz.z.so"
sha256sum \
    "$OH_ZLIB/BUILD.gn" \
    "$OH_ZLIB"/*.c "$OH_ZLIB"/*.h \
    "$OH_ZLIB/contrib/minizip"/*.c \
    "$OH_ZLIB/contrib/minizip"/*.h \
    >"$OUT/logs/zlib-source.sha256"

rm -rf "$OUT/providers"
mkdir -p "$OUT/providers"
cp "$V12"/*.so "$OUT/providers/"
# B6: seal the rebuilt musl bridge without mutating the certified v12 base.
cp "$ROOT/adapter/out/aosp_lib_arm64/libsigchain.so" "$OUT/providers/"
cp "$OUT/libnativeloader.so" "$OUT/providers/"
cp "$OUT/libshared_libz.z.so" "$OUT/providers/"
cp "$OUT/libbionic_compat.so" "$OUT/providers/"
cp "$OUT/libwestlake_thread_guard_registry.so" "$OUT/providers/"
cp "$OUT/libwestlake_bionic_pthread_bridge.so" "$OUT/providers/"
cp "$OUT/libapp_native_loader.so" "$OUT/providers/"
cp "$OUT/libartpalette-system.so" "$OUT/providers/"
FINAL_PROVIDER_COUNT=$(find "$OUT/providers" -maxdepth 1 -type f -name '*.so' | wc -l | tr -d ' ')
EXPECTED_FINAL_PROVIDER_COUNT=$((BASE_PROVIDER_COUNT + 3))
[[ "$FINAL_PROVIDER_COUNT" == "$EXPECTED_FINAL_PROVIDER_COUNT" ]] || {
    echo "ERROR expected exact Route-A provider set size $EXPECTED_FINAL_PROVIDER_COUNT, found $FINAL_PROVIDER_COUNT" >&2
    exit 1
}
[[ ! -e "$OUT/providers/libart_runtime_stubs.so" ]] || {
    echo "ERROR stale broad runtime stub survived provider-set rebuild" >&2
    exit 1
}
(
    cd "$OUT/providers"
    sha256sum ./*.so
) >"$OUT/providers.sha256"
[[ "$(wc -l <"$OUT/providers.sha256" | tr -d ' ')" == "$EXPECTED_FINAL_PROVIDER_COUNT" ]] || {
    echo "ERROR provider identity manifest member count drift" >&2
    exit 1
}

build_provider()
{
    local pass=$1
    local dir=$OUT/$pass/provider
    record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -include "$BASE_GEN/sources/bionic_compat/include/libcxx_compat.h" \
        "${INCLUDES[@]}" \
        -c "$ADAPTER/src/appspawnx_runtime.cpp" \
        -o "$dir/appspawnx_runtime.o"
    record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -include "$BASE_GEN/sources/bionic_compat/include/libcxx_compat.h" \
        "${INCLUDES[@]}" \
        -c "$JNI_ATTACH/src/jni_attach_admission.cpp" \
        -o "$dir/jni_attach_admission.o"
    record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -include "$BASE_GEN/sources/bionic_compat/include/libcxx_compat.h" \
        "${INCLUDES[@]}" \
        -c "$ADAPTER/src/child_main_after_stock.cpp" \
        -o "$dir/child_main_after_stock.o"
    record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -include "$BASE_GEN/sources/bionic_compat/include/libcxx_compat.h" \
        "${INCLUDES[@]}" \
        "-DWLAR_ADAPTER_BRIDGE_PATH=\"$WLAR_ADAPTER_BRIDGE_PATH\"" \
        "-DWLAR_ADAPTER_BRIDGE_SHA256_HEX=\"$WLAR_ADAPTER_BRIDGE_SHA256_HEX\"" \
        "-DWLAR_ADAPTER_BRIDGE_BUILD_ID_HEX=\"$WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX\"" \
        "-DWLAR_ANDROID_RUNTIME_PATH=\"$WLAR_ANDROID_RUNTIME_PATH\"" \
        "-DWLAR_ANDROID_RUNTIME_SHA256_HEX=\"$WLAR_ANDROID_RUNTIME_SHA256_HEX\"" \
        "-DWLAR_ANDROID_RUNTIME_BUILD_ID_HEX=\"$WLAR_ANDROID_RUNTIME_BUILD_ID_HEX\"" \
        -c "$ADAPTER/src/adapter_bridge_identity.cpp" \
        -o "$dir/adapter_bridge_identity.o"
    record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -include "$BASE_GEN/sources/bionic_compat/include/libcxx_compat.h" \
        "${INCLUDES[@]}" \
        "-DWLAR_GENERATION_SHA_HEX=\"$GENERATION_SHA\"" \
        -c "$PLUGIN/src/westlake_android_runtime_provider.cpp" \
        -o "$dir/westlake_android_runtime_provider.o"
    for provider_c_source in \
        host_runtime_services \
        runtime_loader_phase \
        westlake_elf_identity \
        westlake_sha256
    do
        record "$CC" "${COMMON[@]}" -std=c11 \
            "${INCLUDES[@]}" \
            -c "$PLUGIN/src/$provider_c_source.c" \
            -o "$dir/$provider_c_source.o"
    done
    record "$CXX" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -B"$TARGET_LIB" \
        -fuse-ld=lld \
        -shared \
        -nostdlib++ \
        -Wl,-z,defs \
        -Wl,--no-allow-shlib-undefined \
        -Wl,--no-undefined \
        -Wl,-z,now \
        -Wl,-z,relro \
        -Wl,--gc-sections \
        -Wl,--build-id=sha1 \
        -Wl,--hash-style=both \
        -Wl,--fatal-warnings \
        -Wl,-soname,libwestlake_android_runtime_provider.so \
        -Wl,--version-script="$PLUGIN/westlake_android_runtime_provider.map" \
        -L"$OUT/$pass/compat" \
        -L"$OUT/$pass/app-loader" \
        -L"$OUT/$pass/native-loader" \
        -L"$OUT/$pass/registry" \
        -L"$V12" \
        -L"$V12_DEPS" \
        -L"$FROZEN/libraries/oh" \
        -L"$TARGET_LIB" \
        -o "$dir/libwestlake_android_runtime_provider.so" \
        "$dir/appspawnx_runtime.o" \
        "$dir/jni_attach_admission.o" \
        "$dir/child_main_after_stock.o" \
        "$dir/adapter_bridge_identity.o" \
        "$dir/westlake_android_runtime_provider.o" \
        "$dir/host_runtime_services.o" \
        "$dir/runtime_loader_phase.o" \
        "$dir/westlake_elf_identity.o" \
        "$dir/westlake_sha256.o" \
        -Wl,--no-as-needed \
        -lapp_native_loader \
        -lwestlake_thread_guard_registry \
        -lhilog -lnativehelper -llog -lbionic_compat -lart -lnativeloader -lc++ \
        -Wl,--as-needed -lc -ldl -lpthread "$BUILTINS"
}

build_provider pass1
build_provider pass2
cmp "$OUT/pass1/provider/libwestlake_android_runtime_provider.so" \
    "$OUT/pass2/provider/libwestlake_android_runtime_provider.so"
cp "$OUT/pass1/provider/libwestlake_android_runtime_provider.so" \
   "$OUT/libwestlake_android_runtime_provider.so"

# Build the inert child plugin only after the sealed provider closure exists.
# The plugin links the child-only loader implementation, never the provider;
# the final ELF gate proves both parent and plugin lack the old implicit edge.
"$PLUGIN/build_target_in_container.sh"
for generated_input in \
    "$PLUGIN/out/target/pass1/generated_generation_metadata.c" \
    "$PLUGIN/out/target/pass1/generated_generation_metadata.o" \
    "$PLUGIN/out/target/pass2/generated_generation_metadata.c" \
    "$PLUGIN/out/target/pass2/generated_generation_metadata.o"
do
    [[ -s "$generated_input" ]] || {
        echo "ERROR target child plugin omitted generated generation metadata: $generated_input" >&2
        exit 1
    }
done
PLUGIN_ELF=$PLUGIN/out/target/libwestlake_android_child.z.so
PLUGIN_SHA256=$(sha256sum "$PLUGIN_ELF" | awk '{print $1}')
ACTUAL_PLUGIN_BUILD_ID=$(
    "$READELF" -nW "$PLUGIN_ELF" |
        awk '/Build ID:/ {print $3; exit}'
)
[[ $PLUGIN_SHA256 =~ ^[0-9a-f]{64}$ ]] || {
    echo "ERROR invalid child plugin SHA-256" >&2
    exit 1
}
[[ $ACTUAL_PLUGIN_BUILD_ID == "$PLUGIN_BUILD_ID_HEX" ]] || {
    echo "ERROR child plugin Build-ID is not bound to Route-A inputs" >&2
    exit 1
}

HOST_INCLUDES=(
    -I"$PLUGIN/include"
    -I"$APP_LOADER/include"
    -I"$OH/base/startup/appspawn/common"
    -I"$OH/base/startup/appspawn/standard"
    -I"$OH/base/startup/appspawn/modules/common"
    -I"$OH/base/startup/appspawn/modules/modulemgr"
    -I"$OH/base/startup/appspawn/modules/module_engine/include"
    -I"$OH/base/startup/appspawn/modules/sysevent"
    -I"$OH/base/startup/appspawn/util/include"
    -I"$OH/base/startup/appspawn/interfaces/innerkits/include"
    -I"$OH/base/startup/init/interfaces/innerkits/include"
    -I"$OH/aux/base/startup/init/interfaces/innerkits/include/syspara"
    -I"$OH/base/startup/init/interfaces/innerkits/include/syspara"
    -I"$OH/interface/sdk_c/hiviewdfx/hilog/include"
    -I"$OH/third_party/bounds_checking_function/include"
    -I"$OH/third_party/cJSON"
    -I"$OH/aux/base/customization/config_policy/interfaces/inner_api/include"
    -I"$OH/aux/foundation/resourceschedule/ffrt/interfaces/inner_api"
    -I"$OH/aux/foundation/resourceschedule/ffrt/interfaces/kits"
    -I"$OH/aux/base/hiviewdfx/hitrace/interfaces/native/innerkits/include/hitrace_meter"
    -I"$ADAPTER/src"
    -I"$BASE_GEN/sources/bionic_compat/include"
    -I"$REGISTRY/include"
    -I"$PTHREAD_BRIDGE/include"
    -I"$PUBLISHER/include"
)

HOST_DEFINES=(
    -D__MUSL__
    -DSUPPORT_64BIT
    -DWITH_SELINUX
)

python3 "$PLUGIN/generate_appspawn_manager_abi_overlay.py" \
    --current "$OH/base/startup/appspawn/standard/appspawn_manager.h" \
    --target "$TARGET_COHORT_HEADER" \
    --output "$COHORT_OVERLAY" \
    --report "$OUT/logs/manager-abi-overlay.json"

compile_host_c()
{
    local source=$1
    local output=$2
    shift 2
    record "$CC" "${COMMON[@]}" -std=gnu11 \
        -fvisibility=default \
        "${HOST_DEFINES[@]}" "${HOST_INCLUDES[@]}" "$@" \
        -c "$source" -o "$output"
}

compile_host_cxx()
{
    local source=$1
    local output=$2
    shift 2
    record "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -fvisibility=default \
        -include "$BASE_GEN/sources/bionic_compat/include/libcxx_compat.h" \
        "${HOST_DEFINES[@]}" "${HOST_INCLUDES[@]}" "$@" \
        -c "$source" -o "$output"
}

build_stock_host()
{
    local pass=$1
    local dir=$OUT/$pass/host
    mkdir -p "$dir"
    compile_host_c "$PLUGIN/src/westlake_stock_host_main.c" \
        "$dir/westlake_stock_host_main.o" \
        "-DWLASC_PLUGIN_GENERATION_SHA_HEX=\"$GENERATION_SHA\"" \
        "-DWLASC_PLUGIN_BUILD_ID_HEX=\"$PLUGIN_BUILD_ID_HEX\"" \
        "-DWLASC_PLUGIN_ELF_SHA256_HEX=\"$PLUGIN_SHA256\"" \
        "-DWLAR_GENERATION_SHA_HEX=\"$GENERATION_SHA\""
    compile_host_c "$OH/base/startup/appspawn/common/appspawn_server.c" \
        "$dir/appspawn_server.o"
    compile_host_cxx "$OH/base/startup/appspawn/common/appspawn_trace.cpp" \
        "$dir/appspawn_trace.o" -DOHOS_LITE
    compile_host_cxx "$OH/base/startup/appspawn/modules/common/appspawn_dfx_dump.cpp" \
        "$dir/appspawn_dfx_dump.o" -DAPPSPAWN_TEST
    compile_host_c "$OH/base/startup/appspawn/modules/modulemgr/appspawn_modulemgr.c" \
        "$dir/appspawn_modulemgr.o" -include "$COHORT_OVERLAY" \
        -MMD -MF "$dir/appspawn_modulemgr.d"
    compile_host_c "$OH/base/startup/appspawn/standard/appspawn_appmgr.c" \
        "$dir/appspawn_appmgr.o" -include "$COHORT_OVERLAY" \
        -MMD -MF "$dir/appspawn_appmgr.d"
    compile_host_c "$OH/base/startup/appspawn/standard/appspawn_kickdog.c" \
        "$dir/appspawn_kickdog.o" -include "$COHORT_OVERLAY" \
        -MMD -MF "$dir/appspawn_kickdog.d"
    compile_host_c "$OH/base/startup/appspawn/standard/appspawn_msgmgr.c" \
        "$dir/appspawn_msgmgr.o" -include "$COHORT_OVERLAY" \
        -MMD -MF "$dir/appspawn_msgmgr.d"
    compile_host_c "$PLUGIN/stock_host_patched/base/startup/appspawn/standard/appspawn_service.c" \
        "$dir/appspawn_service.o" -include "$COHORT_OVERLAY" \
        -MMD -MF "$dir/appspawn_service.d"
    compile_host_c "$OH/base/startup/appspawn/util/src/appspawn_utils.c" \
        "$dir/appspawn_utils.o"
    compile_host_cxx "$OH/base/startup/appspawn/util/src/appspawndf_utils.cpp" \
        "$dir/appspawndf_utils.o"
    compile_host_cxx "$ADAPTER/src/native_compat_prepare.cpp" \
        "$dir/native_compat_prepare.o" -fno-stack-protector
    compile_host_cxx "$ADAPTER/tls_prefix/bionic_tls_prefix_reservation.cpp" \
        "$dir/bionic_tls_prefix_reservation.o"
    compile_host_c "$PUBLISHER/src/thread_template_publisher.c" \
        "$dir/thread_template_publisher.o"
    compile_host_c "$PLUGIN/src/westlake_elf_identity.c" \
        "$dir/host_westlake_elf_identity.o"
    compile_host_c "$PLUGIN/src/westlake_sha256.c" \
        "$dir/host_westlake_sha256.o"
    record "$CC" "${COMMON[@]}" \
        -c "$ADAPTER/src/native_compat_prepare_owner_aarch64.S" \
        -o "$dir/native_compat_prepare_owner_aarch64.o"

    record "$CXX" \
        "--target=$TARGET" \
        "--sysroot=$SYSROOT" \
        -B"$TOOLCHAIN/bin" \
        -B"$TARGET_LIB" \
        -fuse-ld=lld \
        -pie \
        -nostdlib++ \
        -Wl,-z,defs \
        -Wl,--no-allow-shlib-undefined \
        -Wl,-z,now \
        -Wl,-z,relro \
        -Wl,--build-id=sha1 \
        -Wl,--hash-style=both \
        -Wl,--fatal-warnings \
        -Wl,--export-dynamic \
        -Wl,--dynamic-linker=/lib/ld-musl-aarch64.so.1 \
        -Wl,-soname,appspawn-x \
        -Wl,--version-script="$PLUGIN/westlake_stock_host.map" \
        -L"$OUT/$pass/provider" \
        -L"$OUT/$pass/registry" \
        -L"$OUT/$pass/compat" \
        -L"$OUT/$pass/app-loader" \
        -L"$PLUGIN/frozen/stock_host/libraries" \
        -L"$V12" \
        -L"$V12_DEPS" \
        -L"$FROZEN/libraries/oh" \
        -L"$TARGET_LIB" \
        -o "$dir/appspawn-x-stock" \
        "$dir/westlake_stock_host_main.o" \
        "$dir/appspawn_server.o" \
        "$dir/appspawn_trace.o" \
        "$dir/appspawn_dfx_dump.o" \
        "$dir/appspawn_modulemgr.o" \
        "$dir/appspawn_appmgr.o" \
        "$dir/appspawn_kickdog.o" \
        "$dir/appspawn_msgmgr.o" \
        "$dir/appspawn_service.o" \
        "$dir/appspawn_utils.o" \
        "$dir/appspawndf_utils.o" \
        "$dir/native_compat_prepare.o" \
        "$dir/native_compat_prepare_owner_aarch64.o" \
        "$dir/bionic_tls_prefix_reservation.o" \
        "$dir/thread_template_publisher.o" \
        "$dir/host_westlake_elf_identity.o" \
        "$dir/host_westlake_sha256.o" \
        -Wl,--no-as-needed \
        -lwestlake_thread_guard_registry \
        -lffrt -lcjson.z -lutils.z -lconfigpolicy_util.z \
        -lbegetutil.z -lsec_shared.z -lhilog \
        -lselinux.z -lhap_restorecon.z -lc++ \
        -Wl,--as-needed -lc -ldl -lpthread "$BUILTINS"
}

build_stock_host pass1
build_stock_host pass2
cmp "$OUT/pass1/host/appspawn-x-stock" "$OUT/pass2/host/appspawn-x-stock"
python3 "$PLUGIN/verify_appspawn_host_abi.py" \
    --host "$OUT/pass1/host/appspawn-x-stock" \
    --current-header "$OH/base/startup/appspawn/standard/appspawn_manager.h" \
    --target-header "$TARGET_COHORT_HEADER" \
    --overlay-header "$COHORT_OVERLAY" \
    --dependency-dir "$OUT/pass1/host" \
    --stock-common "$STOCK_COMMON" \
    --dwarfdump "$TOOLCHAIN/bin/llvm-dwarfdump" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/logs/host-abi-pass1.json"
python3 "$PLUGIN/verify_appspawn_host_abi.py" \
    --host "$OUT/pass2/host/appspawn-x-stock" \
    --current-header "$OH/base/startup/appspawn/standard/appspawn_manager.h" \
    --target-header "$TARGET_COHORT_HEADER" \
    --overlay-header "$COHORT_OVERLAY" \
    --dependency-dir "$OUT/pass2/host" \
    --stock-common "$STOCK_COMMON" \
    --dwarfdump "$TOOLCHAIN/bin/llvm-dwarfdump" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/logs/host-abi-pass2.json"
cmp "$OUT/logs/host-abi-pass1.json" "$OUT/logs/host-abi-pass2.json"
cp "$OUT/pass1/host/appspawn-x-stock" "$OUT/appspawn-x-stock"

"$READELF" -nW "$OUT/libwestlake_android_runtime_provider.so" \
    >"$OUT/logs/provider.notes.txt"
"$READELF" -dW "$OUT/libwestlake_android_runtime_provider.so" \
    >"$OUT/logs/provider.dynamic.txt"
"$READELF" -Ws "$OUT/libwestlake_android_runtime_provider.so" \
    >"$OUT/logs/provider.symbols.txt"
"$OBJDUMP" -dr "$OUT/libwestlake_android_runtime_provider.so" \
    >"$OUT/logs/provider.disassembly.txt"

"$READELF" -nW "$OUT/appspawn-x-stock" >"$OUT/logs/host.notes.txt"
"$READELF" -dW "$OUT/appspawn-x-stock" >"$OUT/logs/host.dynamic.txt"
"$READELF" -Ws "$OUT/appspawn-x-stock" >"$OUT/logs/host.symbols.txt"
"$READELF" -lW "$OUT/appspawn-x-stock" >"$OUT/logs/host.segments.txt"
"$OBJDUMP" -dr "$OUT/appspawn-x-stock" >"$OUT/logs/host.disassembly.txt"

python3 "$PLUGIN/verify_route_a_generation.py" \
    --host "$OUT/pass1/host/appspawn-x-stock" \
    --second-host "$OUT/pass2/host/appspawn-x-stock" \
    --provider "$OUT/pass1/provider/libwestlake_android_runtime_provider.so" \
    --second-provider "$OUT/pass2/provider/libwestlake_android_runtime_provider.so" \
    --registry "$OUT/pass1/registry/libwestlake_thread_guard_registry.so" \
    --second-registry "$OUT/pass2/registry/libwestlake_thread_guard_registry.so" \
    --pthread-bridge "$OUT/pass1/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
    --second-pthread-bridge "$OUT/pass2/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
    --compat "$OUT/pass1/compat/libbionic_compat.so" \
    --second-compat "$OUT/pass2/compat/libbionic_compat.so" \
    --app-native-loader "$OUT/pass1/app-loader/libapp_native_loader.so" \
    --second-app-native-loader "$OUT/pass2/app-loader/libapp_native_loader.so" \
    --native-loader "$OUT/pass1/native-loader/libnativeloader.so" \
    --second-native-loader "$OUT/pass2/native-loader/libnativeloader.so" \
    --art-palette "$OUT/pass1/palette/libartpalette-system.so" \
    --second-art-palette "$OUT/pass2/palette/libartpalette-system.so" \
    --provider-set-manifest "$OUT/providers.sha256" \
    --plugin "$PLUGIN/out/target/pass1/libwestlake_android_child.z.so" \
    --second-plugin "$PLUGIN/out/target/pass2/libwestlake_android_child.z.so" \
    --inputs "$PLUGIN/ROUTE_A_INPUTS.json" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/verification.json"

python3 "$REGISTRY/tests/verify_route_a_product_integration.py" \
    --project-root "$ROOT" \
    --host "$OUT/pass1/host/appspawn-x-stock" \
    --second-host "$OUT/pass2/host/appspawn-x-stock" \
    --provider "$OUT/pass1/provider/libwestlake_android_runtime_provider.so" \
    --second-provider "$OUT/pass2/provider/libwestlake_android_runtime_provider.so" \
    --plugin "$PLUGIN/out/target/pass1/libwestlake_android_child.z.so" \
    --second-plugin "$PLUGIN/out/target/pass2/libwestlake_android_child.z.so" \
    --registry "$OUT/pass1/registry/libwestlake_thread_guard_registry.so" \
    --second-registry "$OUT/pass2/registry/libwestlake_thread_guard_registry.so" \
    --pthread-bridge "$OUT/pass1/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
    --second-pthread-bridge "$OUT/pass2/pthread-bridge/libwestlake_bionic_pthread_bridge.so" \
    --compat "$OUT/pass1/compat/libbionic_compat.so" \
    --second-compat "$OUT/pass2/compat/libbionic_compat.so" \
    --app-native-loader "$OUT/pass1/app-loader/libapp_native_loader.so" \
    --second-app-native-loader "$OUT/pass2/app-loader/libapp_native_loader.so" \
    --native-loader "$OUT/pass1/native-loader/libnativeloader.so" \
    --second-native-loader "$OUT/pass2/native-loader/libnativeloader.so" \
    --art-palette "$OUT/pass1/palette/libartpalette-system.so" \
    --second-art-palette "$OUT/pass2/palette/libartpalette-system.so" \
    --provider-set-manifest "$OUT/providers.sha256" \
    --owner-object "$OUT/pass1/host/native_compat_prepare_owner_aarch64.o" \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --report "$OUT/guard-product-verification.json"

sha256sum \
    "$OUT/appspawn-x-stock" \
    "$OUT/libwestlake_android_runtime_provider.so" \
    "$OUT/libwestlake_thread_guard_registry.so" \
    "$OUT/libwestlake_bionic_pthread_bridge.so" \
    "$OUT/libbionic_compat.so" \
    "$OUT/libapp_native_loader.so" \
    "$OUT/libnativeloader.so" \
    "$OUT/libartpalette-system.so" \
    "$OUT/providers.sha256" \
    "$PLUGIN/out/target/libwestlake_android_child.z.so" \
    "$OUT/verification.json" \
    "$OUT/guard-product-verification.json" >"$OUT/artifacts.sha256"

echo "PASS Route A provider + stock host deterministic=2"
