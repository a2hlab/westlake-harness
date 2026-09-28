#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APK="$ROOT_DIR/evidence/fixtures/unity/G2.U02/UnityHelloWorld-arm64-il2cpp.apk"
AAPT="/Applications/Unity/Hub/Editor/6000.0.80f1/PlaybackEngines/AndroidPlayer/SDK/build-tools/36.0.0/aapt"
APKSIGNER="/Applications/Unity/Hub/Editor/6000.0.80f1/PlaybackEngines/AndroidPlayer/SDK/build-tools/36.0.0/apksigner"

EXPECTED_SHA256="1b90458f6f47a6fbb39786e8f5418212a7f86a376be066851035b92fe10d59ee"
EXPECTED_SIZE="13241553"
EXPECTED_PACKAGE="com.westlake.l03a15.unityhelloworld"
EXPECTED_LABEL="UnityHelloWorld"
EXPECTED_ACTIVITY="com.unity3d.player.UnityPlayerGameActivity"
EXPECTED_CERT_SHA256="1757e80e6cb77f8dc4d4fa67805c941df57d04a411468a5402dfca77578d10e5"

usage()
{
    cat <<'EOF'
Usage: src/tools/verify_fn01_unity_arm64_input.sh [options]

Options:
  --apk PATH        APK to validate (default: frozen G2.U02 input)
  --aapt PATH       aapt binary
  --apksigner PATH  apksigner binary
  -h, --help        Show this help

The verifier is read-only. It accepts only the frozen UnityHelloWorld G2.U02
identity, including its inline manifest label, and prints a terminal PASS/FAIL
marker.
EOF
}

fail()
{
    echo "UNITY_INPUT_VERDICT=FAIL reason=$1" >&2
    exit 1
}

