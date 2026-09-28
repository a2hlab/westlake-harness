#!/usr/bin/env bash
#
# Compile-only preflight for the L02.A01 revision-5 typed BMS/installs
# transaction against the exact AlexPC OH 6.1.0.31 source preimages.
#
# This is not a B1 producer. It restores both OH source and prior output files
# before returning, and exists only to expose one paired-library compile/link
# wall without leaving a mixed deployable tree behind.

set -euo pipefail

: "${ADAPTER_ROOT:?ADAPTER_ROOT is required}"
: "${OH_ROOT:?OH_ROOT is required}"
: "${GENERATION_ROOT:?GENERATION_ROOT is required}"

if [[ "$ADAPTER_ROOT" != /* || ! -d "$ADAPTER_ROOT" ]]; then
    echo "ERROR: invalid ADAPTER_ROOT: $ADAPTER_ROOT" >&2
    exit 2
fi
if [[ "$OH_ROOT" != /* || ! -d "$OH_ROOT/out/wukong100" ]]; then
    echo "ERROR: invalid OH_ROOT: $OH_ROOT" >&2
    exit 2
fi
if [[ "$GENERATION_ROOT" != /* || -e "$GENERATION_ROOT" ]]; then
    echo "ERROR: GENERATION_ROOT must be a fresh absolute path: $GENERATION_ROOT" >&2
    exit 2
fi

BUILD_JOBS="${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}"
if [[ ! "$BUILD_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: BUILD_JOBS must be a positive integer: $BUILD_JOBS" >&2
    exit 2
fi

PATCH_ROOT="$ADAPTER_ROOT/ohos_patches/l02_a01"
REV5_PATCH="$PATCH_ROOT/oh610_game_min_rev5.patch"
PREIMAGE_MANIFEST="$PATCH_ROOT/OH610_GAME_MIN_REV5_PREIMAGES.tsv"
PYTHON="$OH_ROOT/prebuilts/python/linux-x86/3.11.4/bin/python3.11"
NINJA="$OH_ROOT/prebuilts/build-tools/linux-x86/bin/ninja"
READELF="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf"

for input in "$REV5_PATCH" "$PREIMAGE_MANIFEST" "$PYTHON" "$NINJA" "$READELF"; do
    if [[ ! -f "$input" ]]; then
        echo "ERROR: required input missing: $input" >&2
        exit 2
    fi
done

META="$GENERATION_ROOT/meta"
LOGS="$GENERATION_ROOT/logs"
ARTIFACTS="$GENERATION_ROOT/artifacts"
SOURCE_BACKUP="$GENERATION_ROOT/preimage/source"
OUTPUT_BACKUP="$GENERATION_ROOT/preimage/output"
TOOL_BIN="$GENERATION_ROOT/tool-bin"
mkdir -p "$META" "$LOGS" "$ARTIFACTS" "$SOURCE_BACKUP" "$OUTPUT_BACKUP" "$TOOL_BIN"
ln -s "$PYTHON" "$TOOL_BIN/python"

sha256sum "$REV5_PATCH" "$PREIMAGE_MANIFEST" > "$META/adapter-inputs.sha256"

tail -n +2 "$PREIMAGE_MANIFEST" > "$META/preimages.sha256"
(
    cd "$OH_ROOT"
    sha256sum -c "$META/preimages.sha256"
) > "$LOGS/preimage-check.log" 2>&1

SOURCE_PATHS=()
while IFS=$'\t' read -r expected relative; do
    [[ "$expected" == "sha256" ]] && continue
    SOURCE_PATHS+=("$relative")
done < "$PREIMAGE_MANIFEST"

for relative in "${SOURCE_PATHS[@]}"; do
    mkdir -p "$SOURCE_BACKUP/$(dirname "$relative")"
    cp -a "$OH_ROOT/$relative" "$SOURCE_BACKUP/$relative"
done

OUTPUT_LIST="$META/prior-output-paths.txt"
(
    cd "$OH_ROOT"
    find out/wukong100 -type f \
        \( -name libbms.z.so -o -name libinstalls.z.so \) -print | sort
) > "$OUTPUT_LIST"
while IFS= read -r relative; do
    mkdir -p "$OUTPUT_BACKUP/$(dirname "$relative")"
    cp -a "$OH_ROOT/$relative" "$OUTPUT_BACKUP/$relative"
done < "$OUTPUT_LIST"

restored=0
restore_tree()
{
    if [[ "$restored" -eq 1 ]]; then
        return
    fi
    for relative in "${SOURCE_PATHS[@]}"; do
        cp -a "$SOURCE_BACKUP/$relative" "$OH_ROOT/$relative"
    done
    while IFS= read -r relative; do
        cp -a "$OUTPUT_BACKUP/$relative" "$OH_ROOT/$relative"
    done < "$OUTPUT_LIST"
    restored=1
}
trap restore_tree EXIT
trap 'exit 130' HUP INT TERM

(
    cd "$OH_ROOT"
    patch --batch --forward -p1 < "$REV5_PATCH"
) > "$LOGS/patch-apply.log" 2>&1

(
    cd "$OH_ROOT"
    PATH="$TOOL_BIN:$PATH" "$NINJA" -C out/wukong100 -w dupbuild=warn -j"$BUILD_JOBS" \
        bundlemanager/bundle_framework/libbms.z.so \
        bundlemanager/bundle_framework/libinstalls.z.so
) > "$LOGS/ninja.log" 2>&1

cp -a "$OH_ROOT/out/wukong100/bundlemanager/bundle_framework/libbms.z.so" \
    "$ARTIFACTS/libbms.z.so"
cp -a "$OH_ROOT/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so" \
    "$ARTIFACTS/libinstalls.z.so"

for artifact in "$ARTIFACTS/libbms.z.so" "$ARTIFACTS/libinstalls.z.so"; do
    "$READELF" -h -n -d "$artifact" > "$META/$(basename "$artifact").readelf.txt"
done
sha256sum "$ARTIFACTS/libbms.z.so" "$ARTIFACTS/libinstalls.z.so" \
    > "$META/artifacts.sha256"

restore_tree
trap - EXIT HUP INT TERM

(
    cd "$OH_ROOT"
    sha256sum -c "$META/preimages.sha256"
) > "$LOGS/post-restore-source-check.log" 2>&1
while IFS= read -r relative; do
    if ! cmp -s "$OUTPUT_BACKUP/$relative" "$OH_ROOT/$relative"; then
        echo "ERROR: prior output restore failed: $relative" >&2
        exit 1
    fi
done < "$OUTPUT_LIST"

echo "PREFLIGHT_PAIR_PASS $ARTIFACTS"
