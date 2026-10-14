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
V12=$FROZEN/provider-v12/providers
V12_DEPS=$FROZEN/provider-v12/dependencies
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

GENERATION_SHA=74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d
PLUGIN_BUILD_ID_HEX=${GENERATION_SHA:0:40}
PLUGIN_SHA256=$(sha256sum "$PLUGIN/out/target/pass1/libwestlake_android_child.z.so" | cut -d " " -f1)
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

CXX_STD=(
    -nostdinc++
    -isystem "$TOOLCHAIN/include/c++/v1"
    -std=gnu++17
)
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
