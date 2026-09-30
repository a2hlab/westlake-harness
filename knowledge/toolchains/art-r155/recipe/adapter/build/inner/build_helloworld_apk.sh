#!/bin/bash
# Canonical, host-only HelloWorld APK build gate.
#
# Product source/resource inputs are restricted to this adapter. Android SDK
# and JBR paths are toolchain inputs only; none of their classes/resources are
# copied into the APK except the standard Android packaging metadata produced
# by aapt2/d8/apksigner.

set -Eeuo pipefail

TASK_ID="HELLOWORLD-G1-CANONICAL-BUILD-20260801-01"
EXPECTED_ROOT="/Volumes/Bridge/src/adapter"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
APP_ROOT="$ADAPTER_ROOT/app"
OUT_ROOT="$ADAPTER_ROOT/out/app"
WORK_ROOT="$OUT_ROOT/.build-helloworld"

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/Users/alexyang/Backups/10.Project/16-WestLake/16.12-HanBing/aosp}"
BUILD_TOOLS_VERSION="${BUILD_TOOLS_VERSION:-aosp14-current-darwin}"
ANDROID_PLATFORM="${ANDROID_PLATFORM:-android-34}"
JAVA_HOME="${JAVA_HOME:-/Users/alexyang/Backups/10.Project/16-WestLake/16.12-HanBing/aosp/prebuilts/jdk/jdk17/darwin-arm64/Contents/Home}"
BUILD_TOOLS="${ANDROID_BUILD_TOOLS_ROOT:-$ANDROID_SDK_ROOT/prebuilts/sdk/tools/darwin}"
BUILD_TOOLS_BIN="${ANDROID_BUILD_TOOLS_BIN:-$BUILD_TOOLS/bin}"
ANDROID_JAR="${ANDROID_JAR:-$ANDROID_SDK_ROOT/prebuilts/sdk/current/public/android.jar}"

AAPT2="$BUILD_TOOLS_BIN/aapt2"
AAPT="$BUILD_TOOLS_BIN/aapt"
D8="$BUILD_TOOLS_BIN/d8"
ZIPALIGN="$BUILD_TOOLS_BIN/zipalign"
APKSIGNER="$BUILD_TOOLS_BIN/apksigner"
D8_JAR="$BUILD_TOOLS/lib/d8.jar"
APKSIGNER_JAR="$BUILD_TOOLS/lib/apksigner.jar"
OH_CLANG="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/clang"
JAVAC="$JAVA_HOME/bin/javac"
JAVA="$JAVA_HOME/bin/java"
JAR="$JAVA_HOME/bin/jar"
KEYTOOL="$JAVA_HOME/bin/keytool"
ZIP_BIN="/usr/bin/zip"
UNZIP_BIN="/usr/bin/unzip"
FILE_BIN="/usr/bin/file"
SHASUM_BIN="/usr/bin/shasum"

APK="$OUT_ROOT/HelloWorld.apk"
KEYSTORE="$OUT_ROOT/helloworld-debug.keystore"
LEGACY_APK="$OUT_ROOT/hello2.apk"
BUILD_LOG="$OUT_ROOT/BUILD.log"
RECEIPT="$OUT_ROOT/BUILD_RECEIPT.md"
INPUT_MANIFEST="$OUT_ROOT/PRODUCT_INPUTS.sha256"
TOOLCHAIN_MANIFEST="$OUT_ROOT/TOOLCHAIN.tsv"
ARTIFACT_MANIFEST="$OUT_ROOT/ARTIFACTS.sha256"
BADGING="$OUT_ROOT/APK_BADGING.txt"
MANIFEST_DUMP="$OUT_ROOT/ANDROID_MANIFEST.txt"
LAYOUT_DUMP="$OUT_ROOT/ACTIVITY_MAIN_LAYOUT.txt"
SIGNATURE_REPORT="$OUT_ROOT/SIGNATURE.txt"
ARCHIVE_LIST="$OUT_ROOT/APK_CONTENTS.txt"
FIRST_FAILURE_FILE="$OUT_ROOT/FIRST_FAILURE.txt"

CURRENT_STAGE="preflight"
CURRENT_COMMAND="preflight"
GIT_HEAD="not_available"
GIT_STATUS_COUNT="not_available"

sha256() {
    "$SHASUM_BIN" -a 256 "$1" | awk '{print $1}'
}

require_file() {
    if [ ! -f "$1" ]; then
        echo "ERROR: required file missing: $1" >&2
        return 1
    fi
}

