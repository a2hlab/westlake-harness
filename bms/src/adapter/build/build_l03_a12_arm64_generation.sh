#!/usr/bin/env bash
set -euo pipefail

# Build one immutable L03.A12/Profile-B ARM64 generation. This script never
# deploys or talks to a device. A generation becomes deploy-eligible only when
# the provider subgraph and full payload+immutable-base closure both pass.

usage()
{
    cat <<'EOF'
Usage: build_l03_a12_arm64_generation.sh

Required environment:
  L03_A12_GENERATION_ID          immutable generation label
  L03_A12_GENERATION_ROOT        new absolute output directory; basename=id
  L03_A12_BUILD_LOCK             absolute lock file under generation parent
  OH_ROOT / AOSP_ROOT            exact external source roots
  OH_PRODUCT_NAME                pinned OH product (for example wukong100)
  OH_TOOLCHAIN_ROOT              manifest-covered OH LLVM tree
  OH_CC / OH_CXX                 exact ARM64 OH clang tools
  OH_READELF / OH_NM             exact LLVM inspection tools
  OH_BUILTINS                    exact ARM64 compiler-rt builtins archive
  L03_A12_LIBCXX_INCLUDE         exact libc++ include tree used by ARM64 producers
  OH_SYSROOT                     exact OH product musl root (.../musl)
  L03_A12_PYTHON / L03_A12_AIDL exact generator executables
  L03_A12_SOURCE_MANIFEST        adapter source SHA-256 manifest
  L03_A12_TOOLCHAIN_MANIFEST     toolchain/host-tool SHA-256 manifest
  L03_A12_SYSROOT_MANIFEST       OH output/sysroot/link-input SHA manifest
  L03_A12_EXTERNAL_SOURCE_MANIFEST  AOSP/OH source SHA manifest
  L03_A12_OFFICIAL_PREBUILT_POOL_ROOT  exact OH packages/phone provider pool
  L03_A12_OFFICIAL_PREBUILT_POOL_MANIFEST SHA manifest for that pool
  L03_A12_IMAGE_FINGERPRINT      target image identity
  L03_A12_EXPECTED_INTERPRETER   absolute appspawn PT_INTERP path
  L03_A12_OH_SERVICE_DIR         directory containing patched OH service .z.so
                                 (e.g. out/oh-service/); may be empty

The generation parent must be a local Linux ext4 filesystem. Inputs are
coverage-checked before and after the build. Bridge, backend, NativeLoader,
runtime, ART companions, and appspawn-x are built in this one generation.
EOF
}

if [ "${1:-}" = --help ] || [ "${1:-}" = -h ]; then
    usage
    exit 0
fi
if [ "$#" -ne 0 ]; then
    usage >&2
    exit 2
fi

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GENERATION_ID=${L03_A12_GENERATION_ID:?L03_A12_GENERATION_ID is required}
GENERATION_ROOT=${L03_A12_GENERATION_ROOT:?L03_A12_GENERATION_ROOT is required}
BUILD_LOCK=${L03_A12_BUILD_LOCK:?L03_A12_BUILD_LOCK is required}
OH=${OH_ROOT:?OH_ROOT is required}
AOSP=${AOSP_ROOT:?AOSP_ROOT is required}
OH_PRODUCT=${OH_PRODUCT_NAME:?OH_PRODUCT_NAME is required}
TOOLCHAIN_ROOT=${OH_TOOLCHAIN_ROOT:?OH_TOOLCHAIN_ROOT is required}
CC=${OH_CC:?OH_CC is required}
CXX=${OH_CXX:?OH_CXX is required}
READELF=${OH_READELF:?OH_READELF is required}
NM=${OH_NM:?OH_NM is required}
BUILTINS=${OH_BUILTINS:?OH_BUILTINS is required}
LIBCXX_INCLUDE=${L03_A12_LIBCXX_INCLUDE:?L03_A12_LIBCXX_INCLUDE is required}
SYSROOT=${OH_SYSROOT:?OH_SYSROOT is required}
PYTHON=${L03_A12_PYTHON:?L03_A12_PYTHON is required}
AIDL=${L03_A12_AIDL:?L03_A12_AIDL is required}
SOURCE_MANIFEST=${L03_A12_SOURCE_MANIFEST:?L03_A12_SOURCE_MANIFEST is required}
TOOLCHAIN_MANIFEST=${L03_A12_TOOLCHAIN_MANIFEST:?L03_A12_TOOLCHAIN_MANIFEST is required}
SYSROOT_MANIFEST=${L03_A12_SYSROOT_MANIFEST:?L03_A12_SYSROOT_MANIFEST is required}
EXTERNAL_SOURCE_MANIFEST=${L03_A12_EXTERNAL_SOURCE_MANIFEST:?L03_A12_EXTERNAL_SOURCE_MANIFEST is required}
OFFICIAL_PREBUILT_POOL_ROOT=${L03_A12_OFFICIAL_PREBUILT_POOL_ROOT:?L03_A12_OFFICIAL_PREBUILT_POOL_ROOT is required}
OFFICIAL_PREBUILT_POOL_MANIFEST=${L03_A12_OFFICIAL_PREBUILT_POOL_MANIFEST:?L03_A12_OFFICIAL_PREBUILT_POOL_MANIFEST is required}
IMAGE_FINGERPRINT=${L03_A12_IMAGE_FINGERPRINT:?L03_A12_IMAGE_FINGERPRINT is required}
EXPECTED_INTERPRETER=${L03_A12_EXPECTED_INTERPRETER:?L03_A12_EXPECTED_INTERPRETER is required}
OH_SERVICE_DIR=${L03_A12_OH_SERVICE_DIR:-}

