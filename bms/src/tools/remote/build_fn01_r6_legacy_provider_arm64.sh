#!/usr/bin/env bash
#
# Build the Fn01 historical r6-compatible APK provider on hw248.
#
# Required:
#   REPO_ROOT        checkout containing the frozen Fn01 adapter profile
#   OH_ROOT          built OpenHarmony 6.1.0.31 source tree
#   GENERATION_ROOT  fresh output directory

set -euo pipefail

: "${REPO_ROOT:?REPO_ROOT is required}"
: "${OH_ROOT:?OH_ROOT is required}"
: "${GENERATION_ROOT:?GENERATION_ROOT is required}"

for directory in "$REPO_ROOT" "$OH_ROOT"; do
    if [[ "$directory" != /* || ! -d "$directory" ]]; then
        echo "ERROR: expected existing absolute directory: $directory" >&2
        exit 2
    fi
done
if [[ "$GENERATION_ROOT" != /* || -e "$GENERATION_ROOT" ]]; then
    echo "ERROR: GENERATION_ROOT must be a fresh absolute path: $GENERATION_ROOT" >&2
    exit 2
fi

ADAPTER_ROOT="$REPO_ROOT/src/atoms/Fn01/A01/hw248-r6-legacy/adapter"
SOURCE_LOCK="$REPO_ROOT/src/atoms/Fn01/A01/hw248-r6-legacy/adapter-source.sha256"
[[ -f "$SOURCE_LOCK" ]] || {
    echo "ERROR: adapter source lock is missing: $SOURCE_LOCK" >&2
    exit 2
}
(
    cd "$REPO_ROOT"
    sha256sum -c "$SOURCE_LOCK"
)

OH_OUT="$OH_ROOT/out/wukong100"
SYSROOT="$OH_OUT/obj/third_party/musl/usr"
MUSL_LIB="$SYSROOT/lib/aarch64-linux-ohos"
HILOG_LIB="$OH_OUT/hiviewdfx/hilog"
OPENSSL_LIB="$OH_OUT/thirdparty/openssl"
UTILS_LIB="$OH_OUT/commonlibrary/c_utils"
ZLIB_LIB="$OH_OUT/thirdparty/zlib"
TOOLCHAIN="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm"
CXX="$TOOLCHAIN/bin/clang++"
CC="$TOOLCHAIN/bin/clang"
READELF="$TOOLCHAIN/bin/llvm-readelf"
BUILTINS="$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"
JNI="$ADAPTER_ROOT/framework/package-manager/jni"
COMPAT_INCLUDE="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"
MINIZIP="$OH_ROOT/third_party/zlib/contrib/minizip"
ZLIB="$OH_ROOT/third_party/zlib"

for directory in "$OH_OUT" "$SYSROOT" "$MUSL_LIB" "$HILOG_LIB" \
    "$OPENSSL_LIB" "$UTILS_LIB" "$ZLIB_LIB" "$TOOLCHAIN" "$JNI" \
    "$COMPAT_INCLUDE" "$MINIZIP"; do
    if [[ ! -d "$directory" ]]; then
        echo "ERROR: required input directory missing: $directory" >&2
        exit 2
    fi
done
for input in "$CXX" "$CC" "$READELF" "$BUILTINS"; do
    if [[ ! -f "$input" ]]; then
        echo "ERROR: required tool/input missing: $input" >&2
        exit 2
    fi
done

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
    "$JNI/game_install_plan_v1.cpp"
    "$JNI/permission_mapper.cpp"
    "$JNI/oh_adapter_install_apk_c_entry.cpp"
)
C_SOURCES=(
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
    "$JNI/apk_verified_session_c_api.h"
    "$JNI/game_install_plan_v1.h"
    "$JNI/native_payload_inspector.h"
    "$JNI/permission_mapper.h"
    "$JNI/template_entry_hap.h"
    "$COMPAT_INCLUDE/libcxx_compat.h"
)
for input in "${CPP_SOURCES[@]}" "${C_SOURCES[@]}" "${SOURCE_HEADERS[@]}"; do
    if [[ ! -f "$input" ]]; then
        echo "ERROR: source input missing: $input" >&2
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
    -Wno-unused-const-variable
)
CPP_FLAGS=(
    "${COMMON_FLAGS[@]}"
    -std=c++17
    -include
    "$COMPAT_INCLUDE/libcxx_compat.h"
    "-I$COMPAT_INCLUDE"
    "-I$JNI"
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
    "-I$MINIZIP"
    "-I$ZLIB"
)

printf 'route=fn01-r6-legacy-direct-manifest\n' > "$META_DIR/target.txt"
printf 'target=OH6.1.0.31/wukong100/AArch64\n' >> "$META_DIR/target.txt"
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
    if wait "${pids[$index]}"; then
        echo "COMPILE_PASS ${names[$index]}"
    else
        echo "COMPILE_FAIL ${names[$index]}" >&2
        sed -n '1,160p' "$LOG_DIR/${names[$index]}.log" >&2
        compile_failed=1
    fi
done
if [[ "$compile_failed" -ne 0 ]]; then
    exit 1
fi

OUTPUT="$ARTIFACT_DIR/libapk_installer.so"
if ! "$CXX" --target=aarch64-linux-ohos "--sysroot=$SYSROOT" -B"$MUSL_LIB" \
    -fuse-ld=lld -shared -flto=thin -fsanitize=cfi -fsanitize-cfi-cross-dso \
    -Wl,-z,defs -Wl,--build-id=sha1 -Wl,-soname,libapk_installer.so \
    -L"$MUSL_LIB" -L"$HILOG_LIB" -L"$OPENSSL_LIB" -L"$UTILS_LIB" -L"$ZLIB_LIB" \
    "$OBJ_DIR"/*.o \
    -lhilog -lcrypto_openssl.z -lutils.z -lshared_libz.z \
    "$BUILTINS" -o "$OUTPUT" > "$LOG_DIR/link.log" 2>&1; then
    echo "LINK_FAIL libapk_installer.so" >&2
    sed -n '1,240p' "$LOG_DIR/link.log" >&2
    exit 1
fi

"$READELF" -h -d -n -Ws "$OUTPUT" > "$META_DIR/libapk_installer.readelf.txt"
file "$OUTPUT" > "$META_DIR/libapk_installer.file.txt"
sha256sum "$OUTPUT" > "$META_DIR/artifacts.sha256"

grep -q 'Class:.*ELF64' "$META_DIR/libapk_installer.readelf.txt"
grep -q 'Machine:.*AArch64' "$META_DIR/libapk_installer.readelf.txt"
grep -q 'Build ID:' "$META_DIR/libapk_installer.readelf.txt"
grep -q '__cfi_check' "$META_DIR/libapk_installer.readelf.txt"
grep -q 'oh_adapter_install_apk_with_manifest' "$META_DIR/libapk_installer.readelf.txt"

echo "BUILD_PASS $OUTPUT"
