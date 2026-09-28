#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1

FROZEN_TEST=${FROZEN_TEST:?set FROZEN_TEST to the frozen-test directory}
OUT=${OUT:?set OUT to an output directory}
BRIDGE_SHA=${BRIDGE_SHA:?set BRIDGE_SHA}
RUNTIME_SHA=${RUNTIME_SHA:?set RUNTIME_SHA}
BRIDGE_BUILD_ID=${BRIDGE_BUILD_ID:-0000000000000000000000000000000000000000}
RUNTIME_BUILD_ID=${RUNTIME_BUILD_ID:-0000000000000000000000000000000000000000}
BRIDGE_PATH=${BRIDGE_PATH:-/system/android/lib64/liboh_adapter_bridge.so}
RUNTIME_PATH=${RUNTIME_PATH:-/system/android/lib64/liboh_android_runtime.so}

TOOLCHAIN=$FROZEN_TEST/toolchain
SYSROOT=$FROZEN_TEST/sysroot
TARGET=aarch64-linux-ohos
TARGET_LIB=$SYSROOT/lib/$TARGET
CXX=$TOOLCHAIN/bin/clang-15
CC=$TOOLCHAIN/bin/clang-15
STRIP=$TOOLCHAIN/bin/llvm-strip
BUILTINS=$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a
INPUTS=$FROZEN_TEST
WORK=$OUT/work
ARTIFACTS=$OUT/artifacts

mkdir -p "$WORK/obj/compat" "$WORK/obj/wrapper" "$WORK/obj/appspawn" "$WORK/obj/pthread_bridge" "$WORK/logs" "$ARTIFACTS"
: >"$WORK/logs/commands.sh"

record_command()
{
    printf '%q ' "$@" >>"$WORK/logs/commands.sh"
    printf '\n' >>"$WORK/logs/commands.sh"
}

run_logged()
{
    local label=$1
    shift
    record_command "$@"
    if ! "$@" >"$WORK/logs/$label.stdout" 2>"$WORK/logs/$label.stderr"; then
        echo "ERROR: $label failed; see $WORK/logs/$label.stderr" >&2
        exit 1
    fi
}

