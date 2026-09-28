#!/usr/bin/env bash
#
# Produce the three L02.A01 AArch64 libraries under one fresh generation root.
# This producer neither builds nor consumes ART/BCP/appspawn-x and restores the
# OpenHarmony source tree and its previous pair outputs before it exits.

set -euo pipefail
IFS=$'\n\t'
umask 022

: "${ADAPTER_ROOT:?ADAPTER_ROOT is required}"
: "${OH_ROOT:?OH_ROOT is required}"
: "${GENERATION_ROOT:?GENERATION_ROOT is required}"

EXPECTED_OH_COMMIT="ef924ea4198befa65a088863d9812b7f872e4bbc"
EXPECTED_APK_SHA256="2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
APK_INPUT="${APK_INPUT:-$ADAPTER_ROOT/out/app/HelloWorld.apk}"
BUILD_JOBS="${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}"

if [[ "$ADAPTER_ROOT" != /* || ! -d "$ADAPTER_ROOT" ||
      "$OH_ROOT" != /* || ! -d "$OH_ROOT/out/wukong100" ]]; then
    echo "ERROR: ADAPTER_ROOT and OH_ROOT must be existing absolute directories" >&2
    exit 2
fi
if [[ "$GENERATION_ROOT" != /* || -e "$GENERATION_ROOT" ]]; then
    echo "ERROR: GENERATION_ROOT must be a fresh absolute path" >&2
    exit 2
fi
if [[ ! "$BUILD_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: BUILD_JOBS must be a positive integer" >&2
    exit 2
fi

PROVIDER_BUILDER="$ADAPTER_ROOT/build/build_l02_a01_apk_installer_arm64.sh"
PAIR_BUILDER="$ADAPTER_ROOT/build/preflight_l02_a01_oh_ipc_pair.sh"
HOST_GATES="$ADAPTER_ROOT/ohos_patches/l02_a01/run_rev5_host_gates.sh"
PATCH="$ADAPTER_ROOT/ohos_patches/l02_a01/oh610_game_min_rev5.patch"
PREIMAGES="$ADAPTER_ROOT/ohos_patches/l02_a01/OH610_GAME_MIN_REV5_PREIMAGES.tsv"
READELF="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf"

for input in "$PROVIDER_BUILDER" "$PAIR_BUILDER" "$HOST_GATES" "$PATCH" \
    "$PREIMAGES" "$READELF" "$APK_INPUT"; do
    [[ -f "$input" ]] || { echo "ERROR: missing input: $input" >&2; exit 2; }
done

OH_BUNDLE_FRAMEWORK_REPO="$OH_ROOT/foundation/bundlemanager/bundle_framework"
actual_commit="$(git -C "$OH_BUNDLE_FRAMEWORK_REPO" rev-parse HEAD)"
if [[ "$actual_commit" != "$EXPECTED_OH_COMMIT" ]]; then
    echo "ERROR: OH source commit mismatch: $actual_commit" >&2
    exit 1
fi
actual_apk_sha="$(sha256sum "$APK_INPUT" | awk '{print $1}')"
if [[ "$actual_apk_sha" != "$EXPECTED_APK_SHA256" ]]; then
    echo "ERROR: HelloWorld APK identity mismatch: $actual_apk_sha" >&2
    exit 1
fi

mkdir -p "$GENERATION_ROOT/meta" "$GENERATION_ROOT/logs" \
    "$GENERATION_ROOT/artifacts" "$GENERATION_ROOT/payload"

SOURCE_COVERAGE="$GENERATION_ROOT/meta/source-coverage.tsv"
{
    printf 'sha256\trole\n'
    printf '%s\toh/repo-commit\n' \
        "$(printf '%s' "$actual_commit" | sha256sum | awk '{print $1}')"
    while IFS=$'\t' read -r digest path; do
        [[ "$digest" == "sha256" ]] && continue
        printf '%s\toh/%s\n' "$digest" "$path"
    done < "$PREIMAGES"
    for input in \
        "$PROVIDER_BUILDER" \
        "$PAIR_BUILDER" \
        "$HOST_GATES" \
        "$PATCH" \
        "$PREIMAGES" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_manifest_parser.cpp" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_manifest_parser.h" \
        "$ADAPTER_ROOT/framework/package-manager/jni/axml_parser.cpp" \
        "$ADAPTER_ROOT/framework/package-manager/jni/axml_parser.h" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_verify_result.cpp" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_verify_result.h" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_verifier_client.cpp" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_verifier_client.h" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_signature_verifier.cpp" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_signature_verifier.h" \
        "$ADAPTER_ROOT/framework/package-manager/jni/game_install_plan_v1.cpp" \
        "$ADAPTER_ROOT/framework/package-manager/jni/game_install_plan_v1.h" \
        "$ADAPTER_ROOT/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp" \
        "$ADAPTER_ROOT/framework/package-manager/jni/apk_verified_session_c_api.h" \
        "$ADAPTER_ROOT/framework/package-manager/jni/native_payload_inspector.h" \
        "$APK_INPUT"; do
        relative="${input#"$ADAPTER_ROOT"/}"
        printf '%s\tadapter/%s\n' "$(sha256sum "$input" | awk '{print $1}')" "$relative"
    done
} > "$SOURCE_COVERAGE"

coverage_sha="$(sha256sum "$SOURCE_COVERAGE" | awk '{print $1}')"
printf '%s\n' "$coverage_sha" > "$GENERATION_ROOT/meta/l01-approved-identity.sha256"
printf '%s\n' "$actual_commit" > "$GENERATION_ROOT/meta/oh-repo-commit.txt"

OH_ROOT="$OH_ROOT" "$HOST_GATES" > "$GENERATION_ROOT/logs/host-gates.log" 2>&1

ADAPTER_ROOT="$ADAPTER_ROOT" OH_ROOT="$OH_ROOT" \
GENERATION_ROOT="$GENERATION_ROOT/provider" BUILD_JOBS="$BUILD_JOBS" \
    "$PROVIDER_BUILDER" > "$GENERATION_ROOT/logs/provider-build.log" 2>&1

ADAPTER_ROOT="$ADAPTER_ROOT" OH_ROOT="$OH_ROOT" \
GENERATION_ROOT="$GENERATION_ROOT/pair" BUILD_JOBS="$BUILD_JOBS" \
    "$PAIR_BUILDER" > "$GENERATION_ROOT/logs/pair-build.log" 2>&1

cp -a "$GENERATION_ROOT/provider/artifacts/libapk_installer.so" \
    "$GENERATION_ROOT/artifacts/libapk_installer.so"
cp -a "$GENERATION_ROOT/pair/artifacts/libbms.z.so" \
    "$GENERATION_ROOT/artifacts/libbms.z.so"
cp -a "$GENERATION_ROOT/pair/artifacts/libinstalls.z.so" \
    "$GENERATION_ROOT/artifacts/libinstalls.z.so"
cp -a "$APK_INPUT" "$GENERATION_ROOT/payload/HelloWorld.apk"

for artifact in "$GENERATION_ROOT"/artifacts/*.so; do
    name="$(basename "$artifact")"
    "$READELF" -h -n -d -Ws "$artifact" > "$GENERATION_ROOT/meta/$name.readelf.txt"
    grep -q 'Class:.*ELF64' "$GENERATION_ROOT/meta/$name.readelf.txt"
    grep -q 'Machine:.*AArch64' "$GENERATION_ROOT/meta/$name.readelf.txt"
    grep -q 'Build ID:' "$GENERATION_ROOT/meta/$name.readelf.txt"
done

sha256sum "$GENERATION_ROOT"/artifacts/*.so \
    "$GENERATION_ROOT/payload/HelloWorld.apk" \
    > "$GENERATION_ROOT/meta/artifacts.sha256"
sha256sum "$GENERATION_ROOT"/logs/*.log > "$GENERATION_ROOT/meta/logs.sha256"

cat > "$GENERATION_ROOT/meta/deploy-manifest.tsv" <<'EOF'
artifact	device_path
libapk_installer.so	/system/lib64/libapk_installer.so
libbms.z.so	/system/lib64/libbms.z.so
libinstalls.z.so	/system/lib64/libinstalls.z.so
EOF
cat > "$GENERATION_ROOT/meta/rollback-manifest.tsv" <<'EOF'
device_path	restore_rule
/system/lib64/libapk_installer.so	remove_if_prestate_absent
/system/lib64/libbms.z.so	restore_exact_prestate_bytes
/system/lib64/libinstalls.z.so	restore_exact_prestate_bytes
EOF

echo "SAME_GENERATION_BUILD_PASS $GENERATION_ROOT"
echo "L01_APPROVED_IDENTITY_SHA256=$coverage_sha"
cat "$GENERATION_ROOT/meta/artifacts.sha256"
