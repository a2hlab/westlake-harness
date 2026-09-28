#!/usr/bin/env bash
# Target-scoped equivalent build for the BUILD.gn fn01_bms_projection target.
# It compiles and archives only the target's own source; dependency closure is
# covered by the separate A10 ARM64 leaf shared-link check.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A10_TARGET_OUT:-$ADAPTER_ROOT/.work/fn01-a10-arm64-target}
TOOLCHAIN=${OHOS_NATIVE_TOOLCHAIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm}
SYSROOT=${OHOS_NATIVE_SYSROOT:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/sysroot}
CXX="$TOOLCHAIN/bin/clang++"
AR="$TOOLCHAIN/bin/llvm-ar"

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A10 target output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi
if [[ -e "$OUT" ]]; then
    echo "ERROR: Fn01.A10 target output must be fresh: $OUT" >&2
    exit 2
fi
for required in "$CXX" "$AR"; do
    [[ -x "$required" ]] || {
        echo "ERROR: missing OH tool: $required" >&2
        exit 2
    }
done
[[ -d "$SYSROOT" ]] || {
    echo "ERROR: missing OH sysroot: $SYSROOT" >&2
    exit 2
}

mkdir -p "$OUT/obj" "$OUT/artifacts" "$OUT/meta"
awk '
  /ohos_static_library\("fn01_bms_projection"\)/ { capture = 1 }
  capture { print }
  capture && /^}/ { exit }
' "$PACKAGE_DIR/BUILD.gn" >"$OUT/meta/gn-target.txt"
grep -q 'bms_projection/src/bms_projection_v1.cpp' \
    "$OUT/meta/gn-target.txt"
grep -q 'bms_projection/include' "$OUT/meta/gn-target.txt"
grep -q 'install_plan/include' "$OUT/meta/gn-target.txt"
grep -q ':fn01_package_transaction' "$OUT/meta/gn-target.txt"

"$CXX" --target=aarch64-linux-ohos "--sysroot=$SYSROOT" \
    -fPIC -O2 -Wall -Wextra -Werror -std=c++17 \
    -I"$PACKAGE_DIR/bms_projection/include" \
    -I"$PACKAGE_DIR/install_plan/include" \
    -c "$PACKAGE_DIR/bms_projection/src/bms_projection_v1.cpp" \
    -o "$OUT/obj/bms_projection_v1.o"
"$AR" rcs "$OUT/artifacts/libfn01_bms_projection.a" \
    "$OUT/obj/bms_projection_v1.o"
"$AR" t "$OUT/artifacts/libfn01_bms_projection.a" \
    >"$OUT/meta/archive-members.txt"
grep -qx 'bms_projection_v1.o' "$OUT/meta/archive-members.txt"

{
    "$CXX" --version
    shasum -a 256 "$CXX" "$AR"
} >"$OUT/meta/toolchain.txt"
shasum -a 256 \
    "$PACKAGE_DIR/BUILD.gn" \
    "$PACKAGE_DIR/bms_projection/include/bms_projection_v1.h" \
    "$PACKAGE_DIR/bms_projection/src/bms_projection_v1.cpp" \
    "$SCRIPT_DIR/build_fn01_a10_arm64_target.sh" \
    >"$OUT/meta/source-inputs.sha256"
shasum -a 256 \
    "$OUT/obj/bms_projection_v1.o" \
    "$OUT/artifacts/libfn01_bms_projection.a" \
    >"$OUT/meta/artifacts.sha256"
printf '%s\n' \
    "action=Fn01.A10" \
    "target=fn01_bms_projection" \
    "target_kind=ohos_static_library" \
    "target_arch=aarch64-linux-ohos" \
    "boundary=target_scoped_equivalent_compile_and_archive" \
    "dependency_closure=SEPARATE_ARM64_LEAF_LINK" \
    "full_generation=NOT_RUN" \
    "package=NOT_RUN" \
    "deploy=NOT_RUN" \
    "device=NOT_RUN" \
    "formal_verdict=NOT_ISSUED" \
    >"$OUT/meta/scope.txt"

echo "ARM64_TARGET_BUILD_READY action=Fn01.A10 target=fn01_bms_projection formal_verdict=NOT_ISSUED"