VERIFY_INPUT=$ROOT/scripts/verify_l03_a12_input_manifest.py
VERIFY_TREE=$ROOT/scripts/verify_l03_a12_tree_identity.py
WRITE_SHA=$ROOT/scripts/write_l03_a12_sha_manifest.py
WRITE_MANIFEST=$ROOT/scripts/write_l03_a12_provider_manifest.py
VERIFY_CLOSURE=$ROOT/scripts/verify_l03_a12_provider_closure.sh
RESOLVE_IMMUTABLE_BASE=$ROOT/scripts/build_l03_a12_immutable_base.py
WRITE_DEPLOY_PLAN=$ROOT/scripts/write_l03_a12_deploy_plan.py

[[ $GENERATION_ID =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || {
    echo "invalid L03_A12_GENERATION_ID: $GENERATION_ID" >&2
    exit 2
}
case "$GENERATION_ROOT" in
    /*) ;;
    *) echo "L03_A12_GENERATION_ROOT must be absolute" >&2; exit 2 ;;
esac
case "$BUILD_LOCK" in
    /*) ;;
    *) echo "L03_A12_BUILD_LOCK must be absolute" >&2; exit 2 ;;
esac
case "$EXPECTED_INTERPRETER" in
    /*) ;;
    *) echo "L03_A12_EXPECTED_INTERPRETER must be absolute" >&2; exit 2 ;;
esac
case "$EXPECTED_INTERPRETER" in
    *'/../'*|*'/..'|*'//'*) echo "unsafe expected interpreter" >&2; exit 2 ;;
esac
[ "$(basename "$GENERATION_ROOT")" = "$GENERATION_ID" ] || {
    echo "generation root basename must equal generation id" >&2
    exit 2
}
if [ -e "$GENERATION_ROOT" ] || [ -L "$GENERATION_ROOT" ]; then
    echo "generation root already exists; refusing reuse: $GENERATION_ROOT" >&2
    exit 2
fi

GENERATION_PARENT=$(dirname "$GENERATION_ROOT")
for directory in "$GENERATION_PARENT" "$OH" "$AOSP" "$TOOLCHAIN_ROOT" \
                 "$SYSROOT" "$LIBCXX_INCLUDE" "$OFFICIAL_PREBUILT_POOL_ROOT"; do
    [ -d "$directory" ] && [ ! -L "$directory" ] || {
        echo "required directory is missing or a symlink: $directory" >&2
        exit 2
    }
done
for executable in "$CC" "$CXX" "$READELF" "$NM" "$PYTHON" "$AIDL"; do
    [ -x "$executable" ] || {
        echo "required executable is missing: $executable" >&2
        exit 2
    }
done
for input in "$BUILTINS" "$SOURCE_MANIFEST" "$TOOLCHAIN_MANIFEST" \
             "$SYSROOT_MANIFEST" "$EXTERNAL_SOURCE_MANIFEST" \
             "$OFFICIAL_PREBUILT_POOL_MANIFEST" "$VERIFY_INPUT" \
             "$VERIFY_TREE" "$WRITE_SHA" "$WRITE_MANIFEST" "$VERIFY_CLOSURE" \
             "$RESOLVE_IMMUTABLE_BASE" "$WRITE_DEPLOY_PLAN"; do
    [ -f "$input" ] && [ ! -L "$input" ] || {
        echo "required input is missing or a symlink: $input" >&2
        exit 2
    }
done

OH_OUT=$OH/out/$OH_PRODUCT
MUSL_ROOT=$OH_OUT/obj/third_party/musl
SYSTEM_LIB_ROOT=$OH_OUT/packages/phone/system/lib64
OH_GEN_ROOT=$OH_OUT/gen
OPENSSL_GEN_ROOT=$OH_OUT/obj/third_party/openssl/build_all_generated/include
ZLIB_OBJ_ROOT=$OH_OUT/obj/third_party/zlib
OFFICIAL_SYSTEM_LIB_ROOT=$OFFICIAL_PREBUILT_POOL_ROOT/system/lib64
DLNS_PROVIDER=$OFFICIAL_PREBUILT_POOL_ROOT/system/lib/$(basename "$EXPECTED_INTERPRETER")
for directory in "$MUSL_ROOT" "$SYSTEM_LIB_ROOT" "$OH_GEN_ROOT" \
                 "$OPENSSL_GEN_ROOT" "$ZLIB_OBJ_ROOT" \
                 "$OFFICIAL_SYSTEM_LIB_ROOT"; do
    [ -d "$directory" ] && [ ! -L "$directory" ] || {
        echo "required OH output input is missing or a symlink: $directory" >&2
        exit 2
    }
done
OFFICIAL_POOL_PHYSICAL=$(cd "$OFFICIAL_PREBUILT_POOL_ROOT" && pwd -P)
OH_PHONE_PHYSICAL=$(cd "$OH_OUT/packages/phone" && pwd -P)
[ "$OFFICIAL_POOL_PHYSICAL" = "$OH_PHONE_PHYSICAL" ] || {
    echo "official prebuilt pool must be the selected product packages/phone root" >&2
    exit 2
}
SYSROOT_PHYSICAL=$(cd "$SYSROOT" && pwd -P)
MUSL_PHYSICAL=$(cd "$MUSL_ROOT" && pwd -P)
[ "$SYSROOT_PHYSICAL" = "$MUSL_PHYSICAL" ] || {
    echo "OH_SYSROOT must be the selected product musl root: $MUSL_ROOT" >&2
    exit 2
}
for tool in "$CC" "$CXX" "$READELF" "$NM" "$BUILTINS"; do
    case "$tool" in
        "$TOOLCHAIN_ROOT"/*) ;;
        *) echo "OH tool escapes OH_TOOLCHAIN_ROOT: $tool" >&2; exit 2 ;;
    esac
done
case "$LIBCXX_INCLUDE" in
    "$TOOLCHAIN_ROOT"/*) ;;
    *)
        echo "ARM64 libc++ include tree must belong to the selected OH toolchain: $LIBCXX_INCLUDE" >&2
        exit 2
        ;;
esac
[ -f "$LIBCXX_INCLUDE/__config_site" ] && [ ! -L "$LIBCXX_INCLUDE/__config_site" ] || {
    echo "ARM64 libc++ include tree lacks a regular target __config_site: $LIBCXX_INCLUDE" >&2
    exit 2
}

[ -f "$DLNS_PROVIDER" ] && [ ! -L "$DLNS_PROVIDER" ] || {
    echo "official prebuilt pool lacks regular expected interpreter: $DLNS_PROVIDER" >&2
    exit 2
}

if ! command -v findmnt >/dev/null 2>&1; then
    echo "findmnt is required for the ext4 provenance gate" >&2
    exit 2
fi
FILESYSTEM_TYPE=$(findmnt -T "$GENERATION_PARENT" -n -o FSTYPE)
[ "$FILESYSTEM_TYPE" = ext4 ] || {
    echo "generation parent must be Linux ext4; actual=$FILESYSTEM_TYPE" >&2
    exit 2
}
case "$BUILD_LOCK" in
    "$GENERATION_PARENT"/*) ;;
    *) echo "build lock must be below the generation parent" >&2; exit 2 ;;
esac
if [ -L "$BUILD_LOCK" ] || { [ -e "$BUILD_LOCK" ] && [ ! -f "$BUILD_LOCK" ]; }; then
    echo "build lock must be a regular non-symlink file" >&2
    exit 2
fi
command -v flock >/dev/null 2>&1 || {
    echo "flock is required for generation serialization" >&2
    exit 2
}
exec 9>"$BUILD_LOCK"
flock -n 9 || {
    echo "another L03.A12 generation owns the build lock: $BUILD_LOCK" >&2
    exit 3
}

sha256_file()
{
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

elf_build_id()
{
    local artifact=$1 build_id count
    [ -f "$artifact" ] && [ ! -L "$artifact" ] || {
        echo "identity artifact is missing or a symlink: $artifact" >&2
        return 1
    }
    build_id=$(
        "$READELF" --notes --wide "$artifact" |
            awk '/Build ID:/ { count++; value=$NF }
                 END { if (count != 1) exit 2; print tolower(value) }'
    ) || {
        echo "ELF must contain exactly one Build-ID: $artifact" >&2
        return 1
    }
    [[ $build_id =~ ^[0-9a-f]{40}$ ]] || {
        echo "ELF Build-ID must be SHA1/40-hex: $artifact id=$build_id" >&2
        return 1
    }
    printf '%s\n' "$build_id"
}

oh_service_deploy_path()
{
    local name=$1
    case "$name" in
        libabilityms.z.so|libmission_list.z.so|libscene_session.z.so|libscene_session_manager.z.so|librender_service_base.z.so|libappexecfwk_common.z.so)
            printf '/system/lib64/platformsdk/%s\n' "$name"
            ;;
        libwms.z.so|libappms.z.so|libbms.z.so|libskia_canvaskit.z.so|libappspawn_client.z.so|librender_service.z.so|libsurface.z.so|libinstalls.z.so)
            printf '/system/lib64/%s\n' "$name"
            ;;
        *)
            echo "unsupported OH service artifact: $name" >&2
            return 1
            ;;
    esac
}

deploy_destination()
{
    local payload_source=$1
    case "$payload_source" in
        bin/appspawn-x) printf '%s\n' /system/bin/appspawn-x ;;
        adapter/*.so|aosp/*.so)
            printf '/system/android/lib64/%s\n' "${payload_source##*/}"
            ;;
        oh-service/*.z.so)
            oh_service_deploy_path "${payload_source##*/}"
            ;;
        *)
            echo "unsupported payload deploy source: $payload_source" >&2
            return 1
            ;;
    esac
}