require_exec() {
    if [ ! -x "$1" ]; then
        echo "ERROR: required executable missing: $1" >&2
        return 1
    fi
}

one_line_version() {
    "$@" 2>&1 | awk 'NF { gsub(/[\t\r\n]+/, " "); print; exit }'
}

write_receipt() {
    local status="$1"
    local exit_code="$2"
    local apk_sha="not_generated"
    local key_sha="not_generated"
    local signer_sha="not_generated"
    local first_failure="none"

    [ -f "$APK" ] && apk_sha="$(sha256 "$APK")"
    [ -f "$KEYSTORE" ] && key_sha="$(sha256 "$KEYSTORE")"
    if [ -f "$SIGNATURE_REPORT" ]; then
        signer_sha="$(awk -F': ' '/Signer #1 certificate SHA-256 digest:/ {print $2; exit}' "$SIGNATURE_REPORT")"
        [ -n "$signer_sha" ] || signer_sha="not_reported"
    fi
    if [ -f "$FIRST_FAILURE_FILE" ]; then
        first_failure="$(sed -n '1p' "$FIRST_FAILURE_FILE")"
    fi

    {
        echo "# HelloWorld APK Build Receipt"
        echo
        echo "- Task-ID: $TASK_ID"
        echo "- Status: $status"
        echo "- Exit code: $exit_code"
        echo "- Exact command: bash build/inner/build_helloworld_apk.sh"
        echo "- Canonical root: $ADAPTER_ROOT"
        echo "- Git HEAD: $GIT_HEAD"
        echo "- Scoped dirty-entry count before build: $GIT_STATUS_COUNT"
        echo "- Last stage: $CURRENT_STAGE"
        echo "- Last command: $CURRENT_COMMAND"
        echo
        echo "## Boundary"
        echo
        echo "Package/Resource + host Device/Tooling only. Product inputs are restricted to app/** and this build recipe under the canonical adapter. No device, install, deploy, reboot, external product source, external APK, or external packaged library is consumed."
        echo
        echo "## Evidence target"
        echo
        echo "A clean, repeatable host build of the canonical HelloWorld Java/resources into a signed APK with package, launcher activity, archive, alignment, and signing identity checks."
        echo
        echo "## Environment"
        echo
        echo "- Host: $(uname -srm)"
        echo "- Android SDK: $ANDROID_SDK_ROOT"
        echo "- Build tools: $BUILD_TOOLS_VERSION"
        echo "- Android platform: $ANDROID_PLATFORM"
        echo "- Java home: $JAVA_HOME"
        echo "- Product input manifest: $INPUT_MANIFEST"
        echo "- Toolchain manifest: $TOOLCHAIN_MANIFEST"
        echo "- Build log: $BUILD_LOG"
        echo
        echo "## Status"
        echo
        if [ "$status" = "build_pass" ]; then
            echo "- build_pass: true"
        else
            echo "- build_pass: false"
        fi
        echo "- stub: false for the build gate; runtime behavior was not exercised"
        echo "- real_impl: not claimed for adapter/runtime behavior"
        echo "- device_verified: false"
        echo
        echo "## Proven"
        echo
        if [ "$status" = "build_pass" ]; then
            echo "- Canonical HelloWorld sources/resources compile and package successfully with the pinned toolchain."
            echo "- APK SHA-256: $apk_sha"
            echo "- Debug keystore SHA-256: $key_sha"
            echo "- Signer certificate SHA-256: $signer_sha"
            echo "- Package: com.example.helloworld"
            echo "- Launcher activity: com.example.helloworld.MainActivity"
            echo "- minSdk/targetSdk: 21/34"
            echo "- zipalign and apksigner verification passed."
        else
            echo "- The failure is reproducible through the exact command above and is preserved in BUILD.log/FIRST_FAILURE.txt."
        fi
        echo
        echo "## Not proven"
        echo
        echo "- Adapter ARM64 generation build, deployment, installation, production-init ownership, truly-cold fork, onCreate, rendering, input, and no-crash duration are not tested."
        echo "- Host build_pass is not device_verified."
        echo
        echo "## Failed"
        echo
        if [ "$status" = "build_pass" ]; then
            echo "- None in this host APK build gate."
        else
            echo "- First failure: $first_failure"
            echo "- Failure stage: $CURRENT_STAGE"
            echo "- Failure command: $CURRENT_COMMAND"
        fi
        echo
        echo "## Next evidence"
        echo
        if [ "$status" = "build_pass" ]; then
            echo "- Bind this APK SHA to a same-generation ARM64 adapter build receipt; only then may the assigned D600 owner perform install and Enforcing production-init truly-cold verification."
        else
            echo "- Fix only the recorded first build failure, then rerun this exact command once; do not move to device work."
        fi
        echo
        echo "## Shim/stub/bypass inventory"
        echo
        echo "- None added. No Java business semantics were changed. The generated signing key is a local debug-build credential, not a security or installation bypass."
        echo
        echo "## Design-check five questions"
        echo
        echo "1. ART/class_linker/vtable semantics changed? No."
        echo "2. BCP Java semantics/classes/method bodies changed? No."
        echo "3. Adapter fix placed outside the boundary layer? No adapter runtime fix was made; this is a package build gate only."
        echo "4. libart/BCP change without coherent 27-segment bake? Not applicable; neither changed."
        echo "5. Enforcing reboot + APPSPAWNX_NO_JIT truly-cold verified? No; explicitly NOT_PROVEN and outside this task."
        echo "J. Java adapter implementation replaced with a stub? No. APK package/log/UI identity strings changed to the frozen HelloWorld identity; adapter Java code did not change."
        echo
        echo "## Memory / Skill / CI / Review updates"
        echo
        echo "- Memory: no global memory write; this receipt and staircase manifest are the task-local recovery point."
        echo "- Skill: westlake-engineering-discipline and design-check evidence/status vocabulary applied."
        echo "- CI: this script is the canonical repeatable host APK gate; no network access is required."
        echo "- Review: require PRODUCT_INPUTS.sha256, TOOLCHAIN.tsv, APK identity reports, and this receipt before promotion."
    } > "$RECEIPT"
}

