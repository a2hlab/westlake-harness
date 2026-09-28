#!/usr/bin/env bash
#
# Build the L02.A01 package-boundary verifier/parser as one strict AArch64
# OpenHarmony shared library. This producer is deliberately package-only:
# it does not build or consume ART, appspawn-x, BCP jars, boot images, or an
# OpenHarmony image.
#
# Required:
#   ADAPTER_ROOT      canonical adapter source snapshot
#   OH_ROOT           complete OH 6.1.0.31 source/output root
#   GENERATION_ROOT   fresh output root for this generation
#
# Optional:
#   BUILD_JOBS        parallel compiler jobs (defaults to host CPU count)

set -euo pipefail

require_absolute_dir()
{
    local name="$1"
    local value="$2"
    if [[ -z "$value" || "$value" != /* || ! -d "$value" ]]; then
        echo "ERROR: $name must name an existing absolute directory: $value" >&2
        exit 2
    fi
}

: "${ADAPTER_ROOT:?ADAPTER_ROOT is required}"
: "${OH_ROOT:?OH_ROOT is required}"
: "${GENERATION_ROOT:?GENERATION_ROOT is required}"

require_absolute_dir ADAPTER_ROOT "$ADAPTER_ROOT"
require_absolute_dir OH_ROOT "$OH_ROOT"

if [[ "$GENERATION_ROOT" != /* ]]; then
    echo "ERROR: GENERATION_ROOT must be absolute: $GENERATION_ROOT" >&2
    exit 2
fi

OH_OUT="$OH_ROOT/out/wukong100"
SYSROOT="$OH_OUT/obj/third_party/musl/usr"
MUSL_LIB="$SYSROOT/lib/aarch64-linux-ohos"
SYSTEM_LIB64="$OH_OUT/packages/phone/system/lib64"
PLATFORMSDK_LIB="$SYSTEM_LIB64/platformsdk"
CHIPSET_SP_LIB="$SYSTEM_LIB64/chipset-sdk-sp"
TOOLCHAIN="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm"
CXX="$TOOLCHAIN/bin/clang++"
CC="$TOOLCHAIN/bin/clang"
READELF="$TOOLCHAIN/bin/llvm-readelf"
BUILTINS="$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"
JNI="$ADAPTER_ROOT/framework/package-manager/jni"
PACKAGE_MANAGER="$ADAPTER_ROOT/framework/package-manager"
COMPAT_INCLUDE="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"
MINIZIP="$OH_ROOT/third_party/zlib/contrib/minizip"
ZLIB="$OH_ROOT/third_party/zlib"

for path in "$OH_OUT" "$SYSROOT" "$MUSL_LIB" "$SYSTEM_LIB64" \
    "$PLATFORMSDK_LIB" "$CHIPSET_SP_LIB" "$TOOLCHAIN" "$JNI" \
    "$COMPAT_INCLUDE" "$MINIZIP"; do
    require_absolute_dir INPUT_DIR "$path"
done
for path in "$CXX" "$CC" "$READELF" "$BUILTINS"; do
    if [[ ! -f "$path" || ! -x "$path" && "$path" != "$BUILTINS" ]]; then
        echo "ERROR: required tool/input missing: $path" >&2
        exit 2
    fi
done

if [[ -e "$GENERATION_ROOT" ]]; then
    echo "ERROR: GENERATION_ROOT already exists; refusing mixed/replayed output: $GENERATION_ROOT" >&2
    exit 2
fi

BUILD_JOBS="${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}"
if [[ ! "$BUILD_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: BUILD_JOBS must be a positive integer: $BUILD_JOBS" >&2
    exit 2
fi

OBJ_DIR="$GENERATION_ROOT/obj/libapk_installer"
LOG_DIR="$GENERATION_ROOT/logs/libapk_installer"
ARTIFACT_DIR="$GENERATION_ROOT/artifacts"
META_DIR="$GENERATION_ROOT/meta"
mkdir -p "$OBJ_DIR" "$LOG_DIR" "$ARTIFACT_DIR" "$META_DIR"

CPP_SOURCES=(
    "$JNI/apk_manifest_parser.cpp"
    "$JNI/axml_parser.cpp"
    "$JNI/apk_installer.cpp"
    "$JNI/arsc_resolver.cpp"
    "$JNI/apk_verify_result.cpp"
    "$JNI/apk_verifier_client.cpp"
    "$JNI/apk_signature_verifier.cpp"
    "$PACKAGE_MANAGER/package_transaction/src/package_transaction_v1.cpp"
    "$PACKAGE_MANAGER/signing_metadata/src/signing_metadata_v1.cpp"
    "$JNI/game_install_plan_v1.cpp"
    "$JNI/oh_adapter_install_apk_c_entry.cpp"
)
C_SOURCES=(
    "$PACKAGE_MANAGER/install_plan/src/sha256.c"
    "$MINIZIP/unzip.c"
    "$MINIZIP/zip.c"
    "$MINIZIP/ioapi.c"
)
SOURCE_HEADERS=(
    "$JNI/apk_installer.h"
    "$JNI/apk_manifest_parser.h"
    "$JNI/arsc_resolver.h"
    "$JNI/axml_parser.h"
    "$JNI/apk_verify_result.h"
    "$JNI/apk_verifier_client.h"
    "$JNI/apk_signature_verifier.h"
    "$PACKAGE_MANAGER/install_plan/include/sha256.h"
    "$PACKAGE_MANAGER/package_transaction/include/package_transaction_v1.h"
    "$PACKAGE_MANAGER/signing_metadata/include/signing_metadata_v1.h"
    "$JNI/apk_verified_session_c_api.h"
    "$JNI/game_install_plan_v1.h"
    "$JNI/launcher_activity.h"
    "$JNI/native_payload_inspector.h"
    "$JNI/template_entry_hap.h"
    "$COMPAT_INCLUDE/libcxx_compat.h"
)

for path in "${CPP_SOURCES[@]}" "${C_SOURCES[@]}" "${SOURCE_HEADERS[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: source input missing: $path" >&2
        exit 2
    fi
done

COMMON_FLAGS=(
    --target=aarch64-linux-ohos
    "--sysroot=$SYSROOT"
    "-I$SYSROOT/include/aarch64-linux-ohos"
    -fPIC
    -O2
    -flto=thin
    -fsanitize=cfi
    -fsanitize-cfi-cross-dso
    -fvisibility=default
    -D__OHOS__
    -Wall
    -Wextra
    -Werror
)
CPP_FLAGS=(
    "${COMMON_FLAGS[@]}"
    -std=c++17
    -include
    "$COMPAT_INCLUDE/libcxx_compat.h"
    "-I$COMPAT_INCLUDE"
    "-I$JNI"
    "-I$PACKAGE_MANAGER/install_plan/include"
    "-I$PACKAGE_MANAGER/package_transaction/include"
    "-I$PACKAGE_MANAGER/signing_metadata/include"
    "-I$MINIZIP"
    "-I$ZLIB"
    "-I$OH_ROOT/third_party/openssl/include"
    "-I$OH_ROOT/third_party/json/single_include"
    "-I$OH_OUT/obj/third_party/openssl/build_all_generated/include"
    "-I$OH_ROOT/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
    "-I$OH_ROOT/commonlibrary/c_utils/base/include"
)
C_FLAGS=(
    "${COMMON_FLAGS[@]}"
    "-I$PACKAGE_MANAGER/install_plan/include"
    "-I$MINIZIP"
    "-I$ZLIB"
)

printf 'target=OH6.1.0.31/wukong100/AArch64\n' > "$META_DIR/target.txt"
printf 'build_jobs=%s\n' "$BUILD_JOBS" >> "$META_DIR/target.txt"
"$CXX" --version > "$META_DIR/compiler.version.txt"
sha256sum "$CXX" "$CC" "$READELF" "$BUILTINS" > "$META_DIR/toolchain.sha256"
sha256sum "${CPP_SOURCES[@]}" "${C_SOURCES[@]}" "${SOURCE_HEADERS[@]}" \
    > "$META_DIR/source-inputs.sha256"

pids=()
names=()
for source in "${CPP_SOURCES[@]}"; do
    name="$(basename "${source%.cpp}")"
    "$CXX" "${CPP_FLAGS[@]}" -c "$source" -o "$OBJ_DIR/$name.o" \
        > "$LOG_DIR/$name.log" 2>&1 &
    pids+=("$!")
    names+=("$name")
done
for source in "${C_SOURCES[@]}"; do
    name="$(basename "${source%.c}")_minizip"
    "$CC" "${C_FLAGS[@]}" -c "$source" -o "$OBJ_DIR/$name.o" \
        > "$LOG_DIR/$name.log" 2>&1 &
    pids+=("$!")
    names+=("$name")
done

compile_failed=0
for index in "${!pids[@]}"; do
    if ! wait "${pids[$index]}"; then
        echo "COMPILE_FAIL ${names[$index]}" >&2
        sed -n '1,160p' "$LOG_DIR/${names[$index]}.log" >&2
        compile_failed=1
    else
        echo "COMPILE_PASS ${names[$index]}"
    fi
done
if [[ "$compile_failed" -ne 0 ]]; then
    exit 1
fi

OUTPUT="$ARTIFACT_DIR/libapk_installer.so"
if ! "$CXX" --target=aarch64-linux-ohos "--sysroot=$SYSROOT" -B"$MUSL_LIB" -fuse-ld=lld \
    -shared -flto=thin -fsanitize=cfi -fsanitize-cfi-cross-dso \
    -Wl,-z,defs -Wl,--build-id=sha1 \
    -Wl,-soname,libapk_installer.so \
    -L"$MUSL_LIB" -L"$SYSTEM_LIB64" -L"$PLATFORMSDK_LIB" -L"$CHIPSET_SP_LIB" \
    "$OBJ_DIR"/*.o \
    -lhilog -lcrypto_openssl.z -lutils.z -lz \
    "$BUILTINS" \
    -o "$OUTPUT" > "$LOG_DIR/link.log" 2>&1; then
    echo "LINK_FAIL libapk_installer.so" >&2
    sed -n '1,240p' "$LOG_DIR/link.log" >&2
    exit 1
fi

"$READELF" -h -d -n -Ws "$OUTPUT" > "$META_DIR/libapk_installer.readelf.txt"
file "$OUTPUT" > "$META_DIR/libapk_installer.file.txt"
sha256sum "$OUTPUT" > "$META_DIR/artifacts.sha256"

if ! grep -q 'Class:.*ELF64' "$META_DIR/libapk_installer.readelf.txt" ||
    ! grep -q 'Machine:.*AArch64' "$META_DIR/libapk_installer.readelf.txt" ||
    ! grep -q 'Build ID:' "$META_DIR/libapk_installer.readelf.txt" ||
    ! grep -q '__cfi_check' "$META_DIR/libapk_installer.readelf.txt"; then
    echo "ERROR: final ELF identity gate failed" >&2
    exit 1
fi

if grep -Eq 'AppSpawnX|libart|oh-adapter-runtime' \
    "$META_DIR/libapk_installer.readelf.txt"; then
    echo "ERROR: forbidden runtime dependency leaked into final verifier" >&2
    exit 1
fi

echo "BUILD_PASS $OUTPUT"
