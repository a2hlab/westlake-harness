#!/usr/bin/env bash
# Minimal OH ARM64 leaf compile -> shared link for Fn01.A10. No package/device.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A10_ARM64_OUT:-$ADAPTER_ROOT/.work/fn01-a10-arm64-leaf}
TOOLCHAIN=${OHOS_NATIVE_TOOLCHAIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm}
SYSROOT=${OHOS_NATIVE_SYSROOT:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/sysroot}
CC="$TOOLCHAIN/bin/clang"
CXX="$TOOLCHAIN/bin/clang++"
READELF="$TOOLCHAIN/bin/llvm-readelf"

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A10 ARM64 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi
if [[ -e "$OUT" ]]; then
    echo "ERROR: Fn01.A10 ARM64 output must be fresh: $OUT" >&2
    exit 2
fi
for required in "$CC" "$CXX" "$READELF"; do
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
COMMON=(
    --target=aarch64-linux-ohos
    "--sysroot=$SYSROOT"
    -fPIC
    -O2
    -Wall
    -Wextra
    -Werror
)

"$CC" "${COMMON[@]}" -std=c11 \
    -I"$PACKAGE_DIR/install_plan/include" \
    -c "$PACKAGE_DIR/install_plan/src/sha256.c" \
    -o "$OUT/obj/sha256.o"
"$CXX" "${COMMON[@]}" -std=c++17 \
    -I"$PACKAGE_DIR/bms_projection/include" \
    -I"$PACKAGE_DIR/install_plan/include" \
    -c "$PACKAGE_DIR/bms_projection/src/bms_projection_v1.cpp" \
    -o "$OUT/obj/bms_projection_v1.o"
"$CXX" --target=aarch64-linux-ohos "--sysroot=$SYSROOT" \
    -fuse-ld=lld -shared \
    "$OUT/obj/bms_projection_v1.o" "$OUT/obj/sha256.o" \
    -o "$OUT/artifacts/libfn01_bms_projection_leaf.so"

"$READELF" -h -d -s "$OUT/artifacts/libfn01_bms_projection_leaf.so" \
    >"$OUT/meta/readelf.txt"
file "$OUT/artifacts/libfn01_bms_projection_leaf.so" \
    >"$OUT/meta/file.txt"
{
    "$CC" --version
    shasum -a 256 "$CC" "$CXX" "$READELF"
    shasum -a 256 \
        "$SYSROOT/usr/lib/aarch64-linux-ohos/libc.so" \
        "$SYSROOT/usr/lib/aarch64-linux-ohos/libc++.so" 2>/dev/null || true
} >"$OUT/meta/toolchain.txt"
shasum -a 256 \
    "$PACKAGE_DIR/bms_projection/include/bms_projection_v1.h" \
    "$PACKAGE_DIR/bms_projection/src/bms_projection_v1.cpp" \
    "$PACKAGE_DIR/install_plan/src/sha256.c" \
    "$SCRIPT_DIR/build_fn01_a10_arm64_leaf.sh" \
    >"$OUT/meta/source-inputs.sha256"
shasum -a 256 \
    "$OUT/obj/bms_projection_v1.o" \
    "$OUT/obj/sha256.o" \
    "$OUT/artifacts/libfn01_bms_projection_leaf.so" \
    >"$OUT/meta/artifacts.sha256"
printf '%s\n' \
    "action=Fn01.A10" \
    "target=aarch64-linux-ohos" \
    "boundary=leaf_compile_and_link_only" \
    "package=NOT_RUN" \
    "deploy=NOT_RUN" \
    "device=NOT_RUN" \
    "generation=NOT_PROMOTED" \
    "formal_verdict=NOT_ISSUED" \
    >"$OUT/meta/scope.txt"

cat "$OUT/meta/file.txt"
echo "ARM64_LEAF_LINK_READY action=Fn01.A10 formal_verdict=NOT_ISSUED"