on_error() {
    local line="$1"
    local exit_code="$2"
    trap - ERR
    sleep 0.1
    local first_failure
    first_failure="$(awk '/(^|[[:space:]])(error:|ERROR:|FAIL:|failed|Exception)/ {print; exit}' "$BUILD_LOG" 2>/dev/null || true)"
    [ -n "$first_failure" ] || first_failure="stage=$CURRENT_STAGE line=$line command=$CURRENT_COMMAND exit=$exit_code"
    printf '%s\n' "$first_failure" > "$FIRST_FAILURE_FILE"
    write_receipt "build_failed" "$exit_code"
    echo "BUILD_FAILED stage=$CURRENT_STAGE line=$line exit=$exit_code"
    echo "FIRST_FAILURE=$first_failure"
    exit "$exit_code"
}

if [ "$ADAPTER_ROOT" != "$EXPECTED_ROOT" ]; then
    echo "ERROR: canonical root mismatch: expected $EXPECTED_ROOT, got $ADAPTER_ROOT" >&2
    exit 2
fi

mkdir -p "$OUT_ROOT"
rm -rf "$WORK_ROOT"
rm -f "$APK" "$BUILD_LOG" "$RECEIPT" "$INPUT_MANIFEST" \
      "$TOOLCHAIN_MANIFEST" "$ARTIFACT_MANIFEST" "$BADGING" \
      "$MANIFEST_DUMP" "$LAYOUT_DUMP" "$SIGNATURE_REPORT" "$ARCHIVE_LIST" \
      "$FIRST_FAILURE_FILE"
mkdir -p "$WORK_ROOT/classes" "$WORK_ROOT/gen" "$WORK_ROOT/dex"

if [ -f "$LEGACY_APK" ]; then
    legacy_sha=$(sha256 "$LEGACY_APK")
    legacy_root="$OUT_ROOT/legacy"
    legacy_target="$legacy_root/hello2-$legacy_sha.apk"
    mkdir -p "$legacy_root"
    if [ -e "$legacy_target" ]; then
        [ "$(sha256 "$legacy_target")" = "$legacy_sha" ] || {
            echo "ERROR: legacy archive identity collision: $legacy_target" >&2
            exit 2
        }
        rm -f "$LEGACY_APK"
    else
        mv "$LEGACY_APK" "$legacy_target"
    fi
fi

exec > >(tee "$BUILD_LOG") 2>&1
trap 'rc=$?; on_error "$LINENO" "$rc"' ERR

echo "TASK_ID=$TASK_ID"
echo "BOUNDARY=canonical_workspace_host_only"
echo "CANONICAL_ROOT=$ADAPTER_ROOT"