while (($#)); do
    case "$1" in
        --apk)
            [[ $# -ge 2 ]] || fail "MISSING_APK_ARGUMENT"
            APK="$2"
            shift 2
            ;;
        --aapt)
            [[ $# -ge 2 ]] || fail "MISSING_AAPT_ARGUMENT"
            AAPT="$2"
            shift 2
            ;;
        --apksigner)
            [[ $# -ge 2 ]] || fail "MISSING_APKSIGNER_ARGUMENT"
            APKSIGNER="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "UNKNOWN_ARGUMENT:$1"
            ;;
    esac
done

[[ -f "$APK" ]] || fail "APK_NOT_FOUND:$APK"
[[ -x "$AAPT" ]] || fail "AAPT_NOT_EXECUTABLE:$AAPT"
[[ -x "$APKSIGNER" ]] || fail "APKSIGNER_NOT_EXECUTABLE:$APKSIGNER"

ACTUAL_SIZE="$(wc -c < "$APK" | tr -d '[:space:]')"
[[ "$ACTUAL_SIZE" == "$EXPECTED_SIZE" ]] || fail "APK_SIZE_MISMATCH:$ACTUAL_SIZE"

ACTUAL_SHA256="$(shasum -a 256 "$APK" | awk '{print $1}')"
[[ "$ACTUAL_SHA256" == "$EXPECTED_SHA256" ]] || fail "APK_IDENTITY_MISMATCH:$ACTUAL_SHA256"

unzip -tqq "$APK" >/dev/null || fail "ZIP_INTEGRITY_FAILED"

BADGING="$("$AAPT" dump badging "$APK")"
grep -Fq "package: name='$EXPECTED_PACKAGE' versionCode='1' versionName='1.0'" <<<"$BADGING" \
    || fail "PACKAGE_OR_VERSION_MISMATCH"
grep -Fq "application-label:'$EXPECTED_LABEL'" <<<"$BADGING" \
    || fail "APPLICATION_LABEL_MISMATCH"
grep -Fq "launchable-activity: name='$EXPECTED_ACTIVITY'" <<<"$BADGING" \
    || fail "LAUNCHABLE_ACTIVITY_MISMATCH"
grep -Fq "native-code: 'arm64-v8a'" <<<"$BADGING" \
    || fail "NATIVE_ABI_MISMATCH"

MANIFEST_TREE="$("$AAPT" dump xmltree "$APK" AndroidManifest.xml)"
grep -Fq 'A: android:label(0x01010001)="UnityHelloWorld" (Raw: "UnityHelloWorld")' \
    <<<"$MANIFEST_TREE" || fail "APPLICATION_LABEL_NOT_INLINE"

SIGNATURE_OUTPUT="$("$APKSIGNER" verify --verbose --print-certs "$APK" 2>&1)" \
    || fail "APK_SIGNATURE_VERIFY_FAILED"
grep -Fq "Verified using v2 scheme (APK Signature Scheme v2): true" <<<"$SIGNATURE_OUTPUT" \
    || fail "V2_SIGNATURE_REQUIRED"
grep -Fq "Signer #1 certificate SHA-256 digest: $EXPECTED_CERT_SHA256" <<<"$SIGNATURE_OUTPUT" \
    || fail "SIGNER_CERT_MISMATCH"

ENTRY_SPECS=(
    "lib/arm64-v8a/libc++_shared.so|4397241b4bd20a8e579bfb41d21107857e12985f6a01ca0c2a5f83380d1270b4"
    "lib/arm64-v8a/libgame.so|0f7819f624f8761048da4035ee4a47cb7f910687d5d96ec4ca7dbd5dc10084e7"
    "lib/arm64-v8a/libmain.so|db864f23088195e79a6869b876f2f357249515be240a7cec23c2455deac3146a"
    "lib/arm64-v8a/libunity.so|21b03d9771267751a7916a889dec38183e93a3155e28988a8c6e522e3dd2db96"
    "lib/arm64-v8a/libil2cpp.so|5a42ecc7e70ff4728eea39016707849cdbc997698f66700aa0ca066660b96e1f"
    "lib/arm64-v8a/libswappywrapper.so|be6fe5f369c91658aede1b48a9506d3a1cfa476f81c4f0794dc8cf53fb66c083"
)

for SPEC in "${ENTRY_SPECS[@]}"; do
    ENTRY="${SPEC%%|*}"
    EXPECTED_ENTRY_SHA="${SPEC#*|}"
    unzip -Z1 "$APK" | grep -Fx "$ENTRY" >/dev/null || fail "NATIVE_ENTRY_MISSING:$ENTRY"
    ACTUAL_ENTRY_SHA="$(unzip -p "$APK" "$ENTRY" | shasum -a 256 | awk '{print $1}')"
    [[ "$ACTUAL_ENTRY_SHA" == "$EXPECTED_ENTRY_SHA" ]] \
        || fail "NATIVE_ENTRY_IDENTITY_MISMATCH:$ENTRY:$ACTUAL_ENTRY_SHA"
    ZIP_METHOD="$(zipinfo -l "$APK" "$ENTRY" | awk -v entry="$ENTRY" '$NF == entry {print $(NF-3)}')"
    [[ "$ZIP_METHOD" == def* ]] || fail "NATIVE_ENTRY_EXPECTED_DEFLATE:$ENTRY:$ZIP_METHOD"
    echo "NATIVE_ENTRY_OK path=$ENTRY sha256=$ACTUAL_ENTRY_SHA zip_method=$ZIP_METHOD"
done

ACTUAL_NATIVE_COUNT="$(unzip -Z1 "$APK" | grep -Ec '^lib/arm64-v8a/[^/]+\.so$')"
[[ "$ACTUAL_NATIVE_COUNT" == "6" ]] \
    || fail "NATIVE_ENTRY_COUNT_MISMATCH:$ACTUAL_NATIVE_COUNT"

echo "APK_PATH=$APK"
echo "APK_SIZE=$ACTUAL_SIZE"
echo "APK_SHA256=$ACTUAL_SHA256"
echo "PACKAGE=$EXPECTED_PACKAGE"
echo "APPLICATION_LABEL=$EXPECTED_LABEL"
echo "ACTIVITY=$EXPECTED_ACTIVITY"
echo "SIGNER_CERT_SHA256=$EXPECTED_CERT_SHA256"
echo "NATIVE_ENTRY_COUNT=$ACTUAL_NATIVE_COUNT"
echo "APPLICATION_LABEL_ENCODING=inline_string"
echo "UNITY_INPUT_VERDICT=PASS artifact=G2.U02"