SOURCE_REQUIRED_FILES=(
    "$ROOT/build/compile_app_native_loader_arm64.sh"
    "$ROOT/build/build_l03_a12_arm64_generation.sh"
    "$ROOT/build/inner/cross_compile_arm64.sh"
    "$ROOT/build/inner/cross_compile_minikin_stack_arm64.sh"
    "$ROOT/build/inner/cross_compile_extras_arm64.sh"
    "$ROOT/build/inner/compile_oh_adapter_bridge_arm64.sh"
    "$ROOT/build/inner/oh_adapter_bridge.ninja.template"
    "$ROOT/build/inner/compile_oh_android_runtime_arm64_stage2unity.sh"
    "$ROOT/build/inner/compile_appspawnx.sh"
    "$VERIFY_INPUT"
    "$VERIFY_TREE"
    "$WRITE_SHA"
    "$WRITE_MANIFEST"
    "$VERIFY_CLOSURE"
    "$RESOLVE_IMMUTABLE_BASE"
    "$WRITE_DEPLOY_PLAN"
    "$ROOT/scripts/verify_l03_a12_deploy_closure.py"
    "$ROOT/scripts/test_l03_a12_profile_b_build_wiring.sh"
    "$ROOT/build/compat/musl_socket_fix.h"
    "$ROOT/build/compat/musl_tgkill_compat.h"
)
LOCAL_SOURCE_TREES=(
    "$ROOT/framework"
    "$ROOT/third_party"
    "$ROOT/build/oh_headers_631_overlay"
    "$ROOT/build/skia_compat_headers"
)
EXTERNAL_SOURCE_TREES=(
    "$AOSP/art"
    "$AOSP/bionic"
    "$AOSP/external"
    "$AOSP/frameworks"
    "$AOSP/libnativehelper"
    "$AOSP/libcore"
    "$AOSP/system"
    "$OH/base"
    "$OH/commonlibrary/c_utils"
    "$OH/foundation"
    "$OH/third_party/bounds_checking_function"
    "$OH/third_party/json"
    "$OH/third_party/openssl"
    "$OH/third_party/selinux"
    "$OH/third_party/skia/m133"
    "$OH/third_party/zlib"
)
for directory in "${LOCAL_SOURCE_TREES[@]}" "${EXTERNAL_SOURCE_TREES[@]}"; do
    [ -d "$directory" ] && [ ! -L "$directory" ] || {
        echo "manifest scope directory is missing or a symlink: $directory" >&2
        exit 2
    }
