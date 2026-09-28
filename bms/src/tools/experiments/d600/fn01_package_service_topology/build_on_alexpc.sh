#!/usr/bin/env bash
set -euo pipefail

OH_ROOT=${1:-/opt/build-trees/oh610_lts_source}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT_DIR=$SCRIPT_DIR/out
ARTIFACT=$OUT_DIR/fn01_topology_probe
LINK_MAP=$OUT_DIR/fn01_topology_probe.map
LINK_DEPENDENCIES=$OUT_DIR/fn01_topology_probe.link.d
ACTUAL_LINK_INPUTS_SHA256=$OUT_DIR/actual-link-inputs.sha256
PROVENANCE_INPUTS=$OUT_DIR/provenance-inputs.sha256
PRODUCT_OUT=$OH_ROOT/out/wukong100
SYSROOT=$PRODUCT_OUT/obj/third_party/musl
TOOLCHAIN=$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm
CXX=$TOOLCHAIN/bin/clang++
TOOLCHAIN_LIB=$TOOLCHAIN/lib/aarch64-linux-ohos
BUILTINS=$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a
RUNTIME_PACKAGE_ROOT=${FN01_RUNTIME_PACKAGE_ROOT:-}
RUNTIME_RECEIPT=${FN01_RUNTIME_RECEIPT:-}
if [[ -n "$RUNTIME_PACKAGE_ROOT" ]]; then
  LIBUTILS=$RUNTIME_PACKAGE_ROOT/lib64/platformsdk/libutils.z.so
  LIBIPC=$RUNTIME_PACKAGE_ROOT/lib64/platformsdk/libipc_single.z.so
  LIBSAMGR_COMMON=$RUNTIME_PACKAGE_ROOT/lib64/platformsdk/libsamgr_common.z.so
  LIBSAMGR_PROXY=$RUNTIME_PACKAGE_ROOT/lib64/platformsdk/libsamgr_proxy.z.so
  RUNTIME_LIBCXX=$RUNTIME_PACKAGE_ROOT/lib64/chipset-sdk-sp/libc++.so
  RUNTIME_LIBC=$RUNTIME_PACKAGE_ROOT/lib/ld-musl-aarch64.so.1
else
  LIBUTILS=$PRODUCT_OUT/commonlibrary/c_utils/libutils.z.so
  LIBIPC=$PRODUCT_OUT/communication/ipc/libipc_single.z.so
  LIBSAMGR_COMMON=$PRODUCT_OUT/systemabilitymgr/samgr/libsamgr_common.z.so
  LIBSAMGR_PROXY=$PRODUCT_OUT/systemabilitymgr/samgr/libsamgr_proxy.z.so
  RUNTIME_LIBCXX=$TOOLCHAIN_LIB/libc++.so
  RUNTIME_LIBC=$SYSROOT/usr/lib/aarch64-linux-ohos/libc.so
fi
SOURCES=(
  "$SCRIPT_DIR/fn01_topology_probe.cpp"
  "$SCRIPT_DIR/fn01_secure_store.cpp"
)
HEADERS=(
  "$SCRIPT_DIR/fn01_topology_policy.h"
  "$SCRIPT_DIR/fn01_secure_store.h"
)
OBJECTS=(
  "$OUT_DIR/fn01_topology_probe.o"
  "$OUT_DIR/fn01_secure_store.o"
)
LINK_INPUTS=(
  "$LIBUTILS"
  "$LIBIPC"
  "$LIBSAMGR_COMMON"
  "$LIBSAMGR_PROXY"
  "$TOOLCHAIN_LIB/libunwind.a"
  "$BUILTINS"
  "$RUNTIME_LIBCXX"
  "$RUNTIME_LIBC"
  "$TOOLCHAIN_LIB/libc++abi.a"
  "$SYSROOT/usr/lib/aarch64-linux-ohos/libdl.a"
  "$SYSROOT/usr/lib/aarch64-linux-ohos/libm.a"
)
AUTOMATIC_LINK_INPUTS=(
  "$SYSROOT/usr/lib/aarch64-linux-ohos/Scrt1.o"
  "$SYSROOT/usr/lib/aarch64-linux-ohos/crti.o"
  "$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtbegin.o"
  "$TOOLCHAIN/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtend.o"
  "$SYSROOT/usr/lib/aarch64-linux-ohos/crtn.o"
)

