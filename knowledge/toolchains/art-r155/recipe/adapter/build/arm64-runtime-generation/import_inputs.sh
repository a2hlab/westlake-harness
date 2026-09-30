#!/usr/bin/env bash
# Freeze the exact ARM64 bridge/runtime build closure into this project.
# This is the only phase allowed to read an external OH/AOSP/ROM origin.
#
# Origins are explicit inputs, never workstation defaults. A deleted default
# path must fail before copying anything instead of silently selecting a
# historical generation.

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
ADAPTER_ROOT="$PROJECT_ROOT/adapter"
GENERATION_ROOT=${WESTLAKE_ARM64_RUNTIME_ROOT:-$PROJECT_ROOT/.work/arm64-runtime-generation}
FROZEN="$GENERATION_ROOT/frozen"
MAPPINGS="$GENERATION_ROOT/origin-mappings.tsv"
PROVENANCE="$GENERATION_ROOT/provenance.tsv"
LOCAL_HASHES="$GENERATION_ROOT/frozen.sha256"

if [[ ${1:-} == --refresh ]]; then
    if [[ -e "$GENERATION_ROOT" ]]; then
        chmod -R u+w "$GENERATION_ROOT"
        rm -rf -- "$GENERATION_ROOT"
    fi
elif [[ $# -ne 0 ]]; then
    echo "usage: $0 [--refresh]" >&2
    exit 2
elif [[ -e "$GENERATION_ROOT" ]]; then
    echo "ERROR: frozen generation already exists; use --refresh" >&2
    exit 2
fi

case "$GENERATION_ROOT" in
    "$PROJECT_ROOT"/.work/*) ;;
    *) echo "ERROR: generation root must be project-local .work" >&2; exit 2 ;;
esac

require_origin()
{
    local name=$1 value=${!1:-}
    [[ -n "$value" ]] || {
        echo "ERROR: $name is required; source/build/image origins must be explicit" >&2
        exit 2
    }
    printf '%s\n' "$value"
}

OH_ORIGIN=$(require_origin WESTLAKE_OH_ORIGIN)
AOSP_ORIGIN=$(require_origin WESTLAKE_AOSP_ORIGIN)
ROM_ORIGIN=$(require_origin WESTLAKE_ROM_ORIGIN)
BASE_ORIGIN="$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/frozen/runtime_provider/provider-v12/providers"
COMPAT_ORIGIN="$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/frozen/runtime_provider/libraries/generated/libbionic_compat.so"
TOOL_ORIGIN=$(require_origin WESTLAKE_TOOLCHAIN_ORIGIN)
SYSROOT_ORIGIN=$(require_origin WESTLAKE_SYSROOT_ORIGIN)
LOADER_ORIGIN=$(require_origin WESTLAKE_LOADER_ORIGIN)
AIDL_ORIGIN=$(require_origin WESTLAKE_AIDL_ORIGIN)

for directory in "$OH_ORIGIN" "$AOSP_ORIGIN" "$ROM_ORIGIN/lib64" \
                 "$BASE_ORIGIN" "$TOOL_ORIGIN" "$SYSROOT_ORIGIN"; do
    [[ -d "$directory" ]] || { echo "ERROR: missing origin directory: $directory" >&2; exit 1; }
done
for file in "$COMPAT_ORIGIN" "$LOADER_ORIGIN" "$AIDL_ORIGIN"; do
    [[ -f "$file" ]] || { echo "ERROR: missing origin file: $file" >&2; exit 1; }
done

mkdir -p "$FROZEN" "$GENERATION_ROOT"
: >"$MAPPINGS"
export COPYFILE_DISABLE=1

copy_file()
{
    local kind=$1 origin=$2 relative=$3 deployability=${4:-BUILD_INPUT}
    local destination="$FROZEN/$relative"
    [[ -f "$origin" ]] || { echo "ERROR: missing origin file: $origin" >&2; exit 1; }
    mkdir -p "$(dirname "$destination")"
    cp -pL "$origin" "$destination"
    printf '%s\t%s\t%s\t%s\n' "$kind" "$relative" "$origin" "$deployability" >>"$MAPPINGS"
}

copy_tree()
{
    local kind=$1 origin=$2 relative=$3 deployability=${4:-BUILD_INPUT}
    local destination="$FROZEN/$relative"
    [[ -d "$origin" ]] || { echo "ERROR: missing origin directory: $origin" >&2; exit 1; }
    mkdir -p "$destination"
    # Mounted source snapshots can retain a .git file/symlink whose target is
    # intentionally absent from the export.  Git metadata is not a compiler
    # input; following it would make a valid source snapshot fail to freeze.
    # Preserve source symlinks: relative links remain valid once their source
    # tree is copied under the same frozen root. Do not dereference them here,
    # because an exported repository's intentionally dangling `.git` link
    # would otherwise make the copy fail before exclusion takes effect.
    rsync -a --exclude='.git' -- "$origin/" "$destination/"
    find "$destination" -type f -print | LC_ALL=C sort | while IFS= read -r file; do
        local leaf=${file#"$destination"/}
        printf '%s\t%s/%s\t%s/%s\t%s\n' \
            "$kind" "$relative" "$leaf" "$origin" "$leaf" "$deployability" >>"$MAPPINGS"
    done
}

copy_tree_if_present()
{
    local kind=$1 origin=$2 relative=$3 deployability=${4:-BUILD_INPUT}
    [[ -d "$origin" ]] || return 0
    copy_tree "$kind" "$origin" "$relative" "$deployability"
}

# Exact project-owned translation units, headers, policies, and build recipes.
for relative in \
    framework/android-runtime \
    framework/core/jni \
    framework/activity/jni \
    framework/window/jni \
    framework/surface/jni \
    framework/broadcast/jni \
    framework/contentprovider/jni \
    framework/package-manager/jni \
    framework/native-loader-oh \
    framework/app-native-loader \
    framework/native-compat/bionic-pthread-bridge \
    framework/appspawn-x/bionic_compat/include \
    third_party/aosp_raw \
    build/oh_headers_631_overlay
do
    copy_tree source "$ADAPTER_ROOT/$relative" "adapter/$relative"
done
copy_file source "$ADAPTER_ROOT/framework/jni/BUILD.gn" adapter/framework/jni/BUILD.gn
for relative in \
    build/inner/compile_oh_adapter_bridge_arm64.sh \
    build/inner/compile_oh_android_runtime_arm64_stage2unity.sh \
    build/inner/cross_compile_minikin_stack_arm64.sh \
    build/inner/oh_adapter_bridge.ninja.template
do
    copy_file recipe "$ADAPTER_ROOT/$relative" "adapter/$relative" NEVER_DEPLOY_RECIPE
done

# Project-local pinned compiler, libc++, resource headers, builtins and sysroot.
copy_tree tool "$TOOL_ORIGIN" toolchain NEVER_DEPLOY_TOOL
copy_file tool "$TOOL_ORIGIN/bin/llvm-nm" \
    toolchain/bin/llvm-nm NEVER_DEPLOY_TOOL
copy_tree sysroot "$SYSROOT_ORIGIN" sysroot
copy_tree sysroot "$SYSROOT_ORIGIN" oh/out/wukong100/obj/third_party/musl/usr

# Exact target image provider tree. Relative symlinks are dereferenced so every
# link input is a regular project-local file. The same bytes are the immutable
# provider base used by the recursive closure verifier.
copy_tree immutable_base "$ROM_ORIGIN/lib64" \
    oh/out/wukong100/packages/phone/system/lib64 DEPLOYABLE_IMMUTABLE_BASE
copy_file immutable_base "$LOADER_ORIGIN" immutable-base/ld-musl-aarch64.so.1 \
    DEPLOYABLE_IMMUTABLE_BASE

# Certified AOSP provider base. Four roots in this task are rebuilt and replace
# any old copies; do not import old NativeLoader/app-loader artifacts.
mkdir -p "$FROZEN/base/aosp"
for provider in "$BASE_ORIGIN"/*.so; do
    case "$(basename "$provider")" in
        libnativeloader.so|libapp_native_loader.so) continue ;;
    esac
    copy_file provider "$provider" "base/aosp/$(basename "$provider")" CERTIFIED_BASE_PROVIDER
done
copy_file provider "$COMPAT_ORIGIN" base/aosp/libbionic_compat.so CERTIFIED_BASE_PROVIDER

# AOSP source/header closure used by current native-loader, ICU, androidfw and
# liboh_android_runtime recipes.
for relative in \
    libnativehelper \
    system/logging/liblog/include \
    system/libbase/include \
    system/core/include \
    system/core/libcutils/include \
    system/core/libutils/include \
    system/libziparchive/include \
    system/incremental_delivery/incfs/util \
    external/icu/icu4c/source/common \
    external/icu/icu4c/source/stubdata \
    external/fmtlib/include \
    external/zlib \
    frameworks/base/libs/androidfw \
    frameworks/base/libs/hwui/apex/include \
    frameworks/base/libs/hwui/jni \
    frameworks/base/core/jni \
    frameworks/native/include \
    frameworks/native/libs/input \
    frameworks/native/libs/gui/include \
    frameworks/native/libs/ui/include \
    frameworks/native/libs/math/include \
    frameworks/native/libs/arect/include \
    bionic/libc/kernel/uapi/linux
do
    copy_tree source "$AOSP_ORIGIN/$relative" "aosp/$relative"
done
copy_file generator "$AOSP_ORIGIN/system/core/toolbox/generate-input.h-labels.py" \
    aosp/system/core/toolbox/generate-input.h-labels.py NEVER_DEPLOY_TOOL
copy_file generator "$AIDL_ORIGIN" \
    tools/aidl NEVER_DEPLOY_TOOL

# OH header closure used by the bridge. These are selected interface/source
# roots, not a mount of the external tree.
for relative in \
    base/hiviewdfx/hilog/interfaces/native/innerkits/include \
    base/hiviewdfx/hitrace/interfaces/native/innerkits/include \
    base/security/access_token/interfaces/innerkits/accesstoken/include \
    base/notification/common_event_service/interfaces/inner_api \
    base/notification/common_event_service/frameworks/core/include \
    base/startup/init/interfaces/innerkits/include \
    base/startup/init/services/param/base/include \
    commonlibrary/c_utils/base/include \
    foundation/ability/ability_runtime/interfaces \
    foundation/ability/ability_runtime/services/abilitymgr/include \
    foundation/ability/ability_base/interfaces \
    foundation/graphic/graphic_2d/interfaces \
    foundation/graphic/graphic_2d/rosen/modules/render_service_client/core \
    foundation/graphic/graphic_2d/rosen/modules/render_service_base \
    foundation/graphic/graphic_2d/rosen/modules/2d_graphics \
    foundation/graphic/graphic_2d/rosen/modules/animation/window_animation/include \
    foundation/graphic/graphic_2d/rosen/modules/platform \
    foundation/graphic/graphic_2d/utils/color_manager/export \
    foundation/graphic/graphic_surface/interfaces \
    foundation/window/window_manager/interfaces \
    foundation/window/window_manager/window_scene \
    foundation/window/window_manager/wm/include \
    foundation/window/window_manager/wmserver/include \
    foundation/distributeddatamgr/data_share/interfaces \
    foundation/distributeddatamgr/relational_store/interfaces \
    foundation/multimodalinput/input/util/common/include \
    foundation/multimodalinput/input/interfaces/native/innerkits \
    foundation/communication/ipc/interfaces \
    foundation/bundlemanager/bundle_framework/interfaces \
    foundation/bundlemanager/bundle_framework/services/bundlemgr/include \
    foundation/systemabilitymgr/samgr/interfaces \
    foundation/systemabilitymgr/safwk/interfaces \
    third_party/bounds_checking_function/include \
    third_party/json/include \
    third_party/openssl/include \
    third_party/zlib \
    third_party/skia/m133
do
    copy_tree_if_present header "$OH_ORIGIN/$relative" "oh/$relative"
done

# Freeze the build/verifier programs after all product source snapshots.
for name in container_build.sh verify_generation.py write_frozen_provenance.py; do
    copy_file config "$SCRIPT_DIR/$name" "config/$name" NEVER_DEPLOY_CONFIG
done

python3 "$SCRIPT_DIR/write_frozen_provenance.py" \
    --mappings "$MAPPINGS" \
    --frozen "$FROZEN" \
    --provenance "$PROVENANCE" \
    --local-hashes "$LOCAL_HASHES"

chmod +x "$FROZEN/toolchain/bin/"* "$FROZEN/tools/aidl" "$FROZEN/config/container_build.sh"
chmod -R a-w "$FROZEN"
echo "FROZEN_INPUTS_PASS root=$FROZEN files=$(find "$FROZEN" -type f | wc -l | tr -d ' ')"