done

verify_local_source()
{
    local arguments=()
    local path
    for path in "${SOURCE_REQUIRED_FILES[@]}"; do
        arguments+=(--required-file "$path")
    done
    for path in "${LOCAL_SOURCE_TREES[@]}"; do
        arguments+=(--required-tree "$path")
    done
    "$PYTHON" "$VERIFY_INPUT" "$SOURCE_MANIFEST" "${arguments[@]}"
}

verify_toolchain_inputs()
{
    "$PYTHON" "$VERIFY_INPUT" "$TOOLCHAIN_MANIFEST" \
        --required-tree "$TOOLCHAIN_ROOT" \
        --required-file "$CC" --required-file "$CXX" \
        --required-file "$READELF" --required-file "$NM" \
        --required-file "$BUILTINS" --required-file "$PYTHON" \
        --required-file "$AIDL" \
        --required-tree "$LIBCXX_INCLUDE"
}

verify_sysroot_inputs()
{
    "$PYTHON" "$VERIFY_INPUT" "$SYSROOT_MANIFEST" \
        --required-tree "$MUSL_ROOT" \
        --required-tree "$SYSTEM_LIB_ROOT" \
        --required-tree "$OH_GEN_ROOT" \
        --required-tree "$OPENSSL_GEN_ROOT" \
        --required-tree "$ZLIB_OBJ_ROOT"
}

verify_external_source()
{
    local arguments=()
    local path
    for path in "${EXTERNAL_SOURCE_TREES[@]}"; do
        arguments+=(--required-tree "$path")
    done
    "$PYTHON" "$VERIFY_INPUT" "$EXTERNAL_SOURCE_MANIFEST" "${arguments[@]}"
}

verify_official_prebuilt_pool()
{
    "$PYTHON" "$VERIFY_INPUT" "$OFFICIAL_PREBUILT_POOL_MANIFEST" \
        --required-tree "$OFFICIAL_SYSTEM_LIB_ROOT" \
        --required-file "$DLNS_PROVIDER"
}

verify_static_inputs()
{
    verify_local_source || return
    verify_toolchain_inputs || return
    verify_sysroot_inputs || return
    verify_external_source || return
    verify_official_prebuilt_pool || return
}

if [ -n "$OH_SERVICE_DIR" ]; then
    [ -d "$OH_SERVICE_DIR" ] && [ ! -L "$OH_SERVICE_DIR" ] || {
        echo "OH service source directory is missing or a symlink: $OH_SERVICE_DIR" >&2
        exit 2
    }
fi

umask 022
mkdir -p "$GENERATION_ROOT/meta/inputs" \
    "$GENERATION_ROOT/work/aosp" "$GENERATION_ROOT/work/adapter" \
    "$GENERATION_ROOT/work/fixtures" "$GENERATION_ROOT/objects" \
    "$GENERATION_ROOT/payload/adapter" "$GENERATION_ROOT/payload/aosp" \
    "$GENERATION_ROOT/payload/bin" "$GENERATION_ROOT/payload/oh-service"
INCOMPLETE=$GENERATION_ROOT/meta/INCOMPLETE
BUILD_LOG=$GENERATION_ROOT/meta/build.log
GATE_LOG=$GENERATION_ROOT/meta/provider_closure.gate.log
MANIFEST=$GENERATION_ROOT/meta/generation.json
GENERATED_INPUT_MANIFEST=$GENERATION_ROOT/meta/generated-inputs.sha256
BASE_COPY=$GENERATION_ROOT/meta/immutable-base
INPUT_SNAPSHOT_DIR=$GENERATION_ROOT/meta/inputs
SOURCE_SNAPSHOT=$INPUT_SNAPSHOT_DIR/source.sha256
TOOLCHAIN_SNAPSHOT=$INPUT_SNAPSHOT_DIR/toolchain.sha256
SYSROOT_SNAPSHOT=$INPUT_SNAPSHOT_DIR/sysroot.sha256
EXTERNAL_SOURCE_SNAPSHOT=$INPUT_SNAPSHOT_DIR/external-source.sha256
IMMUTABLE_BASE_SNAPSHOT=$INPUT_SNAPSHOT_DIR/immutable-base.sha256
DEPLOY_PLAN_SNAPSHOT=$INPUT_SNAPSHOT_DIR/deploy-plan.json
OFFICIAL_PREBUILT_POOL_SNAPSHOT=$INPUT_SNAPSHOT_DIR/official-prebuilt-pool.sha256
IMMUTABLE_RESOLUTION_REPORT=$GENERATION_ROOT/meta/immutable-base-resolution.json
touch "$INCOMPLETE" "$BUILD_LOG"
COMPLETED=0