mkdir -p "$OUT_DIR"

if [[ ${FN01_BUILD_CAPTURE:-0} != 1 ]]; then
  set +e
  FN01_BUILD_CAPTURE=1 "$0" "$OH_ROOT" >"$OUT_DIR/build.log" 2>&1
  build_status=$?
  set -e
  cat "$OUT_DIR/build.log"
  exit "$build_status"
fi

if [[ -n "$RUNTIME_PACKAGE_ROOT" ]]; then
  if [[ -z "$RUNTIME_RECEIPT" || ! -f "$RUNTIME_RECEIPT" ]]; then
    echo "RUNTIME_RECEIPT_REQUIRED root=$RUNTIME_PACKAGE_ROOT" >&2
    exit 92
  fi
  runtime_count=0
  while read -r expected_hash device_path extra; do
    if [[ -z "$expected_hash" || "$expected_hash" == \#* ]]; then
      continue
    fi
    if [[ -n "${extra:-}" || "$device_path" != /* ]]; then
      echo "RUNTIME_RECEIPT_ROW_INVALID path=$device_path" >&2
      exit 93
    fi
    package_path=$RUNTIME_PACKAGE_ROOT$device_path
    if [[ ! -f "$package_path" ]]; then
      echo "RUNTIME_PACKAGE_INPUT_MISSING path=$package_path" >&2
      exit 94
    fi
    actual_hash=$(sha256sum "$package_path" | awk '{print $1}')
    if [[ "$actual_hash" != "$expected_hash" ]]; then
      echo "RUNTIME_PACKAGE_HASH_MISMATCH path=$package_path expected=$expected_hash actual=$actual_hash" >&2
      exit 95
    fi
    printf 'RUNTIME_PACKAGE_HASH_MATCH path=%s sha256=%s\n' \
      "$package_path" "$actual_hash"
    runtime_count=$((runtime_count + 1))
  done <"$RUNTIME_RECEIPT"
  if [[ "$runtime_count" -ne 6 ]]; then
    echo "RUNTIME_RECEIPT_COUNT_INVALID expected=6 actual=$runtime_count" >&2
    exit 96
  fi
  printf 'RUNTIME_PACKAGE_ROOT=%s\n' "$RUNTIME_PACKAGE_ROOT"
  printf 'RUNTIME_RECEIPT_SHA256=%s\n' \
    "$(sha256sum "$RUNTIME_RECEIPT" | awk '{print $1}')"
fi

MANIFEST_COMMIT=$(git -C "$OH_ROOT/.repo/manifests" rev-parse HEAD)
BASELINE_ROWS=()
for component in \
  foundation/systemabilitymgr/safwk \
  foundation/systemabilitymgr/samgr \
  foundation/communication/ipc \
  foundation/bundlemanager/bundle_framework; do
  component_commit=$(git -C "$OH_ROOT/$component" rev-parse HEAD)
  component_status=$(
    git -C "$OH_ROOT/$component" status --short --untracked-files=no |
      sha256sum |
      awk '{print $1}'
  )
  BASELINE_ROWS+=("$component commit=$component_commit tracked_status_sha256=$component_status")
done

COLLISION_SCAN=$OUT_DIR/sa-id-collision-scan.txt
: >"$COLLISION_SCAN"
while IFS= read -r -d '' candidate; do
  grep -Ein \
    '(^|[^0-9A-Fa-f])(127233|0x0*1[fF]101)([^0-9A-Fa-f]|$)' \
    "$candidate" >>"$COLLISION_SCAN" || true
done < <(
  find "$OH_ROOT" \
    -path "$OH_ROOT/.repo" -prune -o \
    -path "$OH_ROOT/out" -prune -o \
    -path "$OH_ROOT/prebuilts" -prune -o \
    -type f \
    \( -path '*/sa_profile/*' -o -name service_contexts -o \
       -name system_ability_definition.h \) \
    -print0
)
if [[ -s "$COLLISION_SCAN" ]]; then
  echo "PRIVATE_SA_ID_COLLISION id=127233"
  cat "$COLLISION_SCAN"
  exit 90
fi

COMMON_FLAGS=(
  --target=aarch64-linux-ohos
  -march=armv8-a
  --sysroot="$SYSROOT"
  -D__MUSL__
  -D_LIBCPP_HAS_MUSL_LIBC
  -D_GNU_SOURCE
  -DOHOS_PLATFORM
  -DCONFIG_STANDARD_SYSTEM
  -std=c++17
  -fPIC
  -fPIE
  -fno-exceptions
  -fno-rtti
  -fvisibility-inlines-hidden
  -Wall
  -Wextra
  -Werror
  -Wno-unused-parameter
  -I"$PRODUCT_OUT/obj/third_party/musl/usr/include/aarch64-linux-ohos"
  -I"$OH_ROOT/commonlibrary/c_utils/base/include"
  -I"$OH_ROOT/third_party/bounds_checking_function/include"
  -I"$OH_ROOT/foundation/communication/ipc/dl_deps"
  -I"$OH_ROOT/foundation/communication/ipc/interfaces/innerkits/ipc_core/include"
  -I"$OH_ROOT/foundation/communication/ipc/ipc/native/src/core/dbinder/include"
  -I"$OH_ROOT/foundation/communication/ipc/ipc/native/src/core/framework/include"
  -I"$OH_ROOT/foundation/communication/ipc/ipc/native/src/core/invoker/include"
  -I"$OH_ROOT/foundation/systemabilitymgr/samgr/interfaces/innerkits/common/include"
  -I"$OH_ROOT/foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include"
  -I"$OH_ROOT/foundation/systemabilitymgr/samgr/interfaces/innerkits/dynamic_cache/include"
)

LINK_FLAGS=(
  --target=aarch64-linux-ohos
  -march=armv8-a
  --sysroot="$SYSROOT"
  -fuse-ld=lld
  -nodefaultlibs
  -pie
  -Wl,-z,noexecstack
  -Wl,-z,now
  -Wl,-z,relro
  -Wl,--build-id=sha1
  -Wl,--hash-style=gnu
  -Wl,--no-undefined
  -Wl,--trace
  -Wl,-Map,"$LINK_MAP"
  -Wl,--dependency-file,"$LINK_DEPENDENCIES"
  -Wl,-rpath-link,"$PRODUCT_OUT/packages/phone/system/lib64/platformsdk"
  -L"$PRODUCT_OUT/obj/third_party/musl/usr/lib/aarch64-linux-ohos"
  -L"$TOOLCHAIN_LIB"
  "${OBJECTS[@]}"
  "${LINK_INPUTS[0]}"
  "${LINK_INPUTS[1]}"
  "${LINK_INPUTS[2]}"
  "${LINK_INPUTS[3]}"
  "$TOOLCHAIN_LIB/libunwind.a"
  "$BUILTINS"
  "$RUNTIME_LIBCXX"
  "$RUNTIME_LIBC"
  "$TOOLCHAIN_LIB/libc++abi.a"
  -ldl
  -lm
  -o "$ARTIFACT"
)

printf 'OH_ROOT=%s\n' "$OH_ROOT"
printf 'BUILD_HOST=%s\n' "$(hostname)"
printf 'BUILD_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'OH_MANIFEST_COMMIT=%s\n' "$MANIFEST_COMMIT"
printf 'OH_COMPONENT_BASELINE=%s\n' "${BASELINE_ROWS[@]}"
printf 'PRIVATE_SA_ID=127233\n'
printf 'PRIVATE_SA_ID_COLLISION_SCAN=ABSENT\n'
printf 'SOURCE_INPUT_SHA256='
sha256sum "${SOURCES[@]}" "${HEADERS[@]}"
printf 'BUILD_SCRIPT_SHA256=%s\n' "$(sha256sum "$0" | awk '{print $1}')"
printf 'COMPILER_SHA256=%s\n' "$(sha256sum "$CXX" | awk '{print $1}')"
printf 'LINK_INPUT_SHA256='
sha256sum "${LINK_INPUTS[@]}"
"$CXX" --version | sed -n '1,4p'
for index in "${!SOURCES[@]}"; do
  printf 'COMPILE_COMMAND='
  printf '%q ' "$CXX" "${COMMON_FLAGS[@]}" -c "${SOURCES[$index]}" \
    -o "${OBJECTS[$index]}"
  printf '\n'
  "$CXX" "${COMMON_FLAGS[@]}" -c "${SOURCES[$index]}" \
    -o "${OBJECTS[$index]}"
done
printf 'OBJECT_SHA256='
sha256sum "${OBJECTS[@]}"
printf 'LINK_COMMAND='
printf '%q ' "$CXX" "${LINK_FLAGS[@]}"
printf '\n'
"$CXX" "${LINK_FLAGS[@]}"

ACTUAL_LINK_INPUTS=(
  "${AUTOMATIC_LINK_INPUTS[@]}"
  "${OBJECTS[@]}"
  "${LINK_INPUTS[@]}"
)
mapfile -t REPORTED_LINK_INPUTS < <(
  sed -n '2,/^$/p' "$LINK_DEPENDENCIES" |
    sed -e '/^$/d' \
      -e 's/^[[:space:]]*//' \
      -e 's/[[:space:]]*\\$//'
)
if [[ "${#REPORTED_LINK_INPUTS[@]}" -ne "${#ACTUAL_LINK_INPUTS[@]}" ]]; then
  printf 'LINK_DEPENDENCY_COUNT_MISMATCH expected=%s actual=%s\n' \
    "${#ACTUAL_LINK_INPUTS[@]}" "${#REPORTED_LINK_INPUTS[@]}" >&2
  printf 'REPORTED_LINK_INPUT=%s\n' "${REPORTED_LINK_INPUTS[@]}" >&2
  exit 91
fi
for input in "${ACTUAL_LINK_INPUTS[@]}"; do
  found=0
  for reported in "${REPORTED_LINK_INPUTS[@]}"; do
    if [[ "$reported" == "$input" ]]; then
      found=1
      break
    fi
  done
  if [[ "$found" != 1 ]]; then
    printf 'LINK_DEPENDENCY_MISSING path=%s\n' "$input" >&2
    exit 91
  fi
done
sha256sum "${ACTUAL_LINK_INPUTS[@]}" |
  LC_ALL=C sort -k2 >"$ACTUAL_LINK_INPUTS_SHA256"
printf 'ACTUAL_LINK_INPUT_COUNT=%s\n' "${#ACTUAL_LINK_INPUTS[@]}"
printf 'ACTUAL_LINK_INPUTS_SHA256=%s\n' \
  "$(sha256sum "$ACTUAL_LINK_INPUTS_SHA256" | awk '{print $1}')"

file "$ARTIFACT"
readelf -h "$ARTIFACT" | sed -n '1,24p'
readelf -d "$ARTIFACT" | grep NEEDED
sha256sum "$0" "$CXX" "${SOURCES[@]}" "${HEADERS[@]}" \
  "${OBJECTS[@]}" "${LINK_INPUTS[@]}" "$LINK_MAP" "$LINK_DEPENDENCIES" \
  "$ACTUAL_LINK_INPUTS_SHA256" "$COLLISION_SCAN" "$ARTIFACT" \
  >"$PROVENANCE_INPUTS"
printf 'PROVENANCE_INPUTS_SHA256=%s\n' \
  "$(sha256sum "$PROVENANCE_INPUTS" | awk '{print $1}')"
printf 'ARTIFACT_SHA256=%s\n' "$(sha256sum "$ARTIFACT" | awk '{print $1}')"
