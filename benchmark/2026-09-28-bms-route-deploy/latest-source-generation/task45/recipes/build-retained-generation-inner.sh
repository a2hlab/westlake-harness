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
LEDGER_DIR=${WESTLAKE_ROUTE_A_LEDGER_DIR:-$PLUGIN}
ROUTE_A_INPUTS=$LEDGER_DIR/ROUTE_A_INPUTS.json
SOURCE_CLOSURE=$LEDGER_DIR/SOURCE_CLOSURE.json
REGISTRY=$ROOT/adapter/framework/native-compat/thread-guard-registry
JNI_ATTACH=$ROOT/adapter/framework/native-compat/jni-attach-admission
PTHREAD_BRIDGE=$ROOT/adapter/framework/native-compat/bionic-pthread-bridge
PUBLISHER=$ROOT/adapter/framework/native-compat/thread-template-publisher
MEDIANDK_PRESENCE=$ROOT/adapter/framework/native-compat/mediandk-presence
COMPAT_SRC=$ADAPTER/bionic_compat/src
COMPAT_INC=$ADAPTER/bionic_compat/include
COMPAT_MAP=$ADAPTER/bionic_compat/bionic_compat.map
APP_LOADER=$ROOT/adapter/framework/app-native-loader
NATIVE_LOADER=$ROOT/adapter/framework/native-loader-oh
ART_PALETTE=$ROOT/adapter/framework/art-palette-oh
OH=$ROOT/adapter/frozen/references/oh-appspawn-security-v7
CANONICAL_OH_ROOT=${WESTLAKE_ROUTE_A_CANONICAL_OH_ROOT:-$ROOT/upstream/openharmony-6.1.0.31}
OH_PRODUCT_LIBEGL=$CANONICAL_OH_ROOT/out/wukong100/graphic/graphic_2d/libEGL.so
TARGET_COHORT_HEADER=$CANONICAL_OH_ROOT/base/startup/appspawn/standard/appspawn_manager.h
COHORT_OVERLAY_DIR=${WESTLAKE_ROUTE_A_COHORT_OVERLAY_DIR:-$PLUGIN/out/abi-cohort/OpenHarmony-6.1.0.31/standard}
COHORT_OVERLAY=$COHORT_OVERLAY_DIR/appspawn_manager.h
STOCK_COMMON=$PLUGIN/frozen/stock_host/abi/libappspawn_common.z.so
BASE_GENERATION_ROOT=${WESTLAKE_GENERATION_ROOT:-$ROOT/.work/product-tls-generation}
BASE_GEN=$BASE_GENERATION_ROOT/frozen
# This source project is declared by the current frozen D600 generation.
OH_ZLIB=$BASE_GEN/sources/oh/zlib
FROZEN=$PLUGIN/frozen/runtime_provider
R45_DYNAMIC_ROOTS=$ROOT/adapter/frozen/r45-dynamic-roots
BASE_PROVIDER_ROOT=${WESTLAKE_ROUTE_A_BASE_PROVIDER_ROOT:-$FROZEN/provider-v12}
V12=$BASE_PROVIDER_ROOT/providers
V12_DEPS=${WESTLAKE_ROUTE_A_BASE_PROVIDER_DEPENDENCIES:-$FROZEN/provider-v12/dependencies}
OUT=${WESTLAKE_ROUTE_A_OUTPUT_ROOT:-$PLUGIN/out/route-a-generation}
TARGET_OUT=${WESTLAKE_ROUTE_A_TARGET_OUTPUT_ROOT:-$PLUGIN/out/target}
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

mkdir -p \
    "$OUT/pass1/provider" "$OUT/pass2/provider" \
    "$OUT/pass1/compat" "$OUT/pass2/compat" \
    "$OUT/pass1/registry" "$OUT/pass2/registry" \
    "$OUT/pass1/pthread-bridge" "$OUT/pass2/pthread-bridge" \
    "$OUT/pass1/app-loader" "$OUT/pass2/app-loader" \
    "$OUT/pass1/native-loader" "$OUT/pass2/native-loader" \
    "$OUT/pass1/palette" "$OUT/pass2/palette" \
    "$OUT/pass1/zlib" "$OUT/pass2/zlib" \
    "$OUT/pass1/mediandk" "$OUT/pass2/mediandk" \
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

GENERATION_SHA=$(sha256sum "$ROUTE_A_INPUTS" | awk '{print $1}')
[[ $GENERATION_SHA =~ ^[0-9a-f]{64}$ ]] || {
    echo "ERROR invalid provider generation identity" >&2
    exit 1
}

PLUGIN_BUILD_ID_HEX=${GENERATION_SHA:0:40}
[[ $PLUGIN_BUILD_ID_HEX =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR invalid deterministic plugin Build-ID" >&2
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
        -lhilog -lnativehelper -llog -lbionic_compat -lart -lbase -lnativeloader -lc++ \
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
    "$TARGET_OUT/pass1/generated_generation_metadata.c" \
    "$TARGET_OUT/pass1/generated_generation_metadata.o" \
    "$TARGET_OUT/pass2/generated_generation_metadata.c" \
    "$TARGET_OUT/pass2/generated_generation_metadata.o"
do
    [[ -s "$generated_input" ]] || {
        echo "ERROR target child plugin omitted generated generation metadata: $generated_input" >&2
        exit 1
    }
done
PLUGIN_ELF=$TARGET_OUT/libwestlake_android_child.z.so
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
        -include "$ROOT/adapter/framework/app-native-loader/include/oh_dlns_abi.h" \
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
    compile_host_c "$PLUGIN/src/bionic_stdio_broker.c" \
        "$dir/bionic_stdio_broker.o" -fno-builtin
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
        "$dir/bionic_stdio_broker.o" \
        "$FROZEN/libraries/oh/libhilog.so" \
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


echo PASS retained-provider real-work host strict link and ABI