finish()
{
    local rc=$?
    if [ "$rc" -eq 0 ] && [ "$COMPLETED" -eq 1 ]; then
        rm -f "$INCOMPLETE"
    else
        printf 'generation failed rc=%d\n' "$rc" >"$INCOMPLETE"
        if [ "$rc" -eq 0 ]; then
            trap - EXIT
            exit 1
        fi
    fi
}
trap finish EXIT

run_phase()
{
    local name=$1
    shift
    printf 'PHASE_BEGIN name=%s\n' "$name" | tee -a "$BUILD_LOG"
    if "$@" >>"$BUILD_LOG" 2>&1; then
        printf 'PHASE_PASS name=%s\n' "$name" | tee -a "$BUILD_LOG"
    else
        local rc=$?
        printf 'PHASE_FAIL name=%s rc=%d\n' "$name" "$rc" \
            | tee -a "$BUILD_LOG" >&2
        tail -80 "$BUILD_LOG" >&2
        return "$rc"
    fi
}

printf 'GENERATION id=%s architecture=aarch64 strict_link=true filesystem=ext4\n' \
    "$GENERATION_ID" >>"$BUILD_LOG"
run_phase all_input_coverage_before verify_static_inputs

SOURCE_BEFORE=$(sha256_file "$SOURCE_MANIFEST")
TOOLCHAIN_SHA=$(sha256_file "$TOOLCHAIN_MANIFEST")
SYSROOT_SHA=$(sha256_file "$SYSROOT_MANIFEST")
EXTERNAL_SOURCE_SHA=$(sha256_file "$EXTERNAL_SOURCE_MANIFEST")
OFFICIAL_PREBUILT_POOL_SHA=$(sha256_file "$OFFICIAL_PREBUILT_POOL_MANIFEST")
DLNS_PROVIDER_SHA=$(sha256_file "$DLNS_PROVIDER")
printf 'INPUT source=%s toolchain=%s sysroot=%s external=%s official_prebuilt_pool=%s dlns=%s\n' \
    "$SOURCE_BEFORE" "$TOOLCHAIN_SHA" "$SYSROOT_SHA" \
    "$EXTERNAL_SOURCE_SHA" "$OFFICIAL_PREBUILT_POOL_SHA" \
    "$DLNS_PROVIDER_SHA" >>"$BUILD_LOG"
printf 'OFFICIAL_PREBUILT generation=%s pool=%s manifest=%s manifest_sha256=%s loader=%s loader_sha256=%s\n' \
    "$GENERATION_ID" "$OFFICIAL_PREBUILT_POOL_ROOT" \
    "$OFFICIAL_PREBUILT_POOL_MANIFEST" "$OFFICIAL_PREBUILT_POOL_SHA" \
    "$DLNS_PROVIDER" "$DLNS_PROVIDER_SHA" >>"$BUILD_LOG"

COMMON_GENERATION_ENV=(
    BUILD_INNER_INVOKED=1
    ADAPTER_ROOT="$ROOT"
    OH_ROOT="$OH"
    AOSP_ROOT="$AOSP"
    OH_PRODUCT_NAME="$OH_PRODUCT"
    L03_A12_GENERATION_ID="$GENERATION_ID"
    L03_A12_STRICT_BUILD=1
    L03_A12_CC="$CC"
    L03_A12_CXX="$CXX"
    L03_A12_AS="$CC"
    L03_A12_READELF="$READELF"
    L03_A12_NM="$NM"
    L03_A12_BUILTINS="$BUILTINS"
    L03_A12_LIBCXX_INCLUDE="$LIBCXX_INCLUDE"
    L03_A12_OH_LINK_ROOT="$SYSTEM_LIB_ROOT"
    L03_A12_PYTHON="$PYTHON"
    L03_A12_AIDL="$AIDL"
)

run_phase backend env \
    ADAPTER_ROOT="$ROOT" \
    ANL_OUT_DIR="$GENERATION_ROOT/work/aosp" \
    ANL_FIXTURE_OUT_DIR="$GENERATION_ROOT/work/fixtures" \
    OH_CC="$CC" OH_READELF="$READELF" OH_SYSROOT="$SYSROOT" \
    OH_DLNS_PROVIDER="$DLNS_PROVIDER" \
    OH_DLNS_PROVIDER_SHA256="$DLNS_PROVIDER_SHA" \
    bash "$ROOT/build/compile_app_native_loader_arm64.sh"

run_phase aosp_profile_b env "${COMMON_GENERATION_ENV[@]}" \
    AOSP_OUT_DIR="$GENERATION_ROOT/work/aosp" \
    AOSP_OBJ_DIR="$GENERATION_ROOT/objects/aosp" \
    AOSP_BUILD_ERROR_LOG="$GENERATION_ROOT/meta/aosp_build_errors.log" \
    BUILD_NJOBS="${BUILD_NJOBS:-16}" \
    bash "$ROOT/build/inner/cross_compile_arm64.sh" --clean