if git -C "$ADAPTER_ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
    GIT_HEAD="$(git -C "$ADAPTER_ROOT" rev-parse HEAD)"
    GIT_STATUS_COUNT="$(git -C "$ADAPTER_ROOT" status --short -- app build/inner/build_helloworld_apk.sh _arch_impl/_manifest/bringup_staircase.md | wc -l | tr -d ' ')"
fi

CURRENT_STAGE="toolchain-preflight"
CURRENT_COMMAND="verify pinned Android SDK and JBR tools"
for tool in "$AAPT2" "$AAPT" "$D8" "$ZIPALIGN" "$APKSIGNER" \
            "$JAVAC" "$JAVA" "$JAR" "$KEYTOOL" "$ZIP_BIN" \
            "$UNZIP_BIN" "$FILE_BIN" "$SHASUM_BIN"; do
    require_exec "$tool"
done
require_file "$ANDROID_JAR"
require_file "$D8_JAR"
require_file "$APKSIGNER_JAR"
require_file "$OH_CLANG"
require_file "$APP_ROOT/native/hello_world_abi_marker.c"
require_file "$APP_ROOT/AndroidManifest.xml"

EXPECTED_JAVA_ROOT="$APP_ROOT/java/com/example/helloworld"
[ -d "$EXPECTED_JAVA_ROOT" ] || {
    echo "ERROR: canonical Java package directory missing: $EXPECTED_JAVA_ROOT" >&2
    exit 3
}
legacy_identity_found=0
while IFS= read -r -d '' text_input; do
    case "$text_input" in
        *.java|*.xml|*.c|*.cc|*.cpp|*.h|*.hpp|*.txt|*.properties)
            if grep -n -i -F "hello2" "$text_input"; then
                legacy_identity_found=1
            fi
            ;;
    esac
done < <(find "$APP_ROOT" -type f -print0)
if [ "$legacy_identity_found" -ne 0 ]; then
    echo "ERROR: legacy hello2 identity remains in textual app product inputs" >&2
    exit 3
fi
grep -Fq 'android:text="HelloWorld"' "$APP_ROOT/res/layout/activity_main.xml" || {
    echo "ERROR: canonical HelloWorld layout title missing" >&2
    exit 3
}
grep -Fq 'android:text="Hello World!"' "$APP_ROOT/res/layout/activity_main.xml" || {
    echo "ERROR: canonical HelloWorld layout content missing" >&2
    exit 3
}
if find "$APP_ROOT/java" -type f -name '*.java' ! -path "$EXPECTED_JAVA_ROOT/*" -print | grep -q .; then
    echo "ERROR: Java source escaped canonical package directory" >&2
    exit 3
fi
while IFS= read -r java_source; do
    grep -Fq "package com.example.helloworld;" "$java_source" || {
        echo "ERROR: Java package declaration mismatch: $java_source" >&2
        exit 3
    }
done < <(find "$EXPECTED_JAVA_ROOT" -type f -name '*.java' -print | LC_ALL=C sort)

if find "$APP_ROOT" -type l -print | grep -q .; then
    echo "ERROR: symlinked product inputs are forbidden under $APP_ROOT" >&2
    exit 3
fi

CURRENT_STAGE="product-input-manifest"
CURRENT_COMMAND="hash canonical app inputs and build recipe"
{
    echo "$APP_ROOT/AndroidManifest.xml"
    find "$APP_ROOT/java" "$APP_ROOT/res" -type f -print
    echo "$SCRIPT_DIR/build_helloworld_apk.sh"
} | LC_ALL=C sort -u > "$WORK_ROOT/product-input-paths.txt"

