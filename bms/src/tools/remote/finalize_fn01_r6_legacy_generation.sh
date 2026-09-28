#!/usr/bin/env bash
#
# Confirm and freeze one hw248 Fn01 r6-legacy platform generation.
#
# Required:
#   OH_ROOT          OpenHarmony 6.1.0.31 source/output tree
#   GENERATION_ROOT  Existing fn01-r6-legacy generation directory

set -euo pipefail

: "${OH_ROOT:?OH_ROOT is required}"
: "${GENERATION_ROOT:?GENERATION_ROOT is required}"

for directory in "$OH_ROOT" "$GENERATION_ROOT"; do
    if [[ "$directory" != /* || ! -d "$directory" ]]; then
        echo "ERROR: expected existing absolute directory: $directory" >&2
        exit 2
    fi
done

NINJA="$OH_ROOT/prebuilts/build-tools/linux-x86/bin/ninja"
READELF="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf"
OUT="$OH_ROOT/out/wukong100"
ARTIFACT_DIR="$GENERATION_ROOT/artifacts"
LOG_DIR="$GENERATION_ROOT/logs"
META_DIR="$GENERATION_ROOT/metadata"

PROVIDER="$ARTIFACT_DIR/libapk_installer.so"
BMS_SOURCE="$OUT/bundlemanager/bundle_framework/libbms.z.so"
INSTALLS_SOURCE="$OUT/bundlemanager/bundle_framework/libinstalls.z.so"
BMS="$ARTIFACT_DIR/libbms.z.so"
INSTALLS="$ARTIFACT_DIR/libinstalls.z.so"

for input in "$NINJA" "$READELF" "$PROVIDER"; do
    if [[ ! -f "$input" ]]; then
        echo "ERROR: required input missing: $input" >&2
        exit 2
    fi
done
mkdir -p "$ARTIFACT_DIR" "$LOG_DIR" "$META_DIR"

# A successful second invocation must either report no work or complete any
# last interrupted edge. Its zero exit status is the authoritative build gate.
"$NINJA" -w dupbuild=warn -C "$OUT" libbms installs \
    >"$LOG_DIR/platform-build-confirm.txt" 2>&1

for input in "$BMS_SOURCE" "$INSTALLS_SOURCE"; do
    if [[ ! -f "$input" ]]; then
        echo "ERROR: platform output missing after successful Ninja: $input" >&2
        exit 1
    fi
done

cp "$BMS_SOURCE" "$BMS"
cp "$INSTALLS_SOURCE" "$INSTALLS"

file "$PROVIDER" "$BMS" "$INSTALLS" >"$META_DIR/artifacts.file.txt"
"$READELF" -h -d -n -Ws "$PROVIDER" \
    >"$META_DIR/libapk_installer.readelf.txt"
"$READELF" -h -d -n -Ws "$BMS" >"$META_DIR/libbms.readelf.txt"
"$READELF" -h -d -n -Ws "$INSTALLS" \
    >"$META_DIR/libinstalls.readelf.txt"
strings "$PROVIDER" >"$META_DIR/libapk_installer.strings.txt"
strings "$BMS" >"$META_DIR/libbms.strings.txt"
strings "$INSTALLS" >"$META_DIR/libinstalls.strings.txt"

for report in \
    "$META_DIR/libapk_installer.readelf.txt" \
    "$META_DIR/libbms.readelf.txt" \
    "$META_DIR/libinstalls.readelf.txt"; do
    grep -q 'Class:.*ELF64' "$report"
    grep -q 'Machine:.*AArch64' "$report"
    grep -q 'Build ID:' "$report"
    grep -q '__cfi_check' "$report"
done

grep -q 'oh_adapter_install_apk_with_manifest' \
    "$META_DIR/libapk_installer.strings.txt"
grep -q 'oh_adapter_build_resources_hap' \
    "$META_DIR/libapk_installer.strings.txt"
grep -q 'oh_adapter_install_apk_with_manifest' \
    "$META_DIR/libbms.strings.txt"
grep -q 'oh_adapter_build_resources_hap' \
    "$META_DIR/libinstalls.strings.txt"

FORBIDDEN_PATTERN='oh_adapter_stage_verified_apk|StageVerifiedApk|adapter_install_transaction|adapter journal|GameInstallPlan'
if grep -Eq "$FORBIDDEN_PATTERN" "$META_DIR/libbms.strings.txt"; then
    echo "ERROR: BMS contains a successor transaction-route marker" >&2
    grep -E "$FORBIDDEN_PATTERN" "$META_DIR/libbms.strings.txt" |
        head -80 >&2
    exit 1
fi
if grep -Eq "$FORBIDDEN_PATTERN" "$META_DIR/libinstalls.strings.txt"; then
    echo "ERROR: installs contains a successor transaction-route marker" >&2
    grep -E "$FORBIDDEN_PATTERN" "$META_DIR/libinstalls.strings.txt" |
        head -80 >&2
    exit 1
fi

(
    cd "$ARTIFACT_DIR"
    sha256sum libapk_installer.so libbms.z.so libinstalls.z.so \
        >SHA256SUMS
)
stat -c '%y %s %n' "$PROVIDER" "$BMS" "$INSTALLS" \
    >"$META_DIR/artifacts.stat.txt"
{
    printf 'result=PASS\n'
    printf 'route=fn01-r6-legacy-direct-manifest\n'
    printf 'target=OH6.1.0.31/wukong100/AArch64\n'
    printf 'finalized_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'ninja_target=libbms installs\n'
    printf 'forbidden_successor_markers=ABSENT_FROM_BMS_AND_INSTALLS\n'
    if [[ -f "$META_DIR/source-tree-sha256.txt" ]]; then
        printf 'source_tree_manifest_sha256=%s\n' \
            "$(sha256sum "$META_DIR/source-tree-sha256.txt" |
                awk '{print $1}')"
    fi
} >"$META_DIR/FINALIZATION.txt"

echo "FN01_R6_LEGACY_GENERATION_FINALIZE=PASS"
echo "ARTIFACTS=$ARTIFACT_DIR"
