#!/usr/bin/env bash
# Freeze every source/header/sysroot/library/tool input used by the AArch64
# appspawn-x generation build into this project.  This is the *only* stage
# allowed to read an external origin.  build_generation.sh never mounts or
# references any origin named below.

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd -P)
ADAPTER_ROOT="$PROJECT_ROOT/adapter"
DEFAULT_GENERATION_ROOT="$PROJECT_ROOT/.work/product-tls-generation"
GENERATION_ROOT=${WESTLAKE_GENERATION_ROOT:-$DEFAULT_GENERATION_ROOT}
REFRESH=0

if [[ ${1:-} == "--refresh" ]]; then
    REFRESH=1
elif [[ $# -ne 0 ]]; then
    echo "usage: $0 [--refresh]" >&2
    exit 2
fi

if [[ -z "${WESTLAKE_GENERATION_ROOT:-}" ]]; then
    case "$GENERATION_ROOT" in
        "$PROJECT_ROOT"/.work/*) ;;
        *)
            echo "ERROR: generation root must be below $PROJECT_ROOT/.work" >&2
            exit 2
            ;;
    esac
fi

if [[ -e "$GENERATION_ROOT" ]]; then
    if [[ $REFRESH -ne 1 ]]; then
        echo "ERROR: frozen generation already exists: $GENERATION_ROOT" >&2
        echo "Use --refresh only when intentionally creating a new input generation." >&2
        exit 2
    fi
    chmod -R u+w "$GENERATION_ROOT"
    rm -rf -- "$GENERATION_ROOT"
fi

mkdir -p "$GENERATION_ROOT/frozen" "$GENERATION_ROOT/.tmp"
export TMPDIR="$GENERATION_ROOT/.tmp"
export COPYFILE_DISABLE=1

FROZEN="$GENERATION_ROOT/frozen"
PROVENANCE="$GENERATION_ROOT/provenance.tsv"
LOCAL_HASHES="$GENERATION_ROOT/frozen.sha256"
MAPPINGS="$GENERATION_ROOT/.tmp/origin-mappings.tsv"
: >"$MAPPINGS"

sha_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

require_file()
{
    [[ -f "$1" ]] || { echo "ERROR: missing origin file: $1" >&2; exit 1; }
}

require_dir()
{
    [[ -d "$1" ]] || { echo "ERROR: missing origin directory: $1" >&2; exit 1; }
}

copy_file()
{
    local kind=$1 origin=$2 relative_dest=$3 deployability=${4:-BUILD_INPUT}
    local dest="$FROZEN/$relative_dest"
    require_file "$origin"
    mkdir -p "$(dirname "$dest")"
    cp -pL "$origin" "$dest"
    printf '%s\t%s\t%s\t%s\n' "$kind" "$relative_dest" "$origin" "$deployability" >>"$MAPPINGS"
}

copy_tree()
{
    local kind=$1 origin=$2 relative_dest=$3 deployability=${4:-BUILD_INPUT}
    local dest="$FROZEN/$relative_dest"
    require_dir "$origin"
    mkdir -p "$dest"
    cp -R -L "$origin/." "$dest/"
    find "$dest" -type f -print | LC_ALL=C sort | while IFS= read -r local_file; do
        local rel=${local_file#"$dest"/}
        printf '%s\t%s/%s\t%s/%s\t%s\n' \
            "$kind" "$relative_dest" "$rel" "$origin" "$rel" "$deployability" >>"$MAPPINGS"
    done
}

# Read-only origins.  These paths are provenance facts, never build paths.
OH_ORIGIN=${WESTLAKE_OH_ORIGIN:-/opt/10.Project/16-WestLake/16.12-HanBing/oh}
AOSP_ORIGIN=${WESTLAKE_AOSP_ORIGIN:-/opt/10.Project/16-WestLake/16.12-HanBing/home/HanBingChen/aosp}
ROM_ORIGIN=${WESTLAKE_ROM_ORIGIN:-/opt/21.Game/scratchpad/rom001_system_readonly/extracted/system}
TOOLCHAIN_ORIGIN=${WESTLAKE_TOOLCHAIN_ORIGIN:-$OH_ORIGIN/prebuilts/clang/ohos/linux-x86_64/llvm}
OH_OUT_ORIGIN=${WESTLAKE_OH_OUT_ORIGIN:-$OH_ORIGIN/out/wukong100}
SYSROOT_ORIGIN=${WESTLAKE_SYSROOT_ORIGIN:-$OH_OUT_ORIGIN/obj/third_party/musl/usr}
REGISTRY_ORIGIN=${WESTLAKE_REGISTRY_ORIGIN:-$PROJECT_ROOT/../.work/registry-lib/libwestlake_thread_guard_registry.so}
IDENTITY_ORIGIN=${WESTLAKE_APPSPAWNX_IDENTITY_ORIGIN:-$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/r45_adapter_identity.env}

# Exact project sources participating in this generation.  The appspawn src
# directory is copied as a header closure, while container_build.sh names the
# only translation units that are compiled.
copy_tree source "$ADAPTER_ROOT/framework/appspawn-x/src" sources/appspawn/src
copy_file source "$ADAPTER_ROOT/framework/appspawn-x/tls_prefix/bionic_tls_prefix_reservation.cpp" \
    sources/appspawn/tls_prefix/bionic_tls_prefix_reservation.cpp
copy_file source "$ADAPTER_ROOT/framework/appspawn-x/hap_domain_wrapper/westlake_hap_domain_wrapper.cpp" \
    sources/hap_domain_wrapper/westlake_hap_domain_wrapper.cpp
copy_tree header "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include" \
    sources/bionic_compat/include

# The admitted compat producer is intentionally narrow.  In particular these
# inputs do NOT include bionic_tls_abi.c, unity_pthread_box.c,
# unity_signal_box.c, or the deprecated minizip.cpp.  ZIP ABI ownership belongs
# to the recursively frozen real AOSP libziparchive provider, never compat.
# Adding a denied source requires a separate architecture review and is
# rejected by the verifier.
for compat_source in \
    system_properties.cpp \
    malloc_compat.cpp \
    fdsan_stubs.cpp \
    misc_compat.cpp \
    abort_message_compat.cpp \
    liblog_android_supplement.cpp \
    sync_builtins.c
do
    copy_file source \
        "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src/$compat_source" \
        "sources/bionic_compat/src/$compat_source"
done

# Native-compatibility implementation sources referenced directly by appspawn-x.
copy_file source \
    "$ADAPTER_ROOT/framework/native-compat/jni-attach-admission/src/jni_attach_admission.cpp" \
    sources/native_compat/jni_attach_admission.cpp
copy_file source \
    "$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/src/thread_guard_registry.c" \
    sources/native_compat/thread_guard_registry.c
copy_file source \
    "$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/src/guard_store_aarch64.S" \
    sources/native_compat/guard_store_aarch64.S
copy_file source \
    "$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/src/thread_guard_registry_internal.h" \
    sources/native_compat/thread_guard_registry_internal.h
copy_file source \
    "$ADAPTER_ROOT/framework/native-compat/thread-template-publisher/src/thread_template_publisher.c" \
    sources/native_compat/thread_template_publisher.c
copy_file source \
    "$ADAPTER_ROOT/framework/native-compat/bionic-pthread-bridge/src/bionic_pthread_bridge.c" \
    sources/native_compat/bionic_pthread_bridge.c

# ELF identity verification used by adapter_bridge_identity.cpp.
copy_file header \
    "$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/include/westlake_elf_identity.h" \
    includes/native/westlake_elf_identity.h
copy_file source \
    "$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/src/westlake_elf_identity.c" \
    sources/native_compat/westlake_elf_identity.c
copy_file header \
    "$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/include/westlake_sha256.h" \
    includes/native/westlake_sha256.h
copy_file source \
    "$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/src/westlake_sha256.c" \
    sources/native_compat/westlake_sha256.c

# Prebuilt thread-guard registry provider required by native_compat_prepare.cpp.
copy_file library \
    "$REGISTRY_ORIGIN" \
    libraries/native/libwestlake_thread_guard_registry.so

# Route-A identity contract for adapter_bridge_identity.cpp.
copy_file config \
    "$IDENTITY_ORIGIN" \
    config/appspawnx-identity.env DEPLOYABLE_CONFIG

# AOSP header inputs used by appspawn-x.  They are copied before compilation;
# no compiler invocation can see the external AOSP tree.
copy_tree header "$AOSP_ORIGIN/libnativehelper/include_jni" includes/aosp/libnativehelper/include_jni
copy_tree header "$AOSP_ORIGIN/libnativehelper/include" includes/aosp/libnativehelper/include
copy_tree header "$AOSP_ORIGIN/libnativehelper/include_platform_header_only" \
    includes/aosp/libnativehelper/include_platform_header_only
copy_tree header "$AOSP_ORIGIN/libnativehelper/include_platform" \
    includes/aosp/libnativehelper/include_platform

# Adapter native-compatibility headers referenced by appspawn-x sources
# (e.g., appspawnx_runtime.h -> westlake_jni_attach_admission.h).
copy_tree header "$ADAPTER_ROOT/framework/native-compat/bionic-pthread-bridge/include" \
    includes/native/bionic_pthread_bridge
copy_tree header "$ADAPTER_ROOT/framework/native-compat/jni-attach-admission/include" \
    includes/native/jni_attach_admission
copy_tree header "$ADAPTER_ROOT/framework/native-compat/thread-guard-registry/include" \
    includes/native/thread_guard_registry
copy_tree header "$ADAPTER_ROOT/framework/native-compat/thread-template-publisher/include" \
    includes/native/thread_template_publisher
copy_tree header "$ADAPTER_ROOT/framework/native-loader-oh/include" \
    includes/native_loader

# OpenHarmony header inputs used by appspawn-x and the stock HAP wrapper.
copy_tree header "$OH_ORIGIN/base/startup/appspawn/interfaces/innerkits/include" \
    includes/oh/appspawn_innerkits
copy_tree header "$OH_ORIGIN/base/startup/init/interfaces/innerkits/include" \
    includes/oh/init_innerkits
copy_tree header "$OH_ORIGIN/base/hiviewdfx/hilog/interfaces/native/innerkits/include" \
    includes/oh/hilog
copy_tree header "$OH_ORIGIN/commonlibrary/c_utils/base/include" includes/oh/c_utils
copy_tree header "$OH_ORIGIN/foundation/communication/ipc/interfaces/innerkits/ipc_core/include" \
    includes/oh/ipc_core
copy_tree header "$OH_ORIGIN/foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include" \
    includes/oh/samgr_proxy
copy_tree header "$OH_ORIGIN/third_party/json/include" includes/oh/json
copy_tree header "$OH_ORIGIN/base/security/selinux_adapter/interfaces/policycoreutils/include" \
    includes/oh/selinux_policycoreutils
copy_tree header "$OH_ORIGIN/third_party/selinux/libselinux/include" \
    includes/oh/libselinux
copy_tree header "$OH_ORIGIN/base/security/access_token/interfaces/innerkits/token_setproc/include" \
    includes/oh/token_setproc
copy_tree header "$OH_ORIGIN/base/security/access_token/interfaces/innerkits/accesstoken/include" \
    includes/oh/accesstoken

# Complete target sysroot.  The origin's include entry is an absolute symlink;
# copy_tree dereferences it so the frozen closure has no escape path.
copy_tree sysroot "$SYSROOT_ORIGIN" sysroot

# Exact deployable library link inputs.  libipc_core.z.so is the link name of
# the same bytes whose runtime SONAME is libipc_single.z.so.
copy_file library "$ROM_ORIGIN/lib64/chipset-sdk/libhilog.so" libraries/oh/libhilog.so
copy_file library "$ROM_ORIGIN/lib64/platformsdk/libipc_single.z.so" libraries/oh/libipc_core.z.so
copy_file library "$ROM_ORIGIN/lib64/chipset-sdk-sp/libsamgr_proxy.z.so" libraries/oh/libsamgr_proxy.z.so
copy_file library "$ROM_ORIGIN/lib64/chipset-sdk-sp/libbegetutil.z.so" libraries/oh/libbegetutil.z.so
copy_file library "$ROM_ORIGIN/lib64/chipset-sdk-sp/libselinux.z.so" libraries/oh/libselinux.z.so
copy_file library "$ROM_ORIGIN/lib64/libhap_restorecon.z.so" libraries/oh/libhap_restorecon.z.so
copy_file library "$ROM_ORIGIN/lib64/platformsdk/libtokensetproc_shared.z.so" \
    libraries/oh/libtokensetproc_shared.z.so
copy_file library "$ROM_ORIGIN/lib64/chipset-sdk-sp/libc++.so" libraries/oh/libc++.so

copy_file library "$ADAPTER_ROOT/out/aosp_lib64/libnativehelper.so" libraries/aosp/libnativehelper.so
copy_file library "$ADAPTER_ROOT/out/aosp_lib64/liblog.so" libraries/aosp/liblog.so
copy_file library "$ADAPTER_ROOT/out/aosp_lib64/libart.so" libraries/aosp/libart.so

# Freeze the minimum OH clang-15 executable closure as project-local tools.
# Ubuntu runtime libraries are supplied only by the locked read-only container
# image; all compiler binaries, resource headers, C++ headers and target
# runtime objects are local frozen inputs.
copy_file tool "$TOOLCHAIN_ORIGIN/bin/clang-15" toolchain/bin/clang-15 NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/bin/lld" toolchain/bin/ld.lld NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/bin/llvm-readobj" toolchain/bin/llvm-readelf NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/bin/llvm-objcopy" toolchain/bin/llvm-strip NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/bin/llvm-objdump" toolchain/bin/llvm-objdump NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/lib/libxml2.so.2.14.0" toolchain/lib/libxml2.so.16 NEVER_DEPLOY_TOOL
copy_tree tool "$TOOLCHAIN_ORIGIN/include/libcxx-ohos/include/c++/v1" \
    toolchain/include/c++/v1 NEVER_DEPLOY_TOOL
copy_tree tool "$TOOLCHAIN_ORIGIN/lib/clang/15.0.4/include" \
    toolchain/lib/clang/15.0.4/include NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a" \
    toolchain/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtbegin.o" \
    toolchain/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtbegin.o NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtend.o" \
    toolchain/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtend.o NEVER_DEPLOY_TOOL
copy_file tool "$TOOLCHAIN_ORIGIN/lib/aarch64-linux-ohos/libunwind.a" \
    toolchain/lib/aarch64-linux-ohos/libunwind.a NEVER_DEPLOY_TOOL

# Build configuration is also frozen and hashed before the container sees it.
copy_file config "$SCRIPT_DIR/container_build.sh" config/container_build.sh NEVER_DEPLOY_CONFIG
copy_file config "$SCRIPT_DIR/verify_generation.py" config/verify_generation.py NEVER_DEPLOY_CONFIG
copy_file config "$SCRIPT_DIR/expected_wrapper_build_id.txt" \
    config/expected_wrapper_build_id.txt NEVER_DEPLOY_CONFIG
copy_file config "$ADAPTER_ROOT/framework/appspawn-x/config/appspawn_x.cfg" \
    config/appspawn_x.cfg DEPLOYABLE_CONFIG

printf 'kind\tlocal_path\torigin_path\torigin_sha256\tlocal_sha256\tdeployability\n' >"$PROVENANCE"
LC_ALL=C sort -t $'\t' -k2,2 "$MAPPINGS" | while IFS=$'\t' read -r kind relative origin deployability; do
    local_file="$FROZEN/$relative"
    origin_sha=$(sha_file "$origin")
    local_sha=$(sha_file "$local_file")
    [[ "$origin_sha" == "$local_sha" ]] || {
        echo "ERROR: copy hash mismatch: $origin -> $relative" >&2
        exit 1
    }
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$kind" "$relative" "$origin" "$origin_sha" "$local_sha" "$deployability" >>"$PROVENANCE"
done

tail -n +2 "$PROVENANCE" | awk -F '\t' '{print $5 "  " $2}' >"$LOCAL_HASHES"

EXPECTED_IMAGE='sha256:76236bc11d9359a260c3e715cfee437bed387f76ff86c9ac086c1a52c3536797'
ACTUAL_IMAGE=$(docker image inspect westlake-oharm64build:local-tools --format '{{.Id}}')
[[ "$ACTUAL_IMAGE" == "$EXPECTED_IMAGE" ]] || {
    echo "ERROR: container image identity changed: $ACTUAL_IMAGE" >&2
    exit 1
}
cat >"$GENERATION_ROOT/tool_runtime.lock" <<EOF
image=westlake-oharm64build:local-tools
image_id=$ACTUAL_IMAGE
platform=linux/amd64
rootfs=read-only
compiler=frozen/toolchain/bin/clang-15
EOF

chmod -R a-w "$FROZEN"
chmod a+x "$FROZEN/toolchain/bin/"* "$FROZEN/config/container_build.sh"

echo "Frozen input closure ready: $GENERATION_ROOT"
echo "Provenance: $PROVENANCE"
echo "Build entry: $SCRIPT_DIR/build_generation.sh"