: > "$INPUT_MANIFEST"
while IFS= read -r input; do
    case "$input" in
        "$ADAPTER_ROOT"/*) ;;
        *) echo "ERROR: product input escaped canonical adapter: $input" >&2; exit 4 ;;
    esac
    require_file "$input"
    printf '%s  %s\n' "$(sha256 "$input")" "${input#$ADAPTER_ROOT/}" >> "$INPUT_MANIFEST"
done < "$WORK_ROOT/product-input-paths.txt"

CURRENT_STAGE="toolchain-manifest"
CURRENT_COMMAND="record toolchain paths versions and SHA-256"
{
    printf 'role\tpath\tsha256\tversion\n'
    printf 'android-platform\t%s\t%s\t%s\n' "$ANDROID_JAR" "$(sha256 "$ANDROID_JAR")" "$ANDROID_PLATFORM"
    printf 'aapt2\t%s\t%s\t%s\n' "$AAPT2" "$(sha256 "$AAPT2")" "$(one_line_version "$AAPT2" version)"
    printf 'aapt\t%s\t%s\t%s\n' "$AAPT" "$(sha256 "$AAPT")" "$(one_line_version "$AAPT" version)"
    printf 'd8-wrapper\t%s\t%s\t%s\n' "$D8" "$(sha256 "$D8")" "AOSP tree wrapper (recorded, not invoked)"
    printf 'd8-jar\t%s\t%s\t%s\n' "$D8_JAR" "$(sha256 "$D8_JAR")" "$(one_line_version "$JAVA" -jar "$D8_JAR" --version)"
    printf 'zipalign\t%s\t%s\t%s\n' "$ZIPALIGN" "$(sha256 "$ZIPALIGN")" "$BUILD_TOOLS_VERSION"
    printf 'apksigner-wrapper\t%s\t%s\t%s\n' "$APKSIGNER" "$(sha256 "$APKSIGNER")" "AOSP tree wrapper (recorded, not invoked)"
    printf 'apksigner-jar\t%s\t%s\t%s\n' "$APKSIGNER_JAR" "$(sha256 "$APKSIGNER_JAR")" "$(one_line_version "$JAVA" -jar "$APKSIGNER_JAR" --version)"
    printf 'oh-clang\t%s\t%s\t%s\n' "$OH_CLANG" "$(sha256 "$OH_CLANG")" "$(one_line_version "$OH_CLANG" --version)"
    printf 'javac\t%s\t%s\t%s\n' "$JAVAC" "$(sha256 "$JAVAC")" "$(one_line_version "$JAVAC" -version)"
    printf 'java\t%s\t%s\t%s\n' "$JAVA" "$(sha256 "$JAVA")" "$(one_line_version "$JAVA" -version)"
    printf 'jar\t%s\t%s\t%s\n' "$JAR" "$(sha256 "$JAR")" "JBR jar"
    printf 'keytool\t%s\t%s\t%s\n' "$KEYTOOL" "$(sha256 "$KEYTOOL")" "JBR keytool"
    printf 'zip\t%s\t%s\t%s\n' "$ZIP_BIN" "$(sha256 "$ZIP_BIN")" "macOS system zip"
    printf 'unzip\t%s\t%s\t%s\n' "$UNZIP_BIN" "$(sha256 "$UNZIP_BIN")" "macOS system unzip"
} > "$TOOLCHAIN_MANIFEST"

CURRENT_STAGE="resource-compile"
CURRENT_COMMAND="aapt2 compile canonical app/res"
"$AAPT2" compile --dir "$APP_ROOT/res" -o "$WORK_ROOT/compiled-res.zip"

CURRENT_STAGE="resource-link"
CURRENT_COMMAND="aapt2 link manifest/resources and generate R.java"
"$AAPT2" link \
    -I "$ANDROID_JAR" \
    --manifest "$APP_ROOT/AndroidManifest.xml" \
    --min-sdk-version 21 \
    --target-sdk-version 34 \
    --version-code 1 \
    --version-name 1.0 \
    --java "$WORK_ROOT/gen" \
    -o "$WORK_ROOT/resources-unsigned.apk" \
    "$WORK_ROOT/compiled-res.zip"

CURRENT_STAGE="java-compile"
CURRENT_COMMAND="javac canonical five Java classes plus generated R.java"
find "$APP_ROOT/java" "$WORK_ROOT/gen" -type f -name '*.java' -print | LC_ALL=C sort > "$WORK_ROOT/java-sources.txt"
"$JAVAC" \
    -encoding UTF-8 \
    -parameters \
    -source 8 \
    -target 8 \
    -bootclasspath "$ANDROID_JAR" \
    -d "$WORK_ROOT/classes" \
    @"$WORK_ROOT/java-sources.txt"

CURRENT_STAGE="dex"
CURRENT_COMMAND="jar compiled classes and run d8 min-api 21"
"$JAR" cf "$WORK_ROOT/classes.jar" -C "$WORK_ROOT/classes" .
"$JAVA" -jar "$D8_JAR" \
    --lib "$ANDROID_JAR" \
    --min-api 21 \
    --output "$WORK_ROOT/dex" \
    "$WORK_ROOT/classes.jar"
require_file "$WORK_ROOT/dex/classes.dex"

CURRENT_STAGE="apk-assemble"
CURRENT_COMMAND="build inert arm64 ABI marker and add classes.dex plus lib/arm64-v8a"
"$OH_CLANG" --target=aarch64-linux-ohos -fPIC -fvisibility=hidden \
    -nostdlib -shared -Wl,-z,defs -Wl,--build-id=sha1 \
    -Wl,-soname,libwestlake_hello_abi.so \
    "$APP_ROOT/native/hello_world_abi_marker.c" \
    -o "$WORK_ROOT/libwestlake_hello_abi.so"
mkdir -p "$WORK_ROOT/apk-payload/lib/arm64-v8a"
cp "$WORK_ROOT/dex/classes.dex" "$WORK_ROOT/apk-payload/classes.dex"
cp "$WORK_ROOT/libwestlake_hello_abi.so" \
    "$WORK_ROOT/apk-payload/lib/arm64-v8a/libwestlake_hello_abi.so"
cp "$WORK_ROOT/resources-unsigned.apk" "$WORK_ROOT/HelloWorld-unaligned.apk"
(cd "$WORK_ROOT/apk-payload" && "$ZIP_BIN" -X -q -r "$WORK_ROOT/HelloWorld-unaligned.apk" classes.dex lib)

CURRENT_STAGE="zipalign"
CURRENT_COMMAND="zipalign APK to four-byte boundaries"
"$ZIPALIGN" -f -p 4 "$WORK_ROOT/HelloWorld-unaligned.apk" "$WORK_ROOT/HelloWorld-aligned.apk"
"$ZIPALIGN" -c -p 4 "$WORK_ROOT/HelloWorld-aligned.apk"

CURRENT_STAGE="signing-key"
CURRENT_COMMAND="reuse or generate canonical out/app debug signing key"
if [ ! -f "$KEYSTORE" ]; then
    "$KEYTOOL" -genkeypair \
        -keystore "$KEYSTORE" \
        -storetype PKCS12 \
        -storepass android \
        -keypass android \
        -alias helloworld-debug \
        -keyalg RSA \
        -keysize 2048 \
        -validity 36500 \
        -dname "CN=WestLake HelloWorld Debug,O=WestLake,C=CN" \
        -noprompt
fi

CURRENT_STAGE="apk-sign"
CURRENT_COMMAND="apksigner sign aligned APK"
"$JAVA" -jar "$APKSIGNER_JAR" sign \
    --ks "$KEYSTORE" \
    --ks-key-alias helloworld-debug \
    --ks-pass pass:android \
    --key-pass pass:android \
    --v3-signing-enabled false \
    --v4-signing-enabled false \
    --out "$APK" \
    "$WORK_ROOT/HelloWorld-aligned.apk"

CURRENT_STAGE="artifact-verify"
CURRENT_COMMAND="verify signature alignment package activity manifest and archive"
"$JAVA" -jar "$APKSIGNER_JAR" verify --verbose --print-certs "$APK" > "$SIGNATURE_REPORT"
"$ZIPALIGN" -c -p 4 "$APK"
"$AAPT2" dump badging "$APK" > "$BADGING"
"$AAPT2" dump xmltree --file AndroidManifest.xml "$APK" > "$MANIFEST_DUMP"
"$AAPT2" dump xmltree --file res/layout/activity_main.xml "$APK" > "$LAYOUT_DUMP"
"$UNZIP_BIN" -Z1 "$APK" > "$ARCHIVE_LIST"

grep -Fq "package: name='com.example.helloworld' versionCode='1' versionName='1.0'" "$BADGING"
grep -Fq "sdkVersion:'21'" "$BADGING"
grep -Fq "targetSdkVersion:'34'" "$BADGING"
grep -Fq "launchable-activity: name='com.example.helloworld.MainActivity'" "$BADGING"
grep -Fq "HelloWorld" "$LAYOUT_DUMP"
grep -Fq "Hello World!" "$LAYOUT_DUMP"
grep -Fxq "classes.dex" "$ARCHIVE_LIST"
grep -Fq "res/raw/l12_testclip.mp4" "$ARCHIVE_LIST"
require_file "$APK"

CURRENT_STAGE="artifact-manifest"
CURRENT_COMMAND="hash final APK and debug signing key"
{
    printf '%s  %s\n' "$(sha256 "$APK")" "HelloWorld.apk"
    printf '%s  %s\n' "$(sha256 "$KEYSTORE")" "helloworld-debug.keystore"
} > "$ARTIFACT_MANIFEST"

CURRENT_STAGE="receipt"
CURRENT_COMMAND="write successful build receipt"
write_receipt "build_pass" 0
trap - ERR

echo "BUILD_PASS"
echo "APK=$APK"
echo "APK_SHA256=$(sha256 "$APK")"
echo "RECEIPT=$RECEIPT"
