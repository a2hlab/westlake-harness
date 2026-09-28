#!/usr/bin/env bash
# Minimal OH ARM64 leaf compile -> link for Fn01.A09. No package/deploy/generation.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A09_ARM64_OUT:-$ADAPTER_ROOT/.work/fn01-a09-arm64-leaf}
TOOLCHAIN=${OHOS_NATIVE_TOOLCHAIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm}
SYSROOT=${OHOS_NATIVE_SYSROOT:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/sysroot}
CC="$TOOLCHAIN/bin/clang"
CXX="$TOOLCHAIN/bin/clang++"
READELF="$TOOLCHAIN/bin/llvm-readelf"

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A09 ARM64 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
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
INCLUDE_PRESENTATION="$PACKAGE_DIR/launcher_presentation/include"
INCLUDE_SHA="$PACKAGE_DIR/install_plan/include"
SOURCE_PRESENTATION="$PACKAGE_DIR/launcher_presentation/src/launcher_presentation_v1.cpp"
SOURCE_SHA="$PACKAGE_DIR/install_plan/src/sha256.c"
PRESENTATION_OBJECT="$OUT/obj/launcher_presentation_v1.o"
SHA_OBJECT="$OUT/obj/sha256.o"
ARTIFACT="$OUT/artifacts/libfn01_launcher_presentation_leaf.so"
RUNNER="$SCRIPT_DIR/build_fn01_a09_arm64_leaf.sh"

COMMON=(
    --target=aarch64-linux-ohos
    "--sysroot=$SYSROOT"
    -fPIC
    -O2
    -Wall
    -Wextra
    -Werror
)

"$CC" "${COMMON[@]}" -std=c11 -I"$INCLUDE_SHA" \
    -c "$SOURCE_SHA" -o "$SHA_OBJECT"
"$CXX" "${COMMON[@]}" -std=c++17 \
    -I"$INCLUDE_PRESENTATION" -I"$INCLUDE_SHA" \
    -c "$SOURCE_PRESENTATION" -o "$PRESENTATION_OBJECT"
"$CXX" --target=aarch64-linux-ohos "--sysroot=$SYSROOT" \
    -fuse-ld=lld -Wl,--build-id=sha1 -shared \
    "$PRESENTATION_OBJECT" "$SHA_OBJECT" \
    -o "$ARTIFACT"

"$READELF" -h -d -s "$ARTIFACT" >"$OUT/meta/readelf.txt"
file "$ARTIFACT" >"$OUT/meta/file.txt"
{
    "$CC" --version
    shasum -a 256 "$CC" "$CXX" "$READELF"
    shasum -a 256 "$SYSROOT/usr/lib/aarch64-linux-ohos/libc.so" \
        "$SYSROOT/usr/lib/aarch64-linux-ohos/libc++.so" 2>/dev/null || true
} >"$OUT/meta/toolchain.txt"
shasum -a 256 \
    "$PACKAGE_DIR/launcher_presentation/include/launcher_presentation_v1.h" \
    "$SOURCE_PRESENTATION" "$SOURCE_SHA" "$RUNNER" \
    >"$OUT/meta/source-inputs.sha256"
shasum -a 256 "$PRESENTATION_OBJECT" "$SHA_OBJECT" "$ARTIFACT" \
    >"$OUT/meta/artifacts.sha256"
printf '%s\n' \
    "target=aarch64-linux-ohos" \
    "boundary=leaf_compile_and_link_only" \
    "package=NOT_RUN" \
    "deploy=NOT_RUN" \
    "device=NOT_RUN" \
    "generation=NOT_PROMOTED" \
    >"$OUT/meta/scope.txt"

cat "$OUT/meta/file.txt"
echo "ARM64_LEAF_LINK_READY action=Fn01.A09 formal_verdict=NOT_ISSUED"
