#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <frozen-source-root> <fresh-output-root>" >&2
  exit 64
fi

SOURCE_ROOT=$1
OUT_ROOT=$2
OH_ROOT=${OH_ROOT:-/opt/build-trees/oh610_lts_source}
TOOLCHAIN="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm"
PRODUCT_OUT="$OH_ROOT/out/wukong100"
SYSROOT="$PRODUCT_OUT/obj/third_party/musl/usr"
TARGET_LIB="$SYSROOT/lib/aarch64-linux-ohos"
LIBCXX_DIR="$PRODUCT_OUT/obj/build/common/musl/prebuilts/clang/ohos/linux-x86_64/llvm/lib/aarch64-linux-ohos"
BUILTINS="$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"
CC="$TOOLCHAIN/bin/clang"
CXX="$TOOLCHAIN/bin/clang++"
PM="$SOURCE_ROOT/src/adapter/framework/package-manager"
PROBE_DIR="$SOURCE_ROOT/tools/fn01_a11_target_fence_probe"
COMPAT="$SOURCE_ROOT/src/adapter/framework/appspawn-x/bionic_compat/include/libcxx_compat.h"
ARTIFACT="$OUT_ROOT/fn01_a11_target_fence_probe"
BUILD_LOG="$OUT_ROOT/build.log"

if [[ -e "$OUT_ROOT" ]]; then
  echo "fresh-output-root already exists: $OUT_ROOT" >&2
  exit 73
fi
mkdir -p "$OUT_ROOT/obj"

INCLUDES=(
  -I"$PM/install_plan/include"
  -I"$PM/package_transaction/include"
  -I"$PM/package_query/include"
  -I"$PM/component_resolver/include"
  -I"$PM/package_info/include"
  -I"$PM/application_info/include"
  -I"$PM/runtime_path_descriptor/include"
)
CPP_SOURCES=(
  "$PM/package_transaction/src/package_transaction_v1.cpp"
  "$PM/package_query/src/package_query_v1.cpp"
  "$PM/component_resolver/src/component_resolver_v1.cpp"
  "$PM/package_info/src/package_info_v1.cpp"
  "$PM/application_info/src/application_info_v1.cpp"
  "$PM/runtime_path_descriptor/src/runtime_path_descriptor_v1.cpp"
  "$PROBE_DIR/fn01_a11_target_fence_probe.cpp"
)
OBJECTS=()
for source in "${CPP_SOURCES[@]}"; do
  base=$(basename "$source" .cpp)
  OBJECTS+=("$OUT_ROOT/obj/$base.o")
done
SHA_OBJECT="$OUT_ROOT/obj/sha256.o"

COMMON=(
  --target=aarch64-linux-ohos
  -march=armv8-a
  --sysroot="$SYSROOT"
  -B"$TOOLCHAIN/bin"
  -D__MUSL__
  -D_LIBCPP_HAS_MUSL_LIBC
  -D_GNU_SOURCE
  -DOHOS_PLATFORM
  -DFN01_ENABLE_REFERENCE_FIXTURES=1
  -fPIE
  -fno-exceptions
  -fno-rtti
  -Wall
  -Wextra
  -Werror
  -Wno-unused-parameter
  -include "$COMPAT"
  -I"$SYSROOT/include/aarch64-linux-ohos"
)

{
  echo "BUILD_SCOPE=Fn01.A11 ARM64 leaf probe only"
  echo "BUILD_HOST=$(hostname)"
  echo "BUILD_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "SOURCE_ROOT=$SOURCE_ROOT"
  echo "OH_ROOT=$OH_ROOT"
  echo "ARTIFACT=$ARTIFACT"
  echo "COMPILER_SHA256=$(sha256sum "$CXX" | awk '{print $1}')"
  echo "LINKER_SHA256=$(sha256sum "$TOOLCHAIN/bin/ld.lld" | awk '{print $1}')"
  "$CXX" --version | sed -n '1,4p'

  "$CC" "${COMMON[@]}" -std=c11 \
    -I"$PM/install_plan/include" \
    -c "$PM/install_plan/src/sha256.c" -o "$SHA_OBJECT"
  for index in "${!CPP_SOURCES[@]}"; do
    "$CXX" "${COMMON[@]}" -std=c++17 "${INCLUDES[@]}" \
      -c "${CPP_SOURCES[$index]}" -o "${OBJECTS[$index]}"
  done

  "$CXX" --target=aarch64-linux-ohos -march=armv8-a \
    --sysroot="$SYSROOT" -B"$TOOLCHAIN/bin" -B"$TARGET_LIB" \
    -fuse-ld=lld -pie -nodefaultlibs \
    -Wl,-z,noexecstack -Wl,-z,now -Wl,-z,relro \
    -Wl,--build-id=sha1 -Wl,--hash-style=gnu -Wl,--no-undefined \
    -Wl,-Map,"$OUT_ROOT/link.map" \
    "${OBJECTS[@]}" "$SHA_OBJECT" \
    -L"$LIBCXX_DIR" -L"$TARGET_LIB" \
    -lc++ -lc -ldl -lm -lpthread "$BUILTINS" \
    -o "$ARTIFACT"

  file "$ARTIFACT"
  readelf -h "$ARTIFACT"
  readelf -d "$ARTIFACT"
  sha256sum "$ARTIFACT"
} 2>&1 | tee "$BUILD_LOG"

echo "ARM64_LEAF_ARTIFACT=$ARTIFACT"
echo "ARM64_BUILD_LOG=$BUILD_LOG"