COMMON=(
    "--target=$TARGET"
    "--sysroot=$SYSROOT"
    -B"$TOOLCHAIN/bin"
    -fPIC
    -O2
    -g
    -D__OHOS__
    -D_GNU_SOURCE
    -D_POSIX_SOURCE
    -ffile-prefix-map="$FROZEN_TEST=inputs"
    -fdebug-prefix-map="$FROZEN_TEST=inputs"
    -ffile-prefix-map="$WORK=work"
    -fdebug-prefix-map="$WORK=work"
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

# libcxx_compat.h probes for <__math/traits.h> to decide whether libc++ already
# provides the isinf/isnan/abs/span overloads it would otherwise define itself.
# The probe under-reports on the OHOS libcxx snapshot shipped with clang 15.0.4:
# that tree has no <__math/traits.h> yet does declare those overloads, so the
# header redeclares them and every C++ translation unit fails to compile.  Let
# the caller state the toolchain generation, exactly as the Route A build does.
if [[ -n ${WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT:-} ]]; then
    COMMON+=("-DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=$WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT")
fi

CXX_STD=(
    -nostdinc++
    -isystem "$TOOLCHAIN/include/c++/v1"
    -std=gnu++17
)

LINK_BASE=(
    "--target=$TARGET"
    "--sysroot=$SYSROOT"
    -B"$TOOLCHAIN/bin"
    -B"$TARGET_LIB"
    -fuse-ld=lld
    -Wl,-z,defs
    -Wl,-z,now
    -Wl,--build-id=sha1
    -Wl,--hash-style=both
    -Wl,--no-undefined
    -Wl,--fatal-warnings
)

COMPAT_SRC=$INPUTS/sources/bionic_compat/src
COMPAT_INC=$INPUTS/sources/bionic_compat/include
COMPAT_OBJECTS=()
for source_name in \
    system_properties.cpp \
    malloc_compat.cpp \
    fdsan_stubs.cpp \
    misc_compat.cpp \
    abort_message_compat.cpp \
    liblog_android_supplement.cpp \
    sync_builtins.c
do
    source="$COMPAT_SRC/$source_name"
    object="$WORK/obj/compat/${source_name%.*}.o"
    COMPAT_OBJECTS+=("$object")
    if [[ $source_name == *.c ]]; then
        run_logged "compat_${source_name%.*}" \
            "$CC" "${COMMON[@]}" -std=c11 -D__ANDROID_API__=34 -DPAGE_SIZE=4096 \
            -I"$COMPAT_INC" -c "$source" -o "$object"
    else
        run_logged "compat_${source_name%.*}" \
            "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
            -include "$COMPAT_INC/libcxx_compat.h" -I"$COMPAT_INC" \
            -DPARAM_VALUE_LEN_MAX=96 -Wno-constant-conversion \
            -c "$source" -o "$object"
    fi
done

run_logged compat_link \
    "$CXX" "${LINK_BASE[@]}" -shared -nostdlib++ \
    -Wl,-soname,libbionic_compat.so \
    -L"$INPUTS/libraries/oh" -L"$TARGET_LIB" \
    -o "$ARTIFACTS/libbionic_compat.so.unstripped" \
    "${COMPAT_OBJECTS[@]}" \
    -Wl,--no-as-needed -lbegetutil.z -lc++ -Wl,--as-needed \
    -lc -ldl -lpthread "$BUILTINS"
cp -p "$ARTIFACTS/libbionic_compat.so.unstripped" "$ARTIFACTS/libbionic_compat.so"
run_logged compat_strip "$STRIP" --strip-unneeded "$ARTIFACTS/libbionic_compat.so"

WRAPPER_SRC=$INPUTS/sources/hap_domain_wrapper/westlake_hap_domain_wrapper.cpp
run_logged wrapper_compile \
    "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
    -include "$COMPAT_INC/libcxx_compat.h" -I"$COMPAT_INC" \
    -I"$INPUTS/includes/oh/selinux_policycoreutils" \
    -I"$INPUTS/includes/oh/libselinux" \
    -c "$WRAPPER_SRC" -o "$WORK/obj/wrapper/westlake_hap_domain_wrapper.o"

run_logged wrapper_link \
    "$CXX" "${LINK_BASE[@]}" -shared -nostdlib++ \
    -Wl,-soname,libwestlake_hap_domain_wrapper.so \
    -L"$INPUTS/libraries/oh" -L"$TARGET_LIB" \
    -o "$ARTIFACTS/libwestlake_hap_domain_wrapper.so.unstripped" \
    "$WORK/obj/wrapper/westlake_hap_domain_wrapper.o" \
    -Wl,--no-as-needed -lhap_restorecon.z -lc++ -Wl,--as-needed \
    -lc -ldl -lpthread "$BUILTINS"
cp -p "$ARTIFACTS/libwestlake_hap_domain_wrapper.so.unstripped" \
    "$ARTIFACTS/libwestlake_hap_domain_wrapper.so"
run_logged wrapper_strip "$STRIP" --strip-unneeded \
    "$ARTIFACTS/libwestlake_hap_domain_wrapper.so"
WRAPPER_BUILD_ID=$(
    "$TOOLCHAIN/bin/llvm-readelf" -nW "$ARTIFACTS/libwestlake_hap_domain_wrapper.so" |
        awk '/Build ID:/ {print $3; exit}'
)
[[ "$WRAPPER_BUILD_ID" =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR: wrapper Build-ID is not sha1: $WRAPPER_BUILD_ID" >&2
    exit 1
}
grep -Fq "\"$WRAPPER_BUILD_ID\"" "$INPUTS/sources/appspawn/src/child_main.cpp" || {
    echo "ERROR: child_main.cpp does not pin wrapper Build-ID $WRAPPER_BUILD_ID" >&2
    exit 1
}
printf '%s\n' "$WRAPPER_BUILD_ID" >"$ARTIFACTS/wrapper.build-id"

APPSPAWN_SRC=$INPUTS/sources/appspawn/src
IDENTITY_SRC=$INPUTS/sources/identity/src
IDENTITY_INC=$INPUTS/sources/identity/include
JNI_ATTACH_SRC=$INPUTS/sources/jni_attach_admission/src
JNI_ATTACH_INC=$INPUTS/sources/jni_attach_admission/include
THREAD_GUARD_SRC=$INPUTS/sources/thread_guard_registry/src
THREAD_GUARD_INC=$INPUTS/sources/thread_guard_registry/include
PTHREAD_BRIDGE_SRC=$INPUTS/sources/bionic_pthread_bridge/src
PTHREAD_BRIDGE_INC=$INPUTS/sources/bionic_pthread_bridge/include
PTHREAD_BRIDGE_MAP=$INPUTS/sources/bionic_pthread_bridge/westlake_bionic_pthread_bridge.map
THREAD_TEMPLATE_SRC=$INPUTS/sources/thread_template_publisher/src
THREAD_TEMPLATE_INC=$INPUTS/sources/thread_template_publisher/include
NATIVELOADER_INC=$INPUTS/includes/aosp/libnativeloader/include
NATIVELOADER_LIB=$INPUTS/libraries/aosp/libnativeloader.so
[[ -f "$NATIVELOADER_INC/nativeloader/native_loader.h" ]] || {
    echo "ERROR: missing NativeLoader header: $NATIVELOADER_INC/nativeloader/native_loader.h" >&2
    exit 1
}
[[ -f "$NATIVELOADER_LIB" ]] || {
    echo "ERROR: missing NativeLoader provider: $NATIVELOADER_LIB" >&2
    exit 1
}
APPSPAWN_INC=(
    -I"$APPSPAWN_SRC"
    -I"$IDENTITY_INC"
    -I"$JNI_ATTACH_INC"
    -I"$THREAD_GUARD_INC"
    -I"$PTHREAD_BRIDGE_INC"
    -I"$THREAD_TEMPLATE_INC"
    -I"$INPUTS/includes/oh/appspawn_innerkits"
    -I"$INPUTS/includes/oh/init_innerkits"
    -I"$INPUTS/includes/oh/init_innerkits/syspara"
    -I"$INPUTS/includes/oh/hilog"
    -I"$INPUTS/includes/oh/c_utils"
    -I"$INPUTS/includes/oh/ipc_core"
    -I"$INPUTS/includes/oh/samgr_proxy"
    -I"$INPUTS/includes/oh/json"
    -I"$INPUTS/includes/oh/selinux_policycoreutils"
    -I"$INPUTS/includes/oh/libselinux"
    -I"$INPUTS/includes/oh/token_setproc"
    -I"$INPUTS/includes/oh/accesstoken"
    -I"$COMPAT_INC"
    -I"$INPUTS/includes/aosp/libnativehelper/include_jni"
    -I"$INPUTS/includes/aosp/libnativehelper/include"
    -I"$INPUTS/includes/aosp/libnativehelper/include_platform_header_only"
    -I"$INPUTS/includes/aosp/libnativehelper/include_platform"
    -I"$NATIVELOADER_INC"
)

APPSPAWN_OBJECTS=()
for source_name in main.cpp appspawnx_runtime.cpp spawn_server.cpp child_main.cpp apk_verify_service.cpp native_compat_prepare.cpp; do
    source="$APPSPAWN_SRC/$source_name"
    object="$WORK/obj/appspawn/${source_name%.cpp}.o"
    APPSPAWN_OBJECTS+=("$object")
    extra_defines=()
    if [[ $source_name == child_main.cpp ]]; then
        extra_defines+=(-DWL_APPSPAWNX_ENABLE_LEGACY_CHILD_FOR_D600_NOHARDCODE=1)
    fi
    # main.cpp carries the matching parent-side escape hatch: the parent-ART
    # daemon (preload the VM, then fork per spawn request) is what actually
    # calls ChildMain::run, so enabling the child half without this one leaves
    # nothing to call it.  Route A refuses both by default and builds the stock
    # OH host instead.
    if [[ $source_name == main.cpp ]]; then
        extra_defines+=(-DWESTLAKE_LEGACY_PARENT_ART_TEST_ONLY=1)
    fi
    run_logged "appspawn_${source_name%.cpp}" \
        "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -include "$COMPAT_INC/libcxx_compat.h" "${APPSPAWN_INC[@]}" \
        "${extra_defines[@]}" \
        -c "$source" -o "$object"
done

run_logged appspawn_adapter_bridge_identity \
    "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
    -include "$COMPAT_INC/libcxx_compat.h" "${APPSPAWN_INC[@]}" \
    -DWLAR_ADAPTER_BRIDGE_PATH="\"$BRIDGE_PATH\"" \
    -DWLAR_ADAPTER_BRIDGE_SHA256_HEX="\"$BRIDGE_SHA\"" \
    -DWLAR_ADAPTER_BRIDGE_BUILD_ID_HEX="\"$BRIDGE_BUILD_ID\"" \
    -DWLAR_ANDROID_RUNTIME_PATH="\"$RUNTIME_PATH\"" \
    -DWLAR_ANDROID_RUNTIME_SHA256_HEX="\"$RUNTIME_SHA\"" \
    -DWLAR_ANDROID_RUNTIME_BUILD_ID_HEX="\"$RUNTIME_BUILD_ID\"" \
    -c "$APPSPAWN_SRC/adapter_bridge_identity.cpp" \
    -o "$WORK/obj/appspawn/adapter_bridge_identity.o"
APPSPAWN_OBJECTS+=("$WORK/obj/appspawn/adapter_bridge_identity.o")

for source_name in westlake_elf_identity.c westlake_sha256.c; do
    object="$WORK/obj/appspawn/${source_name%.c}.o"
    run_logged "identity_${source_name%.c}" \
        "$CC" "${COMMON[@]}" -std=c11 -I"$IDENTITY_INC" \
        -c "$IDENTITY_SRC/$source_name" -o "$object"
    APPSPAWN_OBJECTS+=("$object")
done

run_logged appspawn_jni_attach_admission \
    "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
    -include "$COMPAT_INC/libcxx_compat.h" "${APPSPAWN_INC[@]}" \
    -c "$JNI_ATTACH_SRC/jni_attach_admission.cpp" \
    -o "$WORK/obj/appspawn/jni_attach_admission.o"
APPSPAWN_OBJECTS+=("$WORK/obj/appspawn/jni_attach_admission.o")

run_logged appspawn_thread_guard_registry \
    "$CC" "${COMMON[@]}" -std=c11 -I"$THREAD_GUARD_INC" \
    -c "$THREAD_GUARD_SRC/thread_guard_registry.c" \
    -o "$WORK/obj/appspawn/thread_guard_registry.o"
APPSPAWN_OBJECTS+=("$WORK/obj/appspawn/thread_guard_registry.o")

run_logged pthread_bridge_compile \
    "$CC" "${COMMON[@]}" -std=c11 -Wall -Wextra -Werror -pedantic \
    -ffreestanding -fno-stack-protector -fno-unwind-tables \
    -fno-asynchronous-unwind-tables -mno-outline-atomics \
    -I"$PTHREAD_BRIDGE_INC" \
    -c "$PTHREAD_BRIDGE_SRC/bionic_pthread_bridge.c" \
    -o "$WORK/obj/pthread_bridge/bionic_pthread_bridge.o"

run_logged pthread_bridge_link \
    "$CC" \
    "--target=$TARGET" \
    "--sysroot=$SYSROOT" \
    -B"$TOOLCHAIN/bin" \
    -fuse-ld=lld -nostdlib -shared \
    -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
    -Wl,--no-undefined -Wl,--fatal-warnings \
    -Wl,--build-id=sha1 -Wl,--hash-style=both \
    -Wl,-soname,libwestlake_bionic_pthread_bridge.so \
    -Wl,--version-script="$PTHREAD_BRIDGE_MAP" \
    "$WORK/obj/pthread_bridge/bionic_pthread_bridge.o" \
    -o "$ARTIFACTS/libwestlake_bionic_pthread_bridge.so"

run_logged appspawn_thread_template_publisher \
    "$CC" "${COMMON[@]}" -std=c11 -I"$THREAD_TEMPLATE_INC" \
    -c "$THREAD_TEMPLATE_SRC/thread_template_publisher.c" \
    -o "$WORK/obj/appspawn/thread_template_publisher.o"
APPSPAWN_OBJECTS+=("$WORK/obj/appspawn/thread_template_publisher.o")

run_logged appspawn_guard_store \
    "$CC" "${COMMON[@]}" -c "$THREAD_GUARD_SRC/guard_store_aarch64.S" \
    -o "$WORK/obj/appspawn/guard_store_aarch64.o"
APPSPAWN_OBJECTS+=("$WORK/obj/appspawn/guard_store_aarch64.o")

run_logged appspawn_native_compat_owner \
    "$CC" "${COMMON[@]}" -c "$INPUTS/sources/appspawn/src/native_compat_prepare_owner_aarch64.S" \
    -o "$WORK/obj/appspawn/native_compat_prepare_owner_aarch64.o"
APPSPAWN_OBJECTS+=("$WORK/obj/appspawn/native_compat_prepare_owner_aarch64.o")

run_logged appspawn_tls_prefix \
    "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
    -c "$INPUTS/sources/appspawn/tls_prefix/bionic_tls_prefix_reservation.cpp" \
    -o "$WORK/obj/appspawn/bionic_tls_prefix_reservation.o"
APPSPAWN_OBJECTS+=("$WORK/obj/appspawn/bionic_tls_prefix_reservation.o")

run_logged appspawn_link \
    "$CXX" "${LINK_BASE[@]}" -pie \
    -L"$ARTIFACTS" -L"$INPUTS/libraries/aosp" -L"$INPUTS/libraries/oh" -L"$TARGET_LIB" \
    -o "$ARTIFACTS/appspawn-x.unstripped" \
    "${APPSPAWN_OBJECTS[@]}" \
    -Wl,--no-as-needed \
    -lc -lhilog -lipc_single.z -lsamgr_proxy.z -lbegetutil.z -lselinux.z \
    -lhap_restorecon.z -ltokensetproc_shared.z \
    -lnativehelper -llog -lbionic_compat -lart -lnativeloader -lc++ \
    -Wl,--as-needed -ldl -lpthread "$BUILTINS"
cp -p "$ARTIFACTS/appspawn-x.unstripped" "$ARTIFACTS/appspawn-x"
run_logged appspawn_strip "$STRIP" --strip-unneeded "$ARTIFACTS/appspawn-x"
cp -p "$INPUTS/config/appspawn_x.cfg" "$ARTIFACTS/appspawn_x.cfg"

sha256sum "$ARTIFACTS"/appspawn-x "$ARTIFACTS"/appspawn-x.unstripped \
    "$ARTIFACTS"/libbionic_compat.so \
    "$ARTIFACTS"/libwestlake_hap_domain_wrapper.so \
    "$ARTIFACTS"/libwestlake_hap_domain_wrapper.so.unstripped \
    "$ARTIFACTS"/wrapper.build-id \
    "$ARTIFACTS"/libwestlake_bionic_pthread_bridge.so \
    "$ARTIFACTS"/appspawn_x.cfg \
    | sed "s#$ARTIFACTS/##" >"$ARTIFACTS/artifacts.sha256"
echo "build_pass: appspawn-x rebuilt against BRIDGE_SHA=$BRIDGE_SHA RUNTIME_SHA=$RUNTIME_SHA"