verify_art64_pair()
{
    local artifact machine
    for artifact in \
        "$GENERATION_ROOT/work/aosp/libart.so" \
        "$GENERATION_ROOT/work/aosp/libart-compiler.so"
    do
        [ -f "$artifact" ] && [ ! -L "$artifact" ] || {
            echo "required same-generation ART64 artifact is missing: $artifact" >&2
            return 1
        }
        machine=$(
            "$READELF" --file-header "$artifact" |
                awk -F: '/Machine:/ { sub(/^[[:space:]]+/, "", $2); print $2 }'
        )
        [ "$machine" = "AArch64" ] || {
            echo "ART artifact is not AArch64: $artifact machine=$machine" >&2
            return 1
        }
    done
    printf 'ART64_PAIR_PASS runtime=%s compiler=%s\n' \
        "$(sha256_file "$GENERATION_ROOT/work/aosp/libart.so")" \
        "$(sha256_file "$GENERATION_ROOT/work/aosp/libart-compiler.so")"
}

run_phase art64_pair verify_art64_pair

run_phase aosp_icu_androidfw env "${COMMON_GENERATION_ENV[@]}" \
    AOSP_OUT_DIR="$GENERATION_ROOT/work/aosp" \
    MINIKIN_OBJ_DIR="$GENERATION_ROOT/objects/minikin-stack" \
    MINIKIN_BUILD_LOG="$GENERATION_ROOT/meta/minikin_build.log" \
    bash "$ROOT/build/inner/cross_compile_minikin_stack_arm64.sh" \
    --clean --only=libicuuc,libicui18n,libandroidfw

run_phase aosp_jni_extras env "${COMMON_GENERATION_ENV[@]}" \
    AOSP_OUT_DIR="$GENERATION_ROOT/work/aosp" \
    EXTRAS_OBJ_DIR="$GENERATION_ROOT/objects/jni-extras" \
    EXTRAS_BUILD_LOG="$GENERATION_ROOT/meta/extras_build.log" \
    bash "$ROOT/build/inner/cross_compile_extras_arm64.sh" --clean

run_phase thread_guard_registry env "${COMMON_GENERATION_ENV[@]}" \
    OH_SYSROOT="$SYSROOT" \
    L03_A12_OBJDUMP="$(dirname "$READELF")/llvm-objdump" \
    ADAPTER_OUT_DIR="$GENERATION_ROOT/work/adapter" \
    WLTG_OBJ_DIR="$GENERATION_ROOT/objects/thread-guard-registry" \
    bash "$ROOT/framework/native-compat/thread-guard-registry/build_arm64.sh"

run_phase adapter_bridge env "${COMMON_GENERATION_ENV[@]}" \
    AOSP_LIB_DIR="$GENERATION_ROOT/work/aosp" \
    ADAPTER_OUT_DIR="$GENERATION_ROOT/work/adapter" \
    BRIDGE_OBJ_DIR="$GENERATION_ROOT/objects/adapter-bridge" \
    bash "$ROOT/build/inner/compile_oh_adapter_bridge_arm64.sh" --clean

run_phase android_runtime env "${COMMON_GENERATION_ENV[@]}" \
    AOSP_LIB_DIR="$GENERATION_ROOT/work/aosp" \
    ADAPTER_OUT_DIR="$GENERATION_ROOT/work/adapter" \
    ANDROID_RUNTIME_BUILD_DIR="$GENERATION_ROOT/objects/android-runtime" \
    bash "$ROOT/build/inner/compile_oh_android_runtime_arm64_stage2unity.sh"

BRIDGE_ARTIFACT="$GENERATION_ROOT/work/adapter/liboh_adapter_bridge.so"
RUNTIME_ARTIFACT="$GENERATION_ROOT/work/adapter/liboh_android_runtime.so"
BRIDGE_SHA256=$(sha256_file "$BRIDGE_ARTIFACT")
RUNTIME_SHA256=$(sha256_file "$RUNTIME_ARTIFACT")
BRIDGE_BUILD_ID=$(elf_build_id "$BRIDGE_ARTIFACT")
RUNTIME_BUILD_ID=$(elf_build_id "$RUNTIME_ARTIFACT")
BRIDGE_DEPLOY_PATH=$(deploy_destination adapter/liboh_adapter_bridge.so)
RUNTIME_DEPLOY_PATH=$(deploy_destination adapter/liboh_android_runtime.so)
printf 'IDENTITY role=bridge path=%s sha256=%s build_id=%s\n' \
    "$BRIDGE_DEPLOY_PATH" "$BRIDGE_SHA256" "$BRIDGE_BUILD_ID" >>"$BUILD_LOG"
printf 'IDENTITY role=runtime path=%s sha256=%s build_id=%s\n' \
    "$RUNTIME_DEPLOY_PATH" "$RUNTIME_SHA256" "$RUNTIME_BUILD_ID" >>"$BUILD_LOG"

run_phase appspawn_arm64 env "${COMMON_GENERATION_ENV[@]}" \
    APPSPAWN_TARGET_ARCH=arm64 \
    AOSP_LIB_DIR="$GENERATION_ROOT/work/aosp" \
    ADAPTER_OUT_DIR="$GENERATION_ROOT/work/adapter" \
    WLTG_REGISTRY_LIB_DIR="$GENERATION_ROOT/work/adapter" \
    APPSPAWN_OBJ_DIR="$GENERATION_ROOT/objects/appspawn" \
    WLAR_ADAPTER_BRIDGE_PATH="$BRIDGE_DEPLOY_PATH" \
    WLAR_ADAPTER_BRIDGE_SHA256_HEX="$BRIDGE_SHA256" \
    WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX="$BRIDGE_BUILD_ID" \
    WLAR_ANDROID_RUNTIME_PATH="$RUNTIME_DEPLOY_PATH" \
    WLAR_ANDROID_RUNTIME_SHA256_HEX="$RUNTIME_SHA256" \
    WLAR_ANDROID_RUNTIME_BUILD_ID_HEX="$RUNTIME_BUILD_ID" \
    bash "$ROOT/build/inner/compile_appspawnx.sh"

