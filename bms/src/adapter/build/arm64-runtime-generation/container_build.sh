#!/usr/bin/env bash
# Runs only inside the locked, networkless build container. All inputs are the
# read-only project-local frozen snapshot; /out is the sole writable mount.

set -euo pipefail
IFS=$'\n\t'
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=0

F=/project/.work/arm64-runtime-generation/frozen
ADAPTER="$F/adapter"
AOSP="$F/aosp"
OH="$F/oh"
TOOL="$F/toolchain"
SYSROOT="$F/sysroot"
CC="$TOOL/bin/clang-15"
CXX="$TOOL/bin/clang-15"
READELF="$TOOL/bin/llvm-readelf"
NM="$TOOL/bin/llvm-nm"
BUILTINS="$TOOL/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"
LIBCXX_INCLUDE="$TOOL/include/c++/v1"
OH_LIB="$OH/out/wukong100/packages/phone/system/lib64"
ML="$SYSROOT/lib/aarch64-linux-ohos"
GENERATION_ID=${WESTLAKE_ARM64_RUNTIME_GENERATION_ID:?missing generation id}

for path in "$F" "$ADAPTER" "$AOSP" "$OH" "$TOOL" "$SYSROOT"; do
    case "$(realpath "$path")" in /project/*) ;; *) echo "input escaped project: $path" >&2; exit 2 ;; esac
done
for path in "$CC" "$READELF" "$NM" "$BUILTINS" "$LIBCXX_INCLUDE"; do
    [[ -e "$path" ]] || { echo "missing frozen tool input: $path" >&2; exit 2; }
done
mkdir -p /out/logs

log_command()
{
    printf '%q ' "$@" >>/out/logs/commands.txt
    printf '\n' >>/out/logs/commands.txt
}

run()
{
    log_command "$@"
    "$@"
}

build_pass()
{
    local pass=$1
    local root="/out/$pass"
    local aosp_out="$root/aosp"
    local adapter_out="$root/adapter"
    local objects="$root/objects"
    mkdir -p "$aosp_out" "$adapter_out" "$objects/app-loader" \
        "$objects/native-loader" "$objects/minikin" "$objects/bridge" "$objects/runtime"
    cp "$F/base/aosp/"*.so "$aosp_out/"

    local common=(--target=aarch64-linux-ohos --sysroot="$SYSROOT" -B"$TOOL/bin"
        -fPIC -O2 -g0 -ffile-prefix-map=/project=. -fdebug-prefix-map=/project=.
        -isystem "$SYSROOT/include/aarch64-linux-ohos" -MMD -MP)

    run "$CC" "${common[@]}" -std=c11 -fvisibility=hidden \
        -I"$ADAPTER/framework/app-native-loader/include" \
        -I"$ADAPTER/framework/native-compat/bionic-pthread-bridge/include" \
        -c "$ADAPTER/framework/app-native-loader/src/app_native_loader.c" \
        -o "$objects/app-loader/app_native_loader.o"
    run "$CC" --target=aarch64-linux-ohos --sysroot="$SYSROOT" -B"$TOOL/bin" \
        -fuse-ld=lld -shared -Wl,-z,defs -Wl,--no-allow-shlib-undefined \
        -Wl,--no-undefined -Wl,-z,now -Wl,-z,relro -Wl,--build-id=sha1 \
        -Wl,-soname,libapp_native_loader.so \
        -Wl,--version-script="$ADAPTER/framework/app-native-loader/app_native_loader.map" \
        "$objects/app-loader/app_native_loader.o" \
        "$F/immutable-base/ld-musl-aarch64.so.1" -lc -ldl -lpthread "$BUILTINS" \
        -o "$aosp_out/libapp_native_loader.so"

    local native_objects=()
    local source object
    for source in native_loader.cpp native_loader_registry.cpp system_loader.cpp; do
        object="$objects/native-loader/${source%.cpp}.o"
        run "$CXX" "${common[@]}" -nostdinc++ -isystem "$LIBCXX_INCLUDE" \
            -std=gnu++17 -fno-exceptions -fno-rtti \
            -I"$ADAPTER/framework/native-loader-oh/include" \
            -I"$ADAPTER/framework/native-loader-oh/src" \
            -I"$ADAPTER/framework/app-native-loader/include" \
            -I"$AOSP/libnativehelper/include_jni" \
            -c "$ADAPTER/framework/native-loader-oh/src/$source" -o "$object"
        native_objects+=("$object")
    done
    run "$CXX" --target=aarch64-linux-ohos --sysroot="$SYSROOT" -B"$TOOL/bin" \
        -fuse-ld=lld -shared -Wl,-z,defs -Wl,--no-allow-shlib-undefined \
        -Wl,--no-undefined -Wl,-z,now -Wl,-z,relro -Wl,--build-id=sha1 \
        -Wl,-soname,libnativeloader.so \
        -Wl,--version-script="$ADAPTER/framework/native-loader-oh/native_loader.map" \
        -L"$aosp_out" -L"$OH_LIB/chipset-sdk-sp" -L"$ML" \
        "${native_objects[@]}" -Wl,--no-as-needed -lapp_native_loader \
        -Wl,--as-needed -lc++ -lc -ldl -lpthread "$BUILTINS" \
        -o "$aosp_out/libnativeloader.so"

    env BUILD_INNER_INVOKED=1 ADAPTER_ROOT="$ADAPTER" AOSP_ROOT="$AOSP" OH_ROOT="$OH" \
        OH_PRODUCT_NAME=wukong100 L03_A12_GENERATION_ID="$GENERATION_ID" \
        L03_A12_STRICT_BUILD=1 L03_A12_CC="$CC" L03_A12_CXX="$CXX" \
        L03_A12_NM="$NM" L03_A12_READELF="$READELF" \
        L03_A12_LIBCXX_INCLUDE="$LIBCXX_INCLUDE" AOSP_OUT_DIR="$aosp_out" \
        MINIKIN_OBJ_DIR="$objects/minikin" MINIKIN_BUILD_LOG="$root/minikin.log" \
        bash -x "$ADAPTER/build/inner/cross_compile_minikin_stack_arm64.sh" \
        --clean --only=libicuuc,libandroidfw

    env BUILD_INNER_INVOKED=1 ADAPTER_ROOT="$ADAPTER" AOSP_ROOT="$AOSP" OH_ROOT="$OH" \
        OH_PRODUCT_NAME=wukong100 L03_A12_GENERATION_ID="$GENERATION_ID" \
        L03_A12_STRICT_BUILD=1 L03_A12_CXX="$CXX" L03_A12_READELF="$READELF" \
        L03_A12_BUILTINS="$BUILTINS" L03_A12_LIBCXX_INCLUDE="$LIBCXX_INCLUDE" \
        L03_A12_OH_LINK_ROOT="$OH_LIB" AOSP_LIB_DIR="$aosp_out" \
        ADAPTER_OUT_DIR="$adapter_out" BRIDGE_OBJ_DIR="$objects/bridge" \
        bash -x "$ADAPTER/build/inner/compile_oh_adapter_bridge_arm64.sh" --clean

    env BUILD_INNER_INVOKED=1 ADAPTER_ROOT="$ADAPTER" AOSP_ROOT="$AOSP" OH_ROOT="$OH" \
        OH_PRODUCT_NAME=wukong100 L03_A12_GENERATION_ID="$GENERATION_ID" \
        L03_A12_STRICT_BUILD=1 L03_A12_CXX="$CXX" L03_A12_READELF="$READELF" \
        L03_A12_NM="$NM" L03_A12_AIDL="$F/tools/aidl" L03_A12_PYTHON=/usr/bin/python3 \
        L03_A12_LIBCXX_INCLUDE="$LIBCXX_INCLUDE" AOSP_LIB_DIR="$aosp_out" \
        ADAPTER_OUT_DIR="$adapter_out" ANDROID_RUNTIME_BUILD_DIR="$objects/runtime" \
        bash -x "$ADAPTER/build/inner/compile_oh_android_runtime_arm64_stage2unity.sh"

    mkdir -p "$root/payload/adapter" "$root/payload/aosp"
    cp "$adapter_out/liboh_adapter_bridge.so" "$root/payload/adapter/"
    cp "$adapter_out/liboh_android_runtime.so" "$root/payload/adapter/"
    cp "$aosp_out/libapp_native_loader.so" "$root/payload/adapter/"
    cp "$aosp_out/libnativeloader.so" "$root/payload/aosp/"
    find "$objects" -type f -name '*.d' -print0 | sort -z | xargs -0 cat >"$root/depfiles.txt"
}

: >/out/logs/commands.txt
build_pass pass1 > /out/logs/pass1.log 2>&1
build_pass pass2 > /out/logs/pass2.log 2>&1

for relative in \
    payload/adapter/liboh_adapter_bridge.so \
    payload/adapter/liboh_android_runtime.so \
    payload/adapter/libapp_native_loader.so \
    payload/aosp/libnativeloader.so
do
    cmp "/out/pass1/$relative" "/out/pass2/$relative"
done

/usr/bin/python3 "$F/config/verify_generation.py" \
    --generation-id "$GENERATION_ID" --frozen "$F" --build-root /out
