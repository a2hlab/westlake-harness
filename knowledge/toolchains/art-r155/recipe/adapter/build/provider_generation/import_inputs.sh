#!/usr/bin/env bash
# Freeze the exact source/header/sysroot/tool inputs used by the ARM64
# Bionic/AOSP provider producer below the current project.  This is the only
# phase allowed to read the historical AOSP/OH origins.  The build phase never
# mounts or names either origin.

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
GENERATION_ID=${WESTLAKE_PROVIDER_GENERATION_ID:-provider-inputs-v1}
GENERATION_ROOT=${WESTLAKE_PROVIDER_GENERATION_ROOT:-$PROJECT_ROOT/.work/bionic-musl-provider/$GENERATION_ID}

case "$GENERATION_ID" in
    *[!A-Za-z0-9._-]*|'')
        echo "ERROR: unsafe generation id: $GENERATION_ID" >&2
        exit 2
        ;;
esac
case "$GENERATION_ROOT" in
    "$PROJECT_ROOT"/.work/bionic-musl-provider/*) ;;
    *) echo "ERROR: generation root must stay below the current project" >&2; exit 2 ;;
esac
if [[ -e "$GENERATION_ROOT" || -L "$GENERATION_ROOT" ]]; then
    echo "ERROR: immutable generation root already exists: $GENERATION_ROOT" >&2
    exit 2
fi

AOSP_ORIGIN=${WESTLAKE_AOSP_ORIGIN:-/opt/10.Project/16-WestLake/16.12-HanBing/home/HanBingChen/aosp}
OH_ORIGIN=${WESTLAKE_OH_ORIGIN:-/opt/10.Project/16-WestLake/16.12-HanBing/oh}
TOOLCHAIN_ORIGIN="$OH_ORIGIN/prebuilts/clang/ohos/linux-x86_64/llvm"
OH_OUT_ORIGIN="$OH_ORIGIN/out/wukong100"

FROZEN="$GENERATION_ROOT/frozen"
MAPPINGS="$GENERATION_ROOT/provenance.tsv"
HASHES="$GENERATION_ROOT/frozen.sha256"
mkdir -p "$FROZEN" "$GENERATION_ROOT/evidence"
: >"$MAPPINGS"

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
    local kind=$1 origin=$2 relative=$3
    local destination="$FROZEN/$relative"
    require_file "$origin"
    mkdir -p "$(dirname "$destination")"
    cp -pL "$origin" "$destination"
    printf '%s\t%s\t%s\n' "$kind" "$relative" "$origin" >>"$MAPPINGS"
}

copy_tree()
{
    local kind=$1 origin=$2 relative=$3
    local destination="$FROZEN/$relative"
    require_dir "$origin"
    mkdir -p "$destination"
    cp -R -L "$origin/." "$destination/"
    find "$destination" -type f -print | LC_ALL=C sort | while IFS= read -r file; do
        local suffix=${file#"$destination"/}
        printf '%s\t%s/%s\t%s/%s\n' "$kind" "$relative" "$suffix" "$origin" "$suffix" >>"$MAPPINGS"
    done
}

# Some AOSP public include aggregators contain optional/dangling compatibility
# symlinks.  Do not let them escape or make the snapshot appear complete.
# Copy physical files plus only symlinks whose exact targets exist; record each
# absent optional target explicitly.  A later compile that really needs one
# will then fail closed instead of reading it from the origin.
copy_tree_existing_links()
{
    local kind=$1 origin=$2 relative=$3
    local destination="$FROZEN/$relative"
    require_dir "$origin"
    mkdir -p "$destination"
    find "$origin" -type f -print0 | while IFS= read -r -d '' file; do
        local suffix=${file#"$origin"/}
        mkdir -p "$(dirname "$destination/$suffix")"
        cp -p "$file" "$destination/$suffix"
        printf '%s\t%s/%s\t%s\n' "$kind" "$relative" "$suffix" "$file" >>"$MAPPINGS"
    done
    find "$origin" -type l -print0 | while IFS= read -r -d '' link; do
        local suffix=${link#"$origin"/}
        if [[ -f "$link" ]]; then
            mkdir -p "$(dirname "$destination/$suffix")"
            cp -pL "$link" "$destination/$suffix"
            printf '%s-resolved-link\t%s/%s\t%s\n' \
                "$kind" "$relative" "$suffix" "$link" >>"$MAPPINGS"
        elif [[ -d "$link" ]]; then
            mkdir -p "$destination/$suffix"
            cp -R -L "$link/." "$destination/$suffix/"
            find "$destination/$suffix" -type f -print | LC_ALL=C sort \
                | while IFS= read -r resolved; do
                    local nested=${resolved#"$destination/$suffix"/}
                    printf '%s-resolved-link\t%s/%s/%s\t%s/%s\n' \
                        "$kind" "$relative" "$suffix" "$nested" "$link" "$nested" \
                        >>"$MAPPINGS"
                done
        else
            printf 'omitted-dangling-link\t%s/%s\t%s -> %s\n' \
                "$relative" "$suffix" "$link" "$(readlink "$link")" >>"$MAPPINGS"
        fi
    done
}

# AOSP source closure consumed by cross_compile_arm64.sh.  Broad compile-time
# globs (ART runtime, VIXL, ziparchive and unwindstack) are copied as complete
# local subtrees so a later source addition cannot escape through an origin.
copy_tree source "$AOSP_ORIGIN/art" aosp/art
for tree in cpu_features dlmalloc fmtlib lz4 lzma tinyxml2 vixl zlib; do
    copy_tree source "$AOSP_ORIGIN/external/$tree" "aosp/external/$tree"
done
copy_tree source "$AOSP_ORIGIN/external/rust/crates/rustc-demangle-capi" \
    aosp/external/rust/crates/rustc-demangle-capi
copy_tree header "$AOSP_ORIGIN/external/googletest/googletest/include" \
    aosp/external/googletest/googletest/include
copy_tree_existing_links header "$AOSP_ORIGIN/frameworks/native/include" \
    aosp/frameworks/native/include
copy_tree source "$AOSP_ORIGIN/libnativehelper" aosp/libnativehelper
copy_tree source "$AOSP_ORIGIN/system/core" aosp/system/core
copy_tree header "$AOSP_ORIGIN/system/extras/libprocinfo/include" \
    aosp/system/extras/libprocinfo/include
copy_tree source "$AOSP_ORIGIN/system/libbase" aosp/system/libbase
copy_tree source "$AOSP_ORIGIN/system/libziparchive" aosp/system/libziparchive
copy_tree source "$AOSP_ORIGIN/system/logging/liblog" aosp/system/logging/liblog
copy_tree source "$AOSP_ORIGIN/system/unwinding" aosp/system/unwinding

# Exact OH target ABI inputs.  The sysroot and link providers are bytes, not
# substitutes generated from host headers.
copy_tree header "$OH_ORIGIN/base/startup/init/interfaces/innerkits/include/syspara" \
    oh/base/startup/init/interfaces/innerkits/include/syspara
copy_tree sysroot "$OH_OUT_ORIGIN/obj/third_party/musl" \
    oh/out/wukong100/obj/third_party/musl
copy_tree library "$OH_OUT_ORIGIN/packages/phone/system/lib64/platformsdk" \
    oh/out/wukong100/packages/phone/system/lib64/platformsdk
copy_tree library "$OH_OUT_ORIGIN/packages/phone/system/lib64/ndk" \
    oh/out/wukong100/packages/phone/system/lib64/ndk

# The historical OH output directory above contains only EGL/GLES link files.
# Freeze the exact 5EAB5 provider bytes already acquired into this project as
# non-deployable link aliases.  Runtime identity remains their embedded SONAME;
# the aliases exist only so the strict producer can resolve typed OH edges.
FIXEDPOINT_PROVIDERS="$PROJECT_ROOT/adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-provider-fixedpoint-r2/frozen/providers"
copy_file library "$FIXEDPOINT_PROVIDERS/system__lib64__chipset-sdk-sp__libbegetutil.z.so" \
    oh/out/wukong100/packages/phone/system/lib64/platformsdk/libbegetutil.z.so
copy_file library "$FIXEDPOINT_PROVIDERS/system__lib64__chipset-sdk__libhilog.so" \
    oh/out/wukong100/packages/phone/system/lib64/platformsdk/libhilog.so
copy_file library "$FIXEDPOINT_PROVIDERS/system__lib64__chipset-sdk-sp__libshared_libz.z.so" \
    oh/out/wukong100/packages/phone/system/lib64/platformsdk/libz.so

# Linux x86_64 OH compiler closure.  Ubuntu loader/runtime libraries are
# supplied only by the separately locked, network-disabled container image.
for tool in clang clang++ clang-15 ld.lld lld llvm-nm llvm-readelf llvm-readobj; do
    copy_file tool "$TOOLCHAIN_ORIGIN/bin/$tool" "oh/toolchain/bin/$tool"
done
copy_tree tool "$TOOLCHAIN_ORIGIN/include/libcxx-ohos/include/c++/v1" \
    oh/toolchain/include/c++/v1
copy_tree tool "$TOOLCHAIN_ORIGIN/lib/clang/15.0.4" oh/toolchain/lib/clang/15.0.4
copy_tree tool "$TOOLCHAIN_ORIGIN/lib/aarch64-linux-ohos" \
    oh/toolchain/lib/aarch64-linux-ohos
copy_file tool "$TOOLCHAIN_ORIGIN/lib/libxml2.so.2.14.0" \
    oh/toolchain/runtime/libxml2.so.16

# Project-owned producer and boundary sources are snapshotted as generation
# inputs; the container never reads the live worktree.
copy_file source "$PROJECT_ROOT/adapter/build/inner/cross_compile_arm64.sh" \
    adapter/build/inner/cross_compile_arm64.sh
copy_file source "$PROJECT_ROOT/adapter/build/compile_app_native_loader_arm64.sh" \
    adapter/build/compile_app_native_loader_arm64.sh
copy_tree source "$PROJECT_ROOT/adapter/build/compat" adapter/build/compat
copy_tree source "$PROJECT_ROOT/adapter/framework/appspawn-x/bionic_compat" \
    adapter/framework/appspawn-x/bionic_compat
copy_tree source "$PROJECT_ROOT/adapter/framework/native-loader-oh" \
    adapter/framework/native-loader-oh
copy_tree source "$PROJECT_ROOT/adapter/framework/app-native-loader" \
    adapter/framework/app-native-loader
copy_tree source "$PROJECT_ROOT/adapter/framework/art-palette-oh" \
    adapter/framework/art-palette-oh
copy_file source "$PROJECT_ROOT/adapter/framework/core/jni/android_log_hilog_bridge.cpp" \
    adapter/framework/core/jni/android_log_hilog_bridge.cpp
copy_file source "$SCRIPT_DIR/container_build.sh" adapter/build/provider_generation/container_build.sh

# Exact loader provider used to build libapp_native_loader.so.
LOADER_SOURCE="$PROJECT_ROOT/adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-provider-fixedpoint-r2/frozen/providers/system__lib__ld-musl-aarch64.so.1"
copy_file library "$LOADER_SOURCE" providers/ld-musl-aarch64.so.1

if find "$FROZEN" -type l -print -quit | grep -q .; then
    echo "ERROR: frozen provider closure contains a symlink" >&2
    exit 1
fi

(cd "$FROZEN" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256) >"$HASHES"
chmod -R a-w "$FROZEN"
printf 'generation_id=%s\nfiles=%s\nexternal_origins_consumed_by_build=false\n' \
    "$GENERATION_ID" "$(wc -l <"$HASHES" | tr -d ' ')" \
    >"$GENERATION_ROOT/import-result.env"

echo "PASS provider inputs frozen below current project: $GENERATION_ROOT"