copy_regular()
{
    local source=$1 destination=$2
    [ -f "$source" ] && [ ! -L "$source" ] || {
        echo "missing generation artifact: $source" >&2
        return 1
    }
    cp "$source" "$destination"
}

copy_regular "$GENERATION_ROOT/work/aosp/libapp_native_loader.so" \
    "$GENERATION_ROOT/payload/adapter/libapp_native_loader.so"
copy_regular "$GENERATION_ROOT/work/adapter/liboh_adapter_bridge.so" \
    "$GENERATION_ROOT/payload/adapter/liboh_adapter_bridge.so"
copy_regular "$GENERATION_ROOT/work/adapter/liboh_android_runtime.so" \
    "$GENERATION_ROOT/payload/adapter/liboh_android_runtime.so"
copy_regular "$GENERATION_ROOT/work/adapter/libwestlake_thread_guard_registry.so" \
    "$GENERATION_ROOT/payload/adapter/libwestlake_thread_guard_registry.so"
shopt -s nullglob
aosp_libraries=("$GENERATION_ROOT/work/aosp"/lib*.so)
[ "${#aosp_libraries[@]}" -gt 0 ] || {
    echo "generation produced no AOSP shared libraries" >&2
    exit 1
}
for source in "${aosp_libraries[@]}"; do
    library=$(basename "$source")
    if [ "$library" = libapp_native_loader.so ]; then
        continue
    fi
    copy_regular "$source" "$GENERATION_ROOT/payload/aosp/$library"
done
shopt -u nullglob
copy_regular "$GENERATION_ROOT/work/adapter/appspawn-x" \
    "$GENERATION_ROOT/payload/bin/appspawn-x"

if [ -n "$OH_SERVICE_DIR" ]; then
    printf 'OH_SERVICE_DIR source=%s\n' "$OH_SERVICE_DIR" >>"$BUILD_LOG"
    shopt -s nullglob
    oh_service_artifacts=("$OH_SERVICE_DIR"/*.z.so)
    if [ "${#oh_service_artifacts[@]}" -gt 0 ]; then
        for source in "${oh_service_artifacts[@]}"; do
            library=$(basename "$source")
            copy_regular "$source" "$GENERATION_ROOT/payload/oh-service/$library"
            oh_sha=$(sha256_file "$source")
            oh_deploy_path=$(oh_service_deploy_path "$library")
            printf 'IDENTITY role=oh_service name=%s path=%s sha256=%s\n' \
                "$library" "$oh_deploy_path" "$oh_sha" >>"$BUILD_LOG"
        done
    else
        printf 'OH_SERVICE_DIR empty\n' >>"$BUILD_LOG"
    fi
    shopt -u nullglob
fi

run_phase all_input_coverage_payload verify_static_inputs

IMMUTABLE_PROVIDER_ARGUMENTS=(
    --provider-root "/system/lib64=$OFFICIAL_SYSTEM_LIB_ROOT"
    --provider-root "/system/lib64/platformsdk=$OFFICIAL_SYSTEM_LIB_ROOT/platformsdk"
    --provider-root "/system/lib64/chipset-sdk=$OFFICIAL_SYSTEM_LIB_ROOT/chipset-sdk"
    --provider-root "/system/lib64/chipset-sdk-sp=$OFFICIAL_SYSTEM_LIB_ROOT/chipset-sdk-sp"
    --provider-root "/system/lib64/module/arkts=$OFFICIAL_SYSTEM_LIB_ROOT/module/arkts"
    --provider-root "/system/lib64/ndk=$OFFICIAL_SYSTEM_LIB_ROOT/ndk"
)
run_phase immutable_base_resolution "$PYTHON" "$RESOLVE_IMMUTABLE_BASE" \
    --payload-root "$GENERATION_ROOT/payload" \
    --pool-root "$OFFICIAL_PREBUILT_POOL_ROOT" \
    "${IMMUTABLE_PROVIDER_ARGUMENTS[@]}" \
    --loader "$DLNS_PROVIDER" \
    --expected-interpreter "$EXPECTED_INTERPRETER" \
    --readelf "$READELF" \
    --output "$BASE_COPY" \
    --report "$IMMUTABLE_RESOLUTION_REPORT"

run_phase immutable_base_manifest "$PYTHON" "$WRITE_SHA" \
    --output "$IMMUTABLE_BASE_SNAPSHOT" "$BASE_COPY"
run_phase immutable_base_coverage "$PYTHON" "$VERIFY_INPUT" \
    "$IMMUTABLE_BASE_SNAPSHOT" --required-tree "$BASE_COPY" \
    --required-file "$BASE_COPY/${EXPECTED_INTERPRETER#/}"
IMMUTABLE_BASE_SHA=$(sha256_file "$IMMUTABLE_BASE_SNAPSHOT")

run_phase deploy_plan "$PYTHON" "$WRITE_DEPLOY_PLAN" \
    --generation-id "$GENERATION_ID" \
    --payload-root "$GENERATION_ROOT/payload" \
    --image-fingerprint "$IMAGE_FINGERPRINT" \
    --expected-interpreter "$EXPECTED_INTERPRETER" \
    --filesystem-type "$FILESYSTEM_TYPE" \
    --output "$DEPLOY_PLAN_SNAPSHOT"
DEPLOY_PLAN_SHA=$(sha256_file "$DEPLOY_PLAN_SNAPSHOT")
printf 'GENERATED base=%s deploy=%s resolution=%s\n' \
    "$IMMUTABLE_BASE_SHA" "$DEPLOY_PLAN_SHA" \
    "$(sha256_file "$IMMUTABLE_RESOLUTION_REPORT")" >>"$BUILD_LOG"

verify_generated_deploy_identities()
{
    "$PYTHON" - "$DEPLOY_PLAN_SNAPSHOT" \
        "$BRIDGE_DEPLOY_PATH" "$RUNTIME_DEPLOY_PATH" <<'PY'
import json
import sys

plan_path, bridge, runtime = sys.argv[1:]
with open(plan_path, "r", encoding="utf-8") as stream:
    plan = json.load(stream)
actual = {
    entry.get("source"): entry.get("destination")
    for entry in plan.get("entries", [])
    if isinstance(entry, dict)
}
expected = {
    "adapter/liboh_adapter_bridge.so": bridge,
    "adapter/liboh_android_runtime.so": runtime,
}
if any(actual.get(source) != destination for source, destination in expected.items()):
    raise SystemExit(
        f"generated deploy identities disagree with compiled roles: "
        f"expected={expected!r} actual={actual!r}"
    )
PY
}
run_phase deploy_plan_role_identity verify_generated_deploy_identities

run_phase all_input_coverage_after verify_static_inputs
SOURCE_AFTER=$(sha256_file "$SOURCE_MANIFEST")
[ "$SOURCE_AFTER" = "$SOURCE_BEFORE" ] || {
    echo "source manifest changed during generation" >&2
    exit 1
}
[ "$(sha256_file "$TOOLCHAIN_MANIFEST")" = "$TOOLCHAIN_SHA" ] || {
    echo "toolchain manifest changed during generation" >&2
    exit 1
}
[ "$(sha256_file "$SYSROOT_MANIFEST")" = "$SYSROOT_SHA" ] || {
    echo "sysroot manifest changed during generation" >&2
    exit 1
}
[ "$(sha256_file "$EXTERNAL_SOURCE_MANIFEST")" = "$EXTERNAL_SOURCE_SHA" ] || {
    echo "external source manifest changed during generation" >&2
    exit 1
}
[ "$(sha256_file "$OFFICIAL_PREBUILT_POOL_MANIFEST")" = "$OFFICIAL_PREBUILT_POOL_SHA" ] || {
    echo "official prebuilt pool manifest changed during generation" >&2
    exit 1
}

run_phase generated_input_manifest "$PYTHON" "$WRITE_SHA" \
    --output "$GENERATED_INPUT_MANIFEST" \
    "$GENERATION_ROOT/objects" "$GENERATION_ROOT/work"
GENERATED_INPUT_SHA=$(sha256_file "$GENERATED_INPUT_MANIFEST")

snapshot_provenance()
{
    cp "$SOURCE_MANIFEST" "$SOURCE_SNAPSHOT"
    cp "$TOOLCHAIN_MANIFEST" "$TOOLCHAIN_SNAPSHOT"
    cp "$SYSROOT_MANIFEST" "$SYSROOT_SNAPSHOT"
    cp "$EXTERNAL_SOURCE_MANIFEST" "$EXTERNAL_SOURCE_SNAPSHOT"
    cp "$OFFICIAL_PREBUILT_POOL_MANIFEST" "$OFFICIAL_PREBUILT_POOL_SNAPSHOT"
}
run_phase provenance_snapshot snapshot_provenance

"$PYTHON" "$WRITE_MANIFEST" \
    --generation-id "$GENERATION_ID" \
    --artifact-root "$GENERATION_ROOT/payload" \
    --immutable-base-root "$BASE_COPY" \
    --image-fingerprint "$IMAGE_FINGERPRINT" \
    --expected-interpreter "$EXPECTED_INTERPRETER" \
    --deploy-plan "$DEPLOY_PLAN_SNAPSHOT" \
    --build-log "$BUILD_LOG" \
    --source-before "$SOURCE_BEFORE" --source-after "$SOURCE_AFTER" \
    --toolchain-manifest "$TOOLCHAIN_SHA" \
    --sysroot-manifest "$SYSROOT_SHA" \
    --external-source-manifest "$EXTERNAL_SOURCE_SHA" \
    --immutable-base-manifest "$IMMUTABLE_BASE_SHA" \
    --generated-input-manifest "$GENERATED_INPUT_SHA" \
    --output "$MANIFEST"

READELF="$READELF" "$VERIFY_CLOSURE" \
    "$MANIFEST" "$GENERATION_ROOT/payload" >"$GATE_LOG" 2>&1
grep -q "^PROVIDER_SUBGRAPH_PASS generation=$GENERATION_ID$" "$GATE_LOG"
grep -q "^DEPLOY_CLOSURE_PASS generation=$GENERATION_ID$" "$GATE_LOG"
COMPLETED=1

printf 'GENERATION_PASS id=%s manifest=%s payload=%s base=%s gate=%s\n' \
    "$GENERATION_ID" "$MANIFEST" "$GENERATION_ROOT/payload" \
    "$BASE_COPY" "$GATE_LOG"
