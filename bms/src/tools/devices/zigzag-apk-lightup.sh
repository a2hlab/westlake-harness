#!/usr/bin/env bash
# Local-only ZigZag APK build/deploy/trace loop for accepted direct boards.
# Generated binaries live under .bridge-payload/ and are never Git inputs.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
TOOLS_ROOT="$ROOT/src/tools"
EVIDENCE_ROOT="$ROOT/var/evidence"

first_existing_file()
{
    local candidate
    for candidate in "$@"; do
        if [ -f "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    printf '%s\n' "$1"
}

ADAPTER_ROOT="$ROOT/src/adapter"
PAYLOAD_ROOT="$ROOT/.bridge-payload"
HELLO_BASELINE_STAMP="$PAYLOAD_ROOT/zigzag-hello-baseline.env"
CANDIDATES_ROOT="$PAYLOAD_ROOT/zigzag-candidates"
PERSISTED_ROOT="$PAYLOAD_ROOT/zigzag-persisted"
LINK_INPUTS="${OH61_LINK_INPUTS:-$PAYLOAD_ROOT/oh61-link-inputs}"
LIBCXX_INCLUDE="$PAYLOAD_ROOT/oh61-libcxx-h/v1"
OH_SOURCE_INPUTS="$PAYLOAD_ROOT/oh-source-inputs"
WINDOW_MANAGER_SOURCE="$OH_SOURCE_INPUTS/window_window_manager"
OH61_GENERATED_HEADERS="$PAYLOAD_ROOT/oh61-generated-headers/mock-session-manager"
RAW_PR03="${RAW_PR03:-/Users/zhaoyue/orca/.bridge-payload/pr03-74e6-portable}"
AOSP_ROOT="${AOSP_ROOT:-/Users/zhaoyue/aosp-14}"
OH_ROOT="${OH_ROOT:-/Users/zhaoyue/oh}"
OH_HEADER_OUT="${OH_HEADER_OUT:-/Users/zhaoyue/oh/out/wukong100}"
OH_SDK="${OH_SDK:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}"
OH_TOOLCHAINS="${OH_TOOLCHAINS:-$(dirname "$OH_SDK")/toolchains}"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
FFMPEG_BIN="${FFMPEG_BIN:-$(command -v ffmpeg || true)}"
READELF="$OH_SDK/llvm/bin/llvm-readelf"
NM="$OH_SDK/llvm/bin/llvm-nm"
OBJDUMP="$OH_SDK/llvm/bin/llvm-objdump"
JAVA_BIN="${JAVA_BIN:-/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home/bin/java}"
JAVAC_BIN="${JAVAC_BIN:-/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home/bin/javac}"
DEV_ECO_JAVA_HOME="$(cd "$(dirname "$JAVA_BIN")/.." && pwd)"
ZIP_BIN="${ZIP_BIN:-/usr/bin/zip}"
PATCHELF_BIN="${PATCHELF_BIN:-/opt/homebrew/bin/patchelf}"
ANDROID_NDK_CLANG="${ANDROID_NDK_CLANG:-/Users/zhaoyue/Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android21-clang}"
ANDROID_COMPILE_JAR="${ANDROID_COMPILE_JAR:-/Users/zhaoyue/Library/Android/sdk/platforms/android-36/android.jar}"
APKANALYZER_BIN="${APKANALYZER_BIN:-/Users/zhaoyue/Library/Android/sdk/cmdline-tools/latest/bin/apkanalyzer}"
DEXDUMP_BIN="${DEXDUMP_BIN:-/Users/zhaoyue/Library/Android/sdk/build-tools/36.1.0/dexdump}"
ARK_DISASM_BIN="${ARK_DISASM_BIN:-$OH_TOOLCHAINS/ark_disasm}"
D8_BIN="${D8_BIN:-/Users/zhaoyue/Library/Android/sdk/build-tools/36.1.0/d8}"
D8_JAR="$(dirname "$D8_BIN")/lib/d8.jar"
PM_PROXY_SOURCE="$ADAPTER_ROOT/framework/activity/java/PackageManagerProjectionProxy.java"
PM_PROXY_COMPILE_STUB="$ADAPTER_ROOT/framework/activity/java/compile-stubs/android/content/pm/ApplicationInfo.java"
STORAGE_PROXY_SOURCE="$ADAPTER_ROOT/framework/activity/java/StorageManagerProjectionProxy.java"
USER_PROXY_SOURCE="$ADAPTER_ROOT/framework/activity/java/UserManagerProjectionProxy.java"
DISPLAY_PROXY_SOURCE="$ADAPTER_ROOT/framework/activity/java/DisplayManagerProjectionProxy.java"
CAPYBARA_LETTERBOX_SOURCE="$ADAPTER_ROOT/framework/activity/java/CapybaraLetterboxProjection.java"
MANIFEST_ORIENTATION_SOURCE="$ADAPTER_ROOT/framework/activity/java/ManifestOrientationProjection.java"
BINARY_MANIFEST_ORIENTATION_SOURCE="$ADAPTER_ROOT/framework/activity/java/BinaryAndroidManifestOrientation.java"
INPUT_EVENT_DEVICE_SOURCE="$ADAPTER_ROOT/framework/activity/java/InputEventDeviceProjection.java"
INPUT_EVENT_RECEIVER_COMPILE_STUB="$ADAPTER_ROOT/framework/activity/java/compile-stubs/android/view/InputEventReceiver.java"
AUDIO_COMPAT_BOOTSTRAP_SOURCE="$ADAPTER_ROOT/framework/activity/java/AudioCompatBootstrap.java"
PTHREAD_BRIDGE_ROOT="$ADAPTER_ROOT/framework/native-compat/bionic-pthread-bridge"
PTHREAD_BRIDGE_SOURCE="$PTHREAD_BRIDGE_ROOT/src/bionic_pthread_bridge.c"
PTHREAD_PROPERTY_SOURCE="$PTHREAD_BRIDGE_ROOT/src/bionic_property_bridge.c"
PTHREAD_BRIDGE_MAP="$PTHREAD_BRIDGE_ROOT/westlake_bionic_pthread_bridge.map"
PTHREAD_BRIDGE_HEADER="$PTHREAD_BRIDGE_ROOT/include/westlake_bionic_pthread_bridge.h"
UNITY_LIBC_STUB_SOURCE="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src/unity_libc_stubs.c"
ABORT_MESSAGE_COMPAT_SOURCE="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src/abort_message_compat.cpp"
UNITY_SIGNAL_SOURCE="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/src/unity_signal_box.c"
SIGNAL_BOX_ROOT="$ADAPTER_ROOT/framework/native-compat/bionic-signal-box"
SIGNAL_BOX_MAP="$SIGNAL_BOX_ROOT/westlake_bionic_signal_box.map"
SIGNAL_RENAME_MAP="$SIGNAL_BOX_ROOT/tuanjie_signal_symbols.map"
SIGNAL_ABI_PROBE_SOURCE="$SIGNAL_BOX_ROOT/signal_abi_probe.c"
SIGNAL_BACKEND_SOURCE="$SIGNAL_BOX_ROOT/src/oh_musl_signal_backend.c"
SIGNAL_BACKEND_HEADER="$SIGNAL_BOX_ROOT/include/westlake_musl_signal_backend.h"
MEDIANDK_PRESENCE_SOURCE="$ADAPTER_ROOT/framework/native-compat/mediandk-presence/src/mediandk_presence.c"
BASELINE_RUNTIME_LOCAL="$PAYLOAD_ROOT/device-baseline-61ae/liboh_android_runtime.so"

SMALI_CACHE="/Users/zhaoyue/.gradle/caches/modules-2/files-2.1"
SMALI_JAR="$SMALI_CACHE/org.smali/smali/2.5.2/ef0ee6a014840cf520ee5dd5fe2f7617a58399f7/smali-2.5.2.jar"
BAKSMALI_JAR="$SMALI_CACHE/org.smali/baksmali/2.5.2/1375ac2ff5531e14c308c0342703d9842602388f/baksmali-2.5.2.jar"
DEXLIB_JAR="$SMALI_CACHE/org.smali/dexlib2/2.5.2/8b664182af455b0757a7f59a42020fa5608c7d0e/dexlib2-2.5.2.jar"
SMALI_UTIL_JAR="$SMALI_CACHE/org.smali/util/2.5.2/8aca9e1ca27ac0f6b9d42a1bbd95cde9bb5e0e12/util-2.5.2.jar"
JCOMMANDER_JAR="$SMALI_CACHE/com.beust/jcommander/1.64/456a985ac9b12d34820e4d5de063b2c2fc43ed5a/jcommander-1.64.jar"
GUAVA_JAR="$SMALI_CACHE/com.google.guava/guava/27.1-android/a80ef47421d6607e749f8b7282dd7dee61adfea7/guava-27.1-android.jar"
ANTLR_JAR="$SMALI_CACHE/org.antlr/antlr/3.5.2/c4a65c950bfc3e7d04309c515b2177c00baf7764/antlr-3.5.2.jar"
ANTLR_RUNTIME_JAR="$SMALI_CACHE/org.antlr/antlr-runtime/3.5.2/cd9cd41361c155f3af0f653009dcecb08d8b4afd/antlr-runtime-3.5.2.jar"
STRINGTEMPLATE_JAR="$SMALI_CACHE/org.antlr/stringtemplate/3.2.1/59ec8083721eae215c6f3caee944c410d2be34de/stringtemplate-3.2.1.jar"
SMALI_CP="$SMALI_JAR:$BAKSMALI_JAR:$DEXLIB_JAR:$SMALI_UTIL_JAR:$JCOMMANDER_JAR:$GUAVA_JAR:$ANTLR_JAR:$ANTLR_RUNTIME_JAR:$STRINGTEMPLATE_JAR"

BOARD_ONLY="61ae0be500000000000000000324012c"
BOARD_8605="5ce2dcee00000000000000000923012c"
BOARD_5EA1="5ea1719200000000000000001123012c"
ROM_ONLY="OpenHarmony-6.1.0.31"
GENERATION="74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d"
ROUTE_TARGET="/system/lib64/westlake/route-a/$GENERATION"
ADAPTER_TARGET="/system/android/lib64/liboh_adapter_bridge.so"
PROVIDER_TARGET="$ROUTE_TARGET/libwestlake_android_runtime_provider.so"
CHILD_TARGET="/system/lib64/appspawn/libwestlake_android_child.z.so"
APPSPAWN_TARGET="/system/bin/appspawn-x"
RUNTIME_TARGET="/system/android/lib64/liboh_android_runtime.so"
RUNTIME_JAR_TARGET="/system/android/framework/oh-adapter-runtime.jar"
PTHREAD_BRIDGE_TARGET="/system/android/lib64/libwestlake_bionic_pthread_bridge.so"
NATIVE_LOADER_TARGET="/system/android/lib64/libnativeloader.so"
ROUTE_NATIVE_LOADER_TARGET="$ROUTE_TARGET/libnativeloader.so"
LIBANDROID_TARGET="/system/android/lib64/libandroid.so"
REMOTE_ROOT="/data/zigzag-apk-lightup"
REMOTE_PR03="/data/pr03-74e6-portable"

HELLO_BUNDLE="com.example.helloworld"
HELLO_ABILITY="com.example.helloworld.MainActivity"
ZIGZAG_BUNDLE="com.a2hlab.bridge.zigzag"
ZIGZAG_ABILITY="com.unity3d.player.UnityPlayerActivity"
ZIGZAG_PLAYER_PREFS="/data/app/el2/100/base/$ZIGZAG_BUNDLE/shared_prefs/$ZIGZAG_BUNDLE.v2.playerprefs.xml"
ZIGZAG_APK="$(first_existing_file \
    "$ROOT/src/vendor/samples/apks/ZigZag/project/dist/zigzag.apk" \
    "$ROOT/APKS/ZigZag/project/dist/zigzag.apk")"
ZIGZAG_SHA="aaa7c9cce4886eef1280e917fd25bf434c53065cf0bf8b5704b83738137275bc"
ZIGZAG_CONTROL_HAP="$(first_existing_file \
    "$ROOT/src/vendor/samples/haps/ZigZag/dist/zigzag-control-fmtfix.hap" \
    "$ROOT/HAPS/ZigZag/dist/zigzag-control-fmtfix.hap")"
ZIGZAG_CONTROL_HAP_SHA="cff1e79aea8312e056608c1b9c9fc57fd9e4ab66d1ae09eb5d240634f8afaaa6"
ANDROID_TUANJIE_REFERENCE="$(first_existing_file \
    "$ROOT/src/vendor/samples/haps/ZigZag/project/Library/Bee/artifacts/Android/libtuanjie/arm64-v8a/unstripped/libtuanjie.so" \
    "$ROOT/HAPS/ZigZag/project/Library/Bee/artifacts/Android/libtuanjie/arm64-v8a/unstripped/libtuanjie.so")"
ANDROID_TUANJIE_REFERENCE_SHA="528712a693ae1451ea1bfb2025b867e417a910e8c89fcf189b136de7b757e062"
ANDROID_TUANJIE_BUILD_ID="e26340e571629eaf"
OH_TUANJIE_REFERENCE="$(first_existing_file \
    "$ROOT/src/vendor/samples/haps/ZigZag/project/Library/Bee/artifacts/OpenHarmonyPlayerBuildProgram/libtuanjie/arm64-v8a/unstripped/libtuanjie.so" \
    "$ROOT/HAPS/ZigZag/project/Library/Bee/artifacts/OpenHarmonyPlayerBuildProgram/libtuanjie/arm64-v8a/unstripped/libtuanjie.so")"
OH_TUANJIE_REFERENCE_SHA="bc14f46e2c9c351dcc631a7ffa85c408cfaba19726423c5f0f35bfe47a2416dc"
OH_TUANJIE_BUILD_ID="1ab666d0b9de39b8"
ZIGZAG_LIBMAIN_RAW_SHA="b44d4efd55e713b73a35778b8e7335528f8d2011cb4d4bec17f1edd7b2a6c3ed"
ZIGZAG_LIBMAIN_TARGET="/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/lib/arm64-v8a/libmain.so"
ZIGZAG_LIBIL2CPP_RAW_SHA="74825000b3e6d3ec252755bff9c0d37de4bd8a589d5579c1009f0c1c58cf43a1"
ZIGZAG_LIBIL2CPP_TARGET="/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/lib/arm64-v8a/libil2cpp.so"
ZIGZAG_LIBTUANJIE_RAW_SHA="c5b4a64cbf91267152691710c076002b7fbe6a5c6b1f660cfc5d2af71c630783"
ZIGZAG_LIBTUANJIE_TARGET="/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/lib/arm64-v8a/libtuanjie.so"
TUANJIE_CORE_GETPROC_FILE_OFFSET="0xaaaad4"
TUANJIE_CORE_GETPROC_VADDR="0xaaead4"
TUANJIE_CORE_GETPROC_OLD_HEX="fe0f1ef8"
TUANJIE_CORE_GETPROC_EGL_HEX="11000014"
ZIGZAG_MEDIANDK_TARGET="/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/lib/arm64-v8a/libmediandk.so"
ZIGZAG_SIGNAL_BOX_TARGET="/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/lib/arm64-v8a/libwestlake_bionic_signal_box.so"

RAW_ADAPTER_SHA="7db99e1b760cf843b1a99db1382a3299f189c8cbca786ec411b7c35a2af6ffb9"
RAW_ADAPTER_BUILD_ID="9bc8f9913c07181f72cc7ef7a202e1d252f06d12"
RAW_PROVIDER_SHA="9c650fe37734d8aa29f0abe954021153f831db3c264c35aca7c02b07ce26dc1d"
RAW_CHILD_SHA="f9a36217ebf8a6d08a239d8412be540d9f8cf0ebe9614bfc9486890954d8a828"
RAW_APPSPAWN_SHA="c7fd4bd6f7474841eccf93687009e79748fbd7016a208faed0a70ea580a2976e"
RAW_RUNTIME_SHA="9689ce764083b4f6db848b036ff292cdd4962ecb2e1ca26373850390efb42812"
RAW_RUNTIME_JAR_SHA="06141543bec26c5036931d8d2d71b0efaa45d5ffd73434557d165cd42672be0d"
RAW_PTHREAD_BRIDGE_SHA="cce31e656e233b665c9ad16051ade7292319b326787ee55d3aa9327960b3316a"
RAW_NATIVE_LOADER_SHA="f8a5c1921cb95f62396568cd30a703883ec496f4494478201b4d64b16ad9daca"
RAW_ROUTE_NATIVE_LOADER_SHA="eddeb87ef17754b28f83cd732fe5b606504005af0c77b21923ac62c20e3c34ea"
RAW_ROUTE_NATIVE_LOADER_BUILD_ID="31152a2eb02aef1fe0d768a1379d2255c6a7df85"
RAW_LIBANDROID_SHA="6e9c0c2ced8448fb03ff9cdd36bcf426d86db2ce014e7dd8c3884821d11c590b"
BASE_PROVIDER_SHA="6787ea7d3c4ec0a382621360e3434885b0167446e22217a439b8d17745e54630"
BASE_CHILD_SHA="66afb06c10db5e986d294a465cf787f4be3302ce6be3a17d49309b368b1ec090"
BASE_APPSPAWN_SHA="43d5a319fa43e30fb712c2e39d29ba55e4bf82d171e97af1e6da9fcacc28920c"
RUNTIME_SHA="9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db"
REGISTRY_SHA="674d3ef3b9b00b367e389b539df4ae71bf2a12e3dd25dba962d6fcc7f240f063"
LIBCXX_SOURCE_CONFIG_SHA="9c36886ad0a669b1341429adedcb2ae14b9f6916b1e0a5c128d66de50b0a31ee"
LIBCXX_DERIVED_CONFIG_SHA="b739bcac34ab27facfdcac9224bb46e3378f64cf1c97c78dcfd4098c192f918e"
WINDOW_MANAGER_COMMIT="191866cf44e2e6f7278afee9b851fa4f39c8d4d1"
MOCK_SESSION_IDL_SHA="5e3763204bd867ebec64c57fec51703b7ef9e624bb569c45270ba6295e08176d"
MOCK_SESSION_HEADER_SHA="0cfa6634695f26a24fefd9dbdf5088eee02b1a10e873f41319e6abb4c94d5009"

die() { echo "ERROR: $*" >&2; exit 1; }
step() { printf '\n==> %s\n' "$*"; }
sha256_file() { shasum -a 256 "$1" | awk '{print $1}'; }
elf_build_id() { "$READELF" -nW "$1" 2>/dev/null | awk '/Build ID:/ {print $3; exit}'; }
trim() { tr -d ' \r\n'; }

binary_hex_at()
{
    local file=$1 offset=$2 length=$3
    perl -e '
        use strict;
        use warnings;
        my ($path, $offset_text, $length) = @ARGV;
        my $offset = oct($offset_text);
        open my $fh, "<:raw", $path or die "open $path: $!\n";
        seek($fh, $offset, 0) or die "seek $path: $!\n";
        my $bytes = "";
        my $count = read($fh, $bytes, $length);
        defined($count) && $count == $length
            or die "short read $path at $offset_text\n";
        print unpack("H*", $bytes);
    ' "$file" "$offset" "$length"
}

patch_binary_hex_exact()
{
    local file=$1 offset=$2 expected=$3 replacement=$4 label=$5
    perl -e '
        use strict;
        use warnings;
        my ($path, $offset_text, $expected, $replacement, $label) = @ARGV;
        length($expected) == length($replacement)
            or die "$label: replacement length mismatch\n";
        my $offset = oct($offset_text);
        my $expected_bytes = pack("H*", $expected);
        my $replacement_bytes = pack("H*", $replacement);
        open my $fh, "+<:raw", $path or die "open $path: $!\n";
        seek($fh, $offset, 0) or die "seek $path: $!\n";
        my $actual = "";
        my $count = read($fh, $actual, length($expected_bytes));
        defined($count) && $count == length($expected_bytes)
            or die "$label: short read at $offset_text\n";
        unpack("H*", $actual) eq $expected
            or die "$label: generation mismatch at $offset_text, got="
                . unpack("H*", $actual) . " expected=$expected\n";
        seek($fh, $offset, 0) or die "seek-write $path: $!\n";
        my $written = syswrite($fh, $replacement_bytes);
        defined($written) && $written == length($replacement_bytes)
            or die "$label: short write at $offset_text\n";
        close $fh or die "close $path: $!\n";
    ' "$file" "$offset" "$expected" "$replacement" "$label"
}

usage()
{
    printf '%s\n' \
        "usage: $0 build" \
        "       $0 build-runtime [base-candidate-dir]" \
        "       $0 build-input-classname [base-candidate-dir]" \
        "       $0 check-candidate [candidate-dir]" \
        "       $0 deploy [supported-board-serial] [candidate-dir]" \
        "       $0 run [supported-board-serial] [candidate-dir]" \
        "       $0 run-light [supported-board-serial] [candidate-dir]" \
        "       $0 run-light-risk [supported-board-serial] [candidate-dir]" \
        "       $0 rollback [supported-board-serial]" \
        "       $0 persist [supported-board-serial] [candidate-dir]" \
        "       $0 restore [supported-board-serial]"
}

require_hash()
{
    local expected=$1 path=$2 actual
    [ -f "$path" ] || die "missing file: $path"
    actual=$(sha256_file "$path")
    [ "$actual" = "$expected" ] || die "hash mismatch: $path expected=$expected actual=$actual"
}

ensure_libcxx_headers()
{
    local source_root source_config staging
    source_root="$OH_SDK/llvm/include/libcxx-ohos/include/c++/v1"
    source_config="$source_root/__config_site"
    require_hash "$LIBCXX_SOURCE_CONFIG_SHA" "$source_config"
    if [ ! -d "$LIBCXX_INCLUDE" ]; then
        staging="$PAYLOAD_ROOT/oh61-libcxx-h.staging.$$"
        [ ! -e "$staging" ] || die "libc++ staging path already exists: $staging"
        mkdir -p "$PAYLOAD_ROOT"
        cp -R "$source_root" "$staging"
        chmod -R u+w "$staging"
        perl -pi -e 's/^#define _LIBCPP_ABI_NAMESPACE __n1$/#define _LIBCPP_ABI_NAMESPACE __h/' \
            "$staging/__config_site"
        mkdir -p "$(dirname "$LIBCXX_INCLUDE")"
        mv "$staging" "$LIBCXX_INCLUDE"
        chmod -R a-w "$LIBCXX_INCLUDE"
    fi
    [ ! -L "$LIBCXX_INCLUDE" ] || die "libc++ derived header root must not be a symlink"
    require_hash "$LIBCXX_DERIVED_CONFIG_SHA" "$LIBCXX_INCLUDE/__config_site"
    grep -Eq '^#define[[:space:]]+_LIBCPP_ABI_NAMESPACE[[:space:]]+__h$' \
        "$LIBCXX_INCLUDE/__config_site" || die "derived libc++ headers do not select std::__h"
}

verify_local_inputs()
{
    local skia_commit resource_commit window_manager_commit
    [ "$(hostname)" = "Alvin-MacBook-Pro" ] || die "this workflow is pinned to the current Mac"
    [ -x "$HDC_BIN" ] || die "hdc missing: $HDC_BIN"
    [ -x "$OH_SDK/llvm/bin/clang++" ] || die "DevEco clang++ missing"
    [ -x "$READELF" ] || die "llvm-readelf missing"
    [ -x "$NM" ] || die "llvm-nm missing"
    [ -x "$OBJDUMP" ] || die "llvm-objdump missing"
    [ -x "$JAVA_BIN" ] || die "Java missing: $JAVA_BIN"
    [ -x "$JAVAC_BIN" ] || die "javac missing: $JAVAC_BIN"
    [ -x "$ZIP_BIN" ] || die "zip missing: $ZIP_BIN"
    [ -x "$D8_BIN" ] || die "D8 missing: $D8_BIN"
    [ -x "$APKANALYZER_BIN" ] || die "apkanalyzer missing: $APKANALYZER_BIN"
    [ -x "$DEXDUMP_BIN" ] || die "dexdump missing: $DEXDUMP_BIN"
    [ -x "$ARK_DISASM_BIN" ] || die "ark_disasm missing: $ARK_DISASM_BIN"
    [ -x "$PATCHELF_BIN" ] || die "patchelf missing: $PATCHELF_BIN"
    [ -x "$ANDROID_NDK_CLANG" ] || die "Android NDK clang missing: $ANDROID_NDK_CLANG"
    [ -d "$AOSP_ROOT" ] || die "AOSP missing: $AOSP_ROOT"
    [ -d "$OH_ROOT" ] || die "OpenHarmony source missing: $OH_ROOT"
    [ -d "$OH_HEADER_OUT" ] || die "OpenHarmony generated headers missing: $OH_HEADER_OUT"
    require_hash "$ZIGZAG_SHA" "$ZIGZAG_APK"
    require_hash "$ZIGZAG_CONTROL_HAP_SHA" "$ZIGZAG_CONTROL_HAP"
    require_hash "$ANDROID_TUANJIE_REFERENCE_SHA" "$ANDROID_TUANJIE_REFERENCE"
    require_hash "$OH_TUANJIE_REFERENCE_SHA" "$OH_TUANJIE_REFERENCE"
    [ "$(elf_build_id "$ANDROID_TUANJIE_REFERENCE")" = "$ANDROID_TUANJIE_BUILD_ID" ] \
        || die "Android Tuanjie reference Build-ID drifted"
    [ "$(elf_build_id "$OH_TUANJIE_REFERENCE")" = "$OH_TUANJIE_BUILD_ID" ] \
        || die "OH Tuanjie reference Build-ID drifted"
    require_hash "$RAW_ADAPTER_SHA" "$RAW_PR03/android/lib64/liboh_adapter_bridge.so"
    require_hash "$RAW_PROVIDER_SHA" "$RAW_PR03/route/libwestlake_android_runtime_provider.so"
    require_hash "$RAW_CHILD_SHA" "$RAW_PR03/runtime/libwestlake_android_child.z.so"
    require_hash "$RAW_APPSPAWN_SHA" "$RAW_PR03/runtime/appspawn-x"
    require_hash "$RAW_RUNTIME_SHA" "$RAW_PR03/android/lib64/liboh_android_runtime.so"
    require_hash "$RAW_RUNTIME_JAR_SHA" "$RAW_PR03/android/framework/oh-adapter-runtime.jar"
    require_hash "$RAW_PTHREAD_BRIDGE_SHA" "$RAW_PR03/android/lib64/libwestlake_bionic_pthread_bridge.so"
    require_hash "$RAW_NATIVE_LOADER_SHA" "$RAW_PR03/android/lib64/libnativeloader.so"
    require_hash "$RAW_ROUTE_NATIVE_LOADER_SHA" "$RAW_PR03/route/libnativeloader.so"
    require_hash "a9caa67f397ed4e7bd8ee47784aecb7f6966eaa9afd65c498597947ccc8f04b6" \
        "$RAW_PR03/android/lib64/libapp_native_loader.so"
    require_hash "$RUNTIME_SHA" "$BASELINE_RUNTIME_LOCAL"
    require_hash "d9eb9da824d9e247a352f570f01e1169e725b2954bca9e283a71786c59b59f9a" "$ANDROID_COMPILE_JAR"
    require_hash "b773a721be3d4988dea9660815a9e441b76100e5b0f5c72b5893cfadadc76c6f" "$D8_BIN"
    require_hash "e0c2803fbf9a1258051c3202daad46a2e00f33a0eb91258ac9fd373df0a832ce" "$D8_JAR"
    require_hash "136c5c4653d6531bd7b6f10f35f8691cb96432e727d30b4d5579826ee01e9419" "$SMALI_JAR"
    require_hash "1ed236266d7dc4907aade0b19a34f77efac25342b63c8ace52e579039941b389" "$BAKSMALI_JAR"
    require_hash "5a5c8982d8bd7d6e3bb1a0713049e3c78b719ec32b20f6b619885cec30a0dd61" "$DEXLIB_JAR"
    require_hash "4f580a9cff3ebb83cb3fd20bec88e37e4f183796ca652732992611620282daea" "$SMALI_UTIL_JAR"
    require_hash "156be736199c990321d9ff77090b199629cfc9865e2d6c13f7cd291bb1641817" "$JCOMMANDER_JAR"
    require_hash "686404f2d1d4d221911f96bd627ff60dac2226a5dfa6fb8ba517073eb97ec0ef" "$GUAVA_JAR"
    require_hash "5ac36c2acfb0a0f3d37dafe20b5b570f2643e2d000c648d44503c2738be643df" "$ANTLR_JAR"
    require_hash "ce3fc8ecb10f39e9a3cddcbb2ce350d272d9cd3d0b1e18e6fe73c3b9389c8734" "$ANTLR_RUNTIME_JAR"
    require_hash "f66ce72e965e5301cb0f020e54d2ba6ad76feb91b3cbfc30dbbf00c06a6df6d7" "$STRINGTEMPLATE_JAR"
    rg -q 'if \(ai\.metaData == null\)' "$ADAPTER_ROOT/framework/activity/java/AppSchedulerBridge.java" \
        || die "AppSchedulerBridge metadata non-null source guard is missing"
    rg -q 'FLAG_EXTRACT_NATIVE_LIBS' "$ADAPTER_ROOT/framework/activity/java/AppSchedulerBridge.java" \
        || die "AppSchedulerBridge extract-native-libs source guard is missing"
    rg -q 'PackageManagerProjectionProxy.install' "$ADAPTER_ROOT/framework/activity/java/AppSchedulerBridge.java" \
        || die "AppSchedulerBridge package-manager projection source call is missing"
    rg -q 'implements InvocationHandler' "$PM_PROXY_SOURCE" \
        || die "package-manager projection source is missing"
    rg -q '\[ZZ-PM\] projected getApplicationInfo' "$PM_PROXY_SOURCE" \
        || die "package-manager projection observation marker is missing"
    rg -q 'info\.primaryCpuAbi = null' "$PM_PROXY_SOURCE" \
        || die "package-manager projection ABI selector guard is missing"
    rg -q 'Trace\.beginSection\("ZZ-PM:apk-zip-disabled"\)' "$PM_PROXY_SOURCE" \
        || die "package-manager ABI selector trace marker is missing"
    rg -q '\[ZZ-PM\] extracted native path selected; apk zip path disabled' "$PM_PROXY_SOURCE" \
        || die "package-manager extracted-native-path marker is missing"
    rg -q 'TRANSACTION_GET_VOLUME_LIST = 0x1e' "$STORAGE_PROXY_SOURCE" \
        || die "storage-manager projection transaction is missing"
    rg -q 'ZZ.StorageVolume.getVolumeList' "$STORAGE_PROXY_SOURCE" \
        || die "storage-manager projection trace marker is missing"
    rg -F -q 'cache.put(SERVICE_NAME, new MountBinder())' "$STORAGE_PROXY_SOURCE" \
        || die "storage-manager projection cache install is missing"
    rg -q 'TRANSACTION_isUserUnlockingOrUnlocked' "$USER_PROXY_SOURCE" \
        || die "user-manager projection transaction lookup is missing"
    rg -q 'ZZ.UserManager.isUserUnlockingOrUnlocked' "$USER_PROXY_SOURCE" \
        || die "user-manager projection trace marker is missing"
    rg -F -q 'cache.put(SERVICE_NAME, new UserBinder(transaction))' "$USER_PROXY_SOURCE" \
        || die "user-manager projection cache install is missing"
    rg -q 'setFixedSize' "$CAPYBARA_LETTERBOX_SOURCE" \
        || die "Capybara letterbox projection source is missing"
    rg -q 'libwestlake_audio_compat\.so' "$AUDIO_COMPAT_BOOTSTRAP_SOURCE" \
        || die "audio compatibility bootstrap source is missing"
    rg -q 'BinaryAndroidManifestOrientation.read' "$MANIFEST_ORIENTATION_SOURCE" \
        || die "manifest-orientation AXML reader call is missing"
    rg -q 'ZipFile' "$BINARY_MANIFEST_ORIENTATION_SOURCE" \
        || die "binary-manifest original-APK reader is missing"
    rg -q 'ManifestOrientationProjection.applyActivityInfo' \
        "$ADAPTER_ROOT/framework/activity/java/AppSchedulerBridge.java" \
        || die "AppSchedulerBridge manifest ActivityInfo source call is missing"
    rg -q 'ManifestOrientationProjection.projectConfiguration' \
        "$ADAPTER_ROOT/framework/activity/java/AppSchedulerBridge.java" \
        || die "AppSchedulerBridge manifest Configuration source call is missing"
    rg -q 'resolveOhOrientation' \
        "$ADAPTER_ROOT/framework/activity/jni/ability_scheduler_adapter.cpp" \
        || die "AbilityScheduler manifest parent-orientation call is missing"
    ! rg -q 'com\.Unity3d\.BoatAttackDay' "$MANIFEST_ORIENTATION_SOURCE" \
        || die "manifest-orientation projection must not contain a BoatAttack identity"
    ! rg -q '1920|1200' "$MANIFEST_ORIENTATION_SOURCE" \
        || die "manifest-orientation projection must not contain D600 dimensions"
    rg -q 'public String primaryCpuAbi;' "$PM_PROXY_COMPILE_STUB" \
        || die "compile-only ApplicationInfo ABI stub is missing"
    rg -q 'unsigned char __sF' "$UNITY_LIBC_STUB_SOURCE" \
        || die "Unity Bionic libc bridge source lacks __sF"
    rg -q '^[[:space:]]*__sF;' "$PTHREAD_BRIDGE_MAP" \
        || die "pthread bridge export map lacks __sF@LIBC"
    rg -q 'extern "C" void android_set_abort_message' "$ABORT_MESSAGE_COMPAT_SOURCE" \
        || die "Bionic abort-message compatibility source is missing"
    rg -q '^[[:space:]]*android_set_abort_message;' "$PTHREAD_BRIDGE_MAP" \
        || die "pthread bridge export map lacks android_set_abort_message@LIBC"
    rg -q 'BIO_EXPORT int sigaction' "$UNITY_SIGNAL_SOURCE" \
        || die "Bionic signal ABI box source is missing"
    for signal_symbol in signal sigaction sigemptyset sigfillset sigaddset sigdelset \
            sigismember sigprocmask pthread_sigmask sigsuspend sigaltstack; do
        rg -q "^[[:space:]]*westlake_bionic_${signal_symbol};" "$SIGNAL_BOX_MAP" \
            || die "guest signal-box map lacks westlake_bionic_${signal_symbol}@LIBC"
    done
    for signal_symbol in signal sigaction sigemptyset sigfillset sigaddset sigdelset \
            sigismember sigprocmask pthread_sigmask sigsuspend sigaltstack; do
        rg -q "^${signal_symbol} westlake_bionic_${signal_symbol}$" "$SIGNAL_RENAME_MAP" \
            || die "guest signal rename map lacks ${signal_symbol}"
    done
    rg -q 'westlake_musl_sigaction_bridge' "$SIGNAL_BACKEND_SOURCE" \
        || die "OH musl signal backend source is missing"
    rg -q 'struct westlake_signal_action' "$SIGNAL_BACKEND_HEADER" \
        || die "OH musl signal backend contract is missing"
    rg -q 'sizeof\(sigset_t\) == WESTLAKE_EXPECT_SIGSET_SIZE' \
        "$SIGNAL_ABI_PROBE_SOURCE" || die "signal ABI size probe is missing"
    ! rg -q '^[[:space:]]*sig(action|emptyset|fillset|addset|delset|ismember|procmask);' \
        "$PTHREAD_BRIDGE_MAP" \
        || die "appspawn-wide pthread bridge still exports a Bionic signal ABI"
    rg -q '__system_property_get' "$PTHREAD_PROPERTY_SOURCE" \
        || die "Bionic property forwarding source is missing"
    for property_symbol in __system_property_find __system_property_get __system_property_read; do
        rg -q "^[[:space:]]*${property_symbol};" "$PTHREAD_BRIDGE_MAP" \
            || die "pthread bridge export map lacks ${property_symbol}@LIBC"
    done
    rg -q 'westlake_mediandk_presence_provenance' "$MEDIANDK_PRESENCE_SOURCE" \
        || die "presence-only media provider source is missing"
    rg -q '"/system/lib64/platformsdk"' \
        "$ADAPTER_ROOT/framework/native-loader-oh/include/nativeloader/native_bridge_policy.h" \
        || die "native bridge C++ policy lacks the platform SDK search path"
    rg -q '"/system/lib64/platformsdk"' \
        "$ADAPTER_ROOT/framework/native-loader-oh/policy/native_bridge_policy.v1.json" \
        || die "native bridge JSON policy lacks the platform SDK search path"
    require_hash "$REGISTRY_SHA" "$RAW_PR03/route/libwestlake_thread_guard_registry.so"
    require_hash "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2" "$LINK_INPUTS/libc.so"
    require_hash "9466fb0d933689533bdf4b4962907f3e0c0970be278bd6ccf703ffa2aea838a6" "$LINK_INPUTS/libc++.so"
    require_hash "d79a97df3d20444720a9591d9216a59f6e6e3e773811dc88dc9126864a528d3a" "$LINK_INPUTS/libappkit_native.z.so"
    require_hash "b906ff740c6375d58e6870a02adc3004201203e7af6bde19b60236f99f6b530f" "$LINK_INPUTS/libsession_manager.z.so"
    require_hash "06734bf3308057ab2f28b21cacb5b47aed875f145704fbfd3e1a76a86ee9c102" "$LINK_INPUTS/libwmutil.z.so"
    require_hash "8c96da51508a34a3597b66160885f0e5c861490061740c8c1f0d26e8279ed9b1" "$LINK_INPUTS/libwmutil_base.z.so"
    require_hash "d4197d1c4d1ab0990361ad3047d908fd63cb040a7212d98538fbc75cfef34f51" "$LINK_INPUTS/libeventhandler.z.so"
    ensure_libcxx_headers
    skia_commit=$(git -C "$OH_SOURCE_INPUTS/third_party_skia" rev-parse HEAD)
    resource_commit=$(git -C "$OH_SOURCE_INPUTS/global_resource_management" rev-parse HEAD)
    window_manager_commit=$(git -C "$WINDOW_MANAGER_SOURCE" rev-parse HEAD)
    [ "$skia_commit" = "d26e5772d036c6ffe58e6983c79f78bc0b26231f" ] || die "Skia source commit drifted"
    [ "$resource_commit" = "6ddc6e6c7437a4cbe61a1e4dc8de90751e295fb6" ] || die "resource-management source commit drifted"
    [ "$window_manager_commit" = "$WINDOW_MANAGER_COMMIT" ] || die "window-manager source commit drifted"
    [ -z "$(git -C "$OH_SOURCE_INPUTS/third_party_skia" status --short)" ] || die "Skia source input is dirty"
    [ -z "$(git -C "$OH_SOURCE_INPUTS/global_resource_management" status --short)" ] || die "resource source input is dirty"
    [ -z "$(git -C "$WINDOW_MANAGER_SOURCE" status --short)" ] || die "window-manager source input is dirty"
    [ ! -L "$OH61_GENERATED_HEADERS" ] || die "generated MockSessionManager header root must not be a symlink"
    require_hash "$MOCK_SESSION_IDL_SHA" "$WINDOW_MANAGER_SOURCE/wmserver/IMockSessionManagerInterface.idl"
    require_hash "$MOCK_SESSION_HEADER_SHA" "$OH61_GENERATED_HEADERS/imock_session_manager_interface.h"
    grep -q 'DECLARE_INTERFACE_DESCRIPTOR(u"OHOS.IMockSessionManager")' \
        "$OH61_GENERATED_HEADERS/imock_session_manager_interface.h" \
        || die "generated MockSessionManager header descriptor drifted"
}

replace_ascii_exact()
{
    local file=$1 old=$2 new=$3 expected=$4 before after old_after
    [ "${#old}" -eq "${#new}" ] || die "repin values must have equal lengths"
    case "${#old}" in
        40|64) ;;
        *) die "repin values must be 40- or 64-byte hex" ;;
    esac
    [[ "$old" =~ ^[0-9a-f]+$ && "$new" =~ ^[0-9a-f]+$ ]] || die "repin values must be lowercase hex"
    before=$(LC_ALL=C grep -a -o "$old" "$file" 2>/dev/null | wc -l | trim || true)
    [ "${before:-0}" = "$expected" ] || die "repin occurrence mismatch: $file old=$old expected=$expected actual=${before:-0}"
    perl -0pi -e "s/$old/$new/g" "$file"
    after=$(LC_ALL=C grep -a -o "$new" "$file" 2>/dev/null | wc -l | trim || true)
    old_after=$(LC_ALL=C grep -a -o "$old" "$file" 2>/dev/null | wc -l | trim || true)
    [ "${after:-0}" = "$expected" ] && [ "${old_after:-0}" = 0 ] || die "repin postflight failed: $file"
}

build_runtime_jar()
{
    local output=$1 build=$2 dex smali_root smali_file package post_root
    local helper_classes helper_dex helper_smali helper_file appspawn_smali
    local storage_helper_file storage_binder_file
    local user_helper_file user_binder_file
    local display_helper_file display_binder_file display_handler_file
    local capybara_helper_file capybara_callback_file
    local orientation_helper_file orientation_callback_file
    local binary_orientation_helper_file binary_orientation_pool_file
    local input_device_helper_file input_device_callback_file
    local audio_helper_file
    dex="$build/classes.dex"
    smali_root="$build/smali"
    smali_file="$smali_root/adapter/activity/AppSchedulerBridge.smali"
    package="$build/package"
    post_root="$build/postflight-smali"
    helper_classes="$build/helper-classes"
    helper_dex="$build/helper-dex"
    helper_smali="$build/helper-smali"
    helper_file="$helper_smali/adapter/activity/PackageManagerProjectionProxy.smali"
    storage_helper_file="$helper_smali/adapter/activity/StorageManagerProjectionProxy.smali"
    storage_binder_file="$helper_smali/adapter/activity/StorageManagerProjectionProxy\$MountBinder.smali"
    user_helper_file="$helper_smali/adapter/activity/UserManagerProjectionProxy.smali"
    user_binder_file="$helper_smali/adapter/activity/UserManagerProjectionProxy\$UserBinder.smali"
    display_helper_file="$helper_smali/adapter/activity/DisplayManagerProjectionProxy.smali"
    display_binder_file="$helper_smali/adapter/activity/DisplayManagerProjectionProxy\$DisplayBinder.smali"
    display_handler_file="$helper_smali/adapter/activity/DisplayManagerProjectionProxy\$DisplayInvocationHandler.smali"
    capybara_helper_file="$helper_smali/adapter/activity/CapybaraLetterboxProjection.smali"
    capybara_callback_file="$helper_smali/adapter/activity/CapybaraLetterboxProjection\$1.smali"
    orientation_helper_file="$helper_smali/adapter/activity/ManifestOrientationProjection.smali"
    orientation_callback_file="$helper_smali/adapter/activity/ManifestOrientationProjection\$1.smali"
    binary_orientation_helper_file="$helper_smali/adapter/activity/BinaryAndroidManifestOrientation.smali"
    binary_orientation_pool_file="$helper_smali/adapter/activity/BinaryAndroidManifestOrientation\$StringPool.smali"
    input_device_helper_file="$helper_smali/adapter/activity/InputEventDeviceProjection.smali"
    input_device_callback_file="$helper_smali/adapter/activity/InputEventDeviceProjection\$1.smali"
    audio_helper_file="$helper_smali/adapter/audio/AudioCompatBootstrap.smali"
    appspawn_smali="$smali_root/com/android/internal/os/AppSpawnXInit.smali"
    mkdir -p "$build" "$package/META-INF" "$helper_classes" "$helper_dex" "$helper_smali"
    unzip -p "$RAW_PR03/android/framework/oh-adapter-runtime.jar" classes.dex > "$dex"
    unzip -p "$RAW_PR03/android/framework/oh-adapter-runtime.jar" META-INF/MANIFEST.MF \
        > "$package/META-INF/MANIFEST.MF"
    "$JAVA_BIN" -cp "$SMALI_CP" org.jf.baksmali.Main disassemble "$dex" -o "$smali_root"
    [ -f "$smali_file" ] || die "PR03 runtime dex lacks AppSchedulerBridge"
    [ -f "$appspawn_smali" ] || die "PR03 runtime dex lacks AppSpawnXInit"

    # Keep the immutable PR03 dex as the bytecode base. Apply only the two
    # source-reviewed launch-object repairs so unrelated Java cannot drift.
    perl -0pi -e '
        my $anchor = q~    const v0, 0x802044

    or-int/2addr p1, v0

    iput p1, p0, Landroid/content/pm/ApplicationInfo;->flags:I
~;
        my $insert = q~
    iget-object p1, p0, Landroid/content/pm/ApplicationInfo;->metaData:Landroid/os/Bundle;

    if-nez p1, :zigzag_metadata_ready

    new-instance p1, Landroid/os/Bundle;

    invoke-direct {p1}, Landroid/os/Bundle;-><init>()V

    iput-object p1, p0, Landroid/content/pm/ApplicationInfo;->metaData:Landroid/os/Bundle;

    :zigzag_metadata_ready
    const-string p1, "extractNativeLibs"

    const/4 v0, 0x1

    invoke-virtual {v5, p1, v0}, Lorg/json/JSONObject;->optBoolean(Ljava/lang/String;Z)Z

    move-result p1

    if-eqz p1, :zigzag_extract_clear

    iget p1, p0, Landroid/content/pm/ApplicationInfo;->flags:I

    const v0, 0x10000000

    or-int/2addr p1, v0

    iput p1, p0, Landroid/content/pm/ApplicationInfo;->flags:I

    goto :zigzag_extract_ready

    :zigzag_extract_clear
    iget p1, p0, Landroid/content/pm/ApplicationInfo;->flags:I

    const v0, -0x10000001

    and-int/2addr p1, v0

    iput p1, p0, Landroid/content/pm/ApplicationInfo;->flags:I

    :zigzag_extract_ready
~;
        my $count = () = /\Q$anchor\E/g;
        die "runtime smali anchor count=$count, expected=1\n" unless $count == 1;
        s/\Q$anchor\E/$anchor$insert/;
    ' "$smali_file"
    [ "$(rg -c ':zigzag_metadata_ready|:zigzag_extract_(clear|ready)' "$smali_file")" = 6 ] \
        || die "runtime smali fix labels are incomplete"
    [ "$(rg -c 'const-string p1, \"extractNativeLibs\"' "$smali_file")" = 1 ] \
        || die "runtime smali extractNativeLibs fix is not unique"

    # Load the opt-in BoatAttack JNI bridge only after handleBindApplication
    # has created the APK PathClassLoader. Runtime.load0 then associates the
    # library with the same namespace as FMOD instead of the runtime-jar loader.
    perl -0pi -e '
        my $anchor = q~    .line 314
    invoke-static {}, Ladapter/activity/AppSchedulerBridge;->primeCoroutineStart()V

    const/16 v20, 0x1
~;
        my $insert = q~    .line 314
    invoke-static {}, Ladapter/activity/AppSchedulerBridge;->primeCoroutineStart()V

    invoke-virtual/range {p0 .. p0}, Landroid/app/ActivityThread;->getApplication()Landroid/app/Application;

    move-result-object v0

    if-eqz v0, :boat_audio_bootstrap_done

    invoke-virtual {v0}, Landroid/app/Application;->getClassLoader()Ljava/lang/ClassLoader;

    move-result-object v1

    move-object/from16 v2, p1

    invoke-static {v2, v1}, Ladapter/audio/AudioCompatBootstrap;->load(Ljava/lang/String;Ljava/lang/ClassLoader;)V

    :boat_audio_bootstrap_done
    const/16 v20, 0x1
~;
        my $count = () = /\Q$anchor\E/g;
        die "runtime audio bootstrap anchor count=$count, expected=1\n" unless $count == 1;
        s/\Q$anchor\E/$insert/;
    ' "$smali_file"
    [ "$(rg -c ':boat_audio_bootstrap_done|AudioCompatBootstrap;->load' \
        "$smali_file")" = 3 ] \
        || die "runtime audio bootstrap injection is incomplete"

    # Compile the narrow package/system-service projections against the public
    # Android API, then merge only those helper classes into
    # the immutable PR03 runtime dex. This keeps the paired BCP boot image
    # untouched.
    "$JAVAC_BIN" --release 8 -classpath "$ANDROID_COMPILE_JAR" \
        -d "$helper_classes" "$PM_PROXY_COMPILE_STUB" "$PM_PROXY_SOURCE" \
        "$STORAGE_PROXY_SOURCE" "$USER_PROXY_SOURCE" "$DISPLAY_PROXY_SOURCE" \
        "$CAPYBARA_LETTERBOX_SOURCE" "$MANIFEST_ORIENTATION_SOURCE" \
        "$BINARY_MANIFEST_ORIENTATION_SOURCE" \
        "$INPUT_EVENT_DEVICE_SOURCE" \
        "$INPUT_EVENT_RECEIVER_COMPILE_STUB" \
        "$AUDIO_COMPAT_BOOTSTRAP_SOURCE"
    [ -f "$helper_classes/android/content/pm/ApplicationInfo.class" ] \
        || die "compile-only ApplicationInfo stub was not compiled"
    env JAVA_HOME="$(cd "$(dirname "$JAVA_BIN")/.." && pwd -P)" \
        PATH="$(dirname "$JAVA_BIN"):$PATH" \
        "$D8_BIN" --release --min-api 22 --lib "$ANDROID_COMPILE_JAR" \
        --output "$helper_dex" \
        "$helper_classes/adapter/activity/PackageManagerProjectionProxy.class" \
        "$helper_classes/adapter/activity/StorageManagerProjectionProxy.class" \
        "$helper_classes/adapter/activity/StorageManagerProjectionProxy\$MountBinder.class" \
        "$helper_classes/adapter/activity/UserManagerProjectionProxy.class" \
        "$helper_classes/adapter/activity/UserManagerProjectionProxy\$UserBinder.class" \
        "$helper_classes/adapter/activity/DisplayManagerProjectionProxy.class" \
        "$helper_classes/adapter/activity/DisplayManagerProjectionProxy\$DisplayBinder.class" \
        "$helper_classes/adapter/activity/DisplayManagerProjectionProxy\$DisplayInvocationHandler.class" \
        "$helper_classes/adapter/activity/CapybaraLetterboxProjection.class" \
        "$helper_classes/adapter/activity/CapybaraLetterboxProjection\$1.class" \
        "$helper_classes/adapter/activity/ManifestOrientationProjection.class" \
        "$helper_classes/adapter/activity/ManifestOrientationProjection\$1.class" \
        "$helper_classes/adapter/activity/BinaryAndroidManifestOrientation.class" \
        "$helper_classes/adapter/activity/BinaryAndroidManifestOrientation\$StringPool.class" \
        "$helper_classes/adapter/activity/InputEventDeviceProjection.class" \
        "$helper_classes/adapter/activity/InputEventDeviceProjection\$1.class" \
        "$helper_classes/adapter/audio/AudioCompatBootstrap.class"
    "$JAVA_BIN" -cp "$SMALI_CP" org.jf.baksmali.Main disassemble \
        "$helper_dex/classes.dex" -o "$helper_smali"
    [ -f "$helper_file" ] || die "compiled package-manager projection class is missing"
    [ -f "$storage_helper_file" ] || die "compiled storage-manager projection class is missing"
    [ -f "$storage_binder_file" ] || die "compiled storage-manager binder class is missing"
    [ -f "$user_helper_file" ] || die "compiled user-manager projection class is missing"
    [ -f "$user_binder_file" ] || die "compiled user-manager binder class is missing"
    [ -f "$display_helper_file" ] || die "compiled display-manager projection class is missing"
    [ -f "$display_binder_file" ] || die "compiled display-manager binder class is missing"
    [ -f "$display_handler_file" ] || die "compiled display-manager handler class is missing"
    [ -f "$capybara_helper_file" ] || die "compiled Capybara letterbox class is missing"
    [ -f "$capybara_callback_file" ] || die "compiled Capybara callback class is missing"
    [ -f "$orientation_helper_file" ] \
        || die "compiled manifest-orientation projection class is missing"
    [ -f "$orientation_callback_file" ] \
        || die "compiled manifest-orientation callback class is missing"
    [ -f "$binary_orientation_helper_file" ] \
        || die "compiled binary-manifest orientation class is missing"
    [ -f "$binary_orientation_pool_file" ] \
        || die "compiled binary-manifest string pool class is missing"
    [ -f "$input_device_helper_file" ] \
        || die "compiled input-device projection class is missing"
    [ -f "$input_device_callback_file" ] \
        || die "compiled input-device projection callback is missing"
    [ -f "$audio_helper_file" ] \
        || die "compiled audio compatibility bootstrap is missing"
    cp "$helper_file" "$smali_root/adapter/activity/PackageManagerProjectionProxy.smali"
    cp "$storage_helper_file" "$smali_root/adapter/activity/StorageManagerProjectionProxy.smali"
    cp "$storage_binder_file" \
        "$smali_root/adapter/activity/StorageManagerProjectionProxy\$MountBinder.smali"
    cp "$user_helper_file" "$smali_root/adapter/activity/UserManagerProjectionProxy.smali"
    cp "$user_binder_file" \
        "$smali_root/adapter/activity/UserManagerProjectionProxy\$UserBinder.smali"
    cp "$display_helper_file" "$smali_root/adapter/activity/DisplayManagerProjectionProxy.smali"
    cp "$display_binder_file" \
        "$smali_root/adapter/activity/DisplayManagerProjectionProxy\$DisplayBinder.smali"
    cp "$display_handler_file" \
        "$smali_root/adapter/activity/DisplayManagerProjectionProxy\$DisplayInvocationHandler.smali"
    cp "$capybara_helper_file" \
        "$smali_root/adapter/activity/CapybaraLetterboxProjection.smali"
    cp "$capybara_callback_file" \
        "$smali_root/adapter/activity/CapybaraLetterboxProjection\$1.smali"
    cp "$orientation_helper_file" \
        "$smali_root/adapter/activity/ManifestOrientationProjection.smali"
    cp "$orientation_callback_file" \
        "$smali_root/adapter/activity/ManifestOrientationProjection\$1.smali"
    cp "$binary_orientation_helper_file" \
        "$smali_root/adapter/activity/BinaryAndroidManifestOrientation.smali"
    cp "$binary_orientation_pool_file" \
        "$smali_root/adapter/activity/BinaryAndroidManifestOrientation\$StringPool.smali"
    cp "$input_device_helper_file" \
        "$smali_root/adapter/activity/InputEventDeviceProjection.smali"
    cp "$input_device_callback_file" \
        "$smali_root/adapter/activity/InputEventDeviceProjection\$1.smali"
    mkdir -p "$smali_root/adapter/audio"
    cp "$audio_helper_file" "$smali_root/adapter/audio/AudioCompatBootstrap.smali"

    # The native InputEventReceiver first resolves AppSchedulerBridge from the
    # hot-swappable runtime jar.  Add the exact method it probes for and keep
    # all repair logic in the separately compiled helper above.  This avoids a
    # BCP framework-jar change while preserving the bridge's main-looper route.
    perl -0pi -e '
        my $signature = q~.method public static dispatchOnMainThread(Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V~;
        my $method = q~

.method public static dispatchOnMainThread(Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V
    .registers 3

    invoke-static {p0, p1, p2}, Ladapter/activity/InputEventDeviceProjection;->dispatchOnMainThread(Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V

    return-void
.end method
~;
        my $count = () = /\Q$signature\E/g;
        die "runtime input dispatch method already present count=$count\n" unless $count == 0;
        $_ .= $method;
    ' "$smali_file"

    perl -0pi -e '
        my $anchor = q~    sput-boolean v20, Ladapter/activity/AppSchedulerBridge;->sBindAppDone:Z
~;
        my $insert = q~
    invoke-virtual/range {p0 .. p0}, Landroid/app/ActivityThread;->getApplication()Landroid/app/Application;

    move-result-object v0

    move-object/from16 v1, p1

    invoke-static {v0, v1}, Ladapter/activity/CapybaraLetterboxProjection;->install(Landroid/app/Application;Ljava/lang/String;)V
~;
        my $count = () = /\Q$anchor\E/g;
        die "runtime Capybara letterbox anchor count=$count, expected=1\n" unless $count == 1;
        s/\Q$anchor\E/$anchor$insert/;
    ' "$smali_file"

    # BMS currently drops Android screenOrientation while registering an APK.
    # Recover it from the immutable installed base.apk before constructing the
    # launch Intent, then project the matching display axis into both launch
    # Configuration objects. The helper owns all parsing and remains fail-open.
    perl -0pi -e '
        my $anchor = q~    invoke-static {v8, v1, v9, v3}, Ladapter/activity/AppSchedulerBridge;->buildActivityInfoFromAbility(Ljava/lang/String;Ljava/lang/String;Landroid/content/pm/ApplicationInfo;Ljava/lang/String;)Landroid/content/pm/ActivityInfo;

    move-result-object v1
~;
        my $insert = q~
    invoke-static {v8, v1}, Ladapter/activity/ManifestOrientationProjection;->applyActivityInfo(Ljava/lang/String;Landroid/content/pm/ActivityInfo;)V
~;
        my $count = () = /\Q$anchor\E/g;
        die "runtime manifest ActivityInfo anchor count=$count, expected=1\n" unless $count == 1;
        s/\Q$anchor\E/$anchor$insert/;
    ' "$smali_file"

    perl -0pi -e '
        my $anchor = q~    invoke-virtual/range {v23 .. v23}, Landroid/app/ActivityThread;->getConfiguration()Landroid/content/res/Configuration;

    move-result-object v25
~;
        my $insert = q~
    invoke-static/range {v24 .. v25}, Ladapter/activity/ManifestOrientationProjection;->projectConfiguration(Landroid/content/pm/ActivityInfo;Landroid/content/res/Configuration;)Landroid/content/res/Configuration;

    move-result-object v25
~;
        my $count = () = /\Q$anchor\E/g;
        die "runtime manifest Configuration anchor count=$count, expected=1\n" unless $count == 1;
        s/\Q$anchor\E/$anchor$insert/;
    ' "$smali_file"

    perl -0pi -e '
        my $anchor = q~    invoke-static {}, Lcom/android/internal/os/AppSpawnXInit;->installServiceManagerAdapter()V
~;
        my $insert = q~
    invoke-static {}, Ladapter/activity/StorageManagerProjectionProxy;->install()V

    invoke-static {}, Ladapter/activity/UserManagerProjectionProxy;->install()V

    invoke-static {}, Ladapter/activity/DisplayManagerProjectionProxy;->install()V
~;
        my $count = () = /\Q$anchor\E/g;
        die "runtime storage projection anchor count=$count, expected=1\n" unless $count == 1;
        s/\Q$anchor\E/$anchor$insert/;
    ' "$appspawn_smali"
    [ "$(rg -c 'StorageManagerProjectionProxy;->install' "$appspawn_smali")" = 1 ] \
        || die "runtime storage-manager projection call is not unique"
    [ "$(rg -c 'UserManagerProjectionProxy;->install' "$appspawn_smali")" = 1 ] \
        || die "runtime user-manager projection call is not unique"
    [ "$(rg -c 'DisplayManagerProjectionProxy;->install' "$appspawn_smali")" = 1 ] \
        || die "runtime display-manager projection call is not unique"

    perl -0pi -e '
        my $anchor = q~    invoke-static {v10, v14}, Ladapter/activity/AppSchedulerBridge;->applyManifestFieldsToAppInfoLocal(Landroid/content/pm/ApplicationInfo;Ljava/lang/String;)V
~;
        my $insert = q~
    invoke-static {v10, v14}, Ladapter/activity/PackageManagerProjectionProxy;->install(Landroid/content/pm/ApplicationInfo;Ljava/lang/String;)V
~;
        my $count = () = /\Q$anchor\E/g;
        die "runtime PM projection anchor count=$count, expected=1\n" unless $count == 1;
        s/\Q$anchor\E/$anchor$insert/;
    ' "$smali_file"
    [ "$(rg -c 'PackageManagerProjectionProxy;->install' "$smali_file")" = 1 ] \
        || die "runtime package-manager projection call is not unique"

    "$JAVA_BIN" -cp "$SMALI_CP" org.jf.smali.Main assemble "$smali_root" \
        -o "$package/classes.dex"
    mkdir -p "$post_root"
    "$JAVA_BIN" -cp "$SMALI_CP" org.jf.baksmali.Main disassemble \
        "$package/classes.dex" -o "$post_root"
    [ "$(rg -c 'ApplicationInfo;->metaData:Landroid/os/Bundle;' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 2 ] \
        || die "runtime jar metadata read/write guard did not survive assembly"
    [ "$(rg -c 'const-string p1, "extractNativeLibs"|const v0, 0x10000000|const v0, -0x10000001' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 3 ] \
        || die "runtime jar extractNativeLibs branch did not survive assembly"
    [ "$(rg -c 'PackageManagerProjectionProxy;->install' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 1 ] \
        || die "runtime package-manager projection call did not survive assembly"
    [ -f "$post_root/adapter/activity/PackageManagerProjectionProxy.smali" ] \
        || die "runtime package-manager projection class did not survive assembly"
    [ "$(rg -c 'StorageManagerProjectionProxy;->install' \
        "$post_root/com/android/internal/os/AppSpawnXInit.smali")" = 1 ] \
        || die "runtime storage-manager projection call did not survive assembly"
    [ -f "$post_root/adapter/activity/StorageManagerProjectionProxy.smali" ] \
        || die "runtime storage-manager projection class did not survive assembly"
    [ -f "$post_root/adapter/activity/StorageManagerProjectionProxy\$MountBinder.smali" ] \
        || die "runtime storage-manager binder class did not survive assembly"
    [ "$(rg -c 'UserManagerProjectionProxy;->install' \
        "$post_root/com/android/internal/os/AppSpawnXInit.smali")" = 1 ] \
        || die "runtime user-manager projection call did not survive assembly"
    [ -f "$post_root/adapter/activity/UserManagerProjectionProxy.smali" ] \
        || die "runtime user-manager projection class did not survive assembly"
    [ -f "$post_root/adapter/activity/UserManagerProjectionProxy\$UserBinder.smali" ] \
        || die "runtime user-manager binder class did not survive assembly"
    [ "$(rg -c 'DisplayManagerProjectionProxy;->install' \
        "$post_root/com/android/internal/os/AppSpawnXInit.smali")" = 1 ] \
        || die "runtime display-manager projection call did not survive assembly"
    [ -f "$post_root/adapter/activity/DisplayManagerProjectionProxy.smali" ] \
        || die "runtime display-manager projection class did not survive assembly"
    [ -f "$post_root/adapter/activity/DisplayManagerProjectionProxy\$DisplayBinder.smali" ] \
        || die "runtime display-manager binder class did not survive assembly"
    [ -f "$post_root/adapter/activity/DisplayManagerProjectionProxy\$DisplayInvocationHandler.smali" ] \
        || die "runtime display-manager handler class did not survive assembly"
    [ "$(rg -c 'CapybaraLetterboxProjection;->install' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 1 ] \
        || die "runtime Capybara letterbox install call did not survive assembly"
    [ -f "$post_root/adapter/activity/CapybaraLetterboxProjection.smali" ] \
        || die "runtime Capybara letterbox class did not survive assembly"
    [ "$(rg -c 'ManifestOrientationProjection;->applyActivityInfo' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 1 ] \
        || die "runtime manifest ActivityInfo projection did not survive assembly"
    [ "$(rg -c 'ManifestOrientationProjection;->projectConfiguration' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 1 ] \
        || die "runtime manifest Configuration projection did not survive assembly"
    [ -f "$post_root/adapter/activity/ManifestOrientationProjection.smali" ] \
        || die "runtime manifest-orientation class did not survive assembly"
    [ -f "$post_root/adapter/activity/BinaryAndroidManifestOrientation.smali" ] \
        || die "runtime binary-manifest class did not survive assembly"
    rg -F -q 'ZipFile;->getEntry(Ljava/lang/String;)Ljava/util/zip/ZipEntry;' \
        "$post_root/adapter/activity/BinaryAndroidManifestOrientation.smali" \
        || die "runtime manifest projection lost original-APK AXML reading"
    ! rg -F -q 'PackageManager;->getPackageArchiveInfo' \
        "$post_root/adapter/activity/ManifestOrientationProjection.smali" \
        || die "runtime manifest projection still invokes PackageParser"
    rg -F -q 'SurfaceHolder;->setFixedSize(II)V' \
        "$post_root/adapter/activity/ManifestOrientationProjection.smali" \
        || die "runtime manifest projection lost pre-EGL surface sizing"
    [ "$(rg -c '^\.method public static dispatchOnMainThread' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 1 ] \
        || die "runtime input dispatch entry did not survive assembly"
    [ -f "$post_root/adapter/activity/InputEventDeviceProjection.smali" ] \
        || die "runtime input-device projection class did not survive assembly"
    [ "$(rg -c 'AudioCompatBootstrap;->load' \
        "$post_root/adapter/activity/AppSchedulerBridge.smali")" = 1 ] \
        || die "runtime audio bootstrap call did not survive assembly"
    [ -f "$post_root/adapter/audio/AudioCompatBootstrap.smali" ] \
        || die "runtime audio bootstrap class did not survive assembly"
    rg -F -q 'MotionEvent;->obtain(JJIFFFFIFFII)Landroid/view/MotionEvent;' \
        "$post_root/adapter/activity/InputEventDeviceProjection.smali" \
        || die "runtime input-device projection lost full MotionEvent reconstruction"
    rg -F -q 'InputDevice;->getDeviceIds()' \
        "$post_root/adapter/activity/InputEventDeviceProjection.smali" \
        || die "runtime input-device projection lost touchscreen discovery"
    rg -q 'const/16 [vp][0-9]+, 0x1e' \
        "$post_root/adapter/activity/StorageManagerProjectionProxy\$MountBinder.smali" \
        || die "runtime storage-manager transaction did not survive assembly"
    rg -q 'ZZ.StorageVolume.getVolumeList' \
        "$post_root/adapter/activity/StorageManagerProjectionProxy.smali" \
        "$post_root/adapter/activity/StorageManagerProjectionProxy\$MountBinder.smali" \
        || die "runtime storage-manager trace marker did not survive assembly"
    rg -q 'TRANSACTION_isUserUnlockingOrUnlocked' \
        "$post_root/adapter/activity/UserManagerProjectionProxy.smali" \
        || die "runtime user-manager transaction lookup did not survive assembly"
    rg -q 'ZZ.UserManager.isUserUnlockingOrUnlocked' \
        "$post_root/adapter/activity/UserManagerProjectionProxy.smali" \
        "$post_root/adapter/activity/UserManagerProjectionProxy\$UserBinder.smali" \
        || die "runtime user-manager trace marker did not survive assembly"
    rg -q 'TRANSACTION_getWifiDisplayStatus' \
        "$post_root/adapter/activity/DisplayManagerProjectionProxy.smali" \
        || die "runtime display-manager transaction lookup did not survive assembly"
    rg -q 'ZZ.DisplayManager.getWifiDisplayStatus' \
        "$post_root/adapter/activity/DisplayManagerProjectionProxy.smali" \
        "$post_root/adapter/activity/DisplayManagerProjectionProxy\$DisplayBinder.smali" \
        || die "runtime display-manager trace marker did not survive assembly"
    rg -q 'registerCallbackWithEventMask' \
        "$post_root/adapter/activity/DisplayManagerProjectionProxy\$DisplayInvocationHandler.smali" \
        || die "runtime display-manager callback interception did not survive assembly"
    rg -q '\[ZZ-DISPLAY-EVENT\] registered' \
        "$post_root/adapter/activity/DisplayManagerProjectionProxy.smali" \
        || die "runtime display-manager event marker did not survive assembly"
    rg -q '\[ZZ-PM\] projected getApplicationInfo' \
        "$post_root/adapter/activity/PackageManagerProjectionProxy.smali" \
        || die "runtime package-manager projection marker did not survive assembly"
    rg -q 'Ljava/io/File;->isDirectory\(\)Z' \
        "$post_root/adapter/activity/PackageManagerProjectionProxy.smali" \
        || die "runtime extracted-native-directory check did not survive assembly"
    [ "$(rg -c 'Landroid/content/pm/ApplicationInfo;->primaryCpuAbi:Ljava/lang/String;' \
        "$post_root/adapter/activity/PackageManagerProjectionProxy.smali")" = 1 ] \
        || die "runtime primaryCpuAbi direct write did not survive assembly"
    rg -q 'const-string [vp][0-9]+, "ZZ-PM:apk-zip-disabled"' \
        "$post_root/adapter/activity/PackageManagerProjectionProxy.smali" \
        || die "runtime ABI selector trace marker did not survive assembly"
    rg -q '\[ZZ-PM\] extracted native path selected; apk zip path disabled' \
        "$post_root/adapter/activity/PackageManagerProjectionProxy.smali" \
        || die "runtime extracted-native-path marker did not survive assembly"
    touch -t 198001010000 "$package/META-INF/MANIFEST.MF" "$package/classes.dex"
    (cd "$package" && "$ZIP_BIN" -X -q "$output" META-INF/MANIFEST.MF classes.dex)
    unzip -t "$output" >/dev/null || die "runtime jar zip verification failed"
    unzip -p "$output" classes.dex > "$build/postflight.dex"
    rg -a -q 'extractNativeLibs' "$build/postflight.dex" || die "runtime jar marker missing"
    rg -a -q '\[ZZ-PM\] projected getApplicationInfo' "$build/postflight.dex" \
        || die "runtime jar package-manager projection marker missing"
    rg -a -q '\[ZZ-PM\] extracted native path selected; apk zip path disabled' \
        "$build/postflight.dex" \
        || die "runtime jar extracted-native-path marker missing"
    rg -a -q 'ZZ-PM:apk-zip-disabled' "$build/postflight.dex" \
        || die "runtime jar ABI selector trace marker missing"
    rg -a -q 'ZZ.StorageVolume.getVolumeList' "$build/postflight.dex" \
        || die "runtime jar storage-manager trace marker missing"
    rg -a -q '\[ZZ-STORAGE\] installed child-local mount binder' "$build/postflight.dex" \
        || die "runtime jar storage-manager install marker missing"
    rg -a -q 'ZZ.UserManager.isUserUnlockingOrUnlocked' "$build/postflight.dex" \
        || die "runtime jar user-manager trace marker missing"
    rg -a -q '\[ZZ-USER\] installed child-local user binder' "$build/postflight.dex" \
        || die "runtime jar user-manager install marker missing"
    rg -a -q '\[ZZ-DISPLAY-EVENT\] registered' "$build/postflight.dex" \
        || die "runtime jar display-manager event marker missing"
    rg -a -q '\[CAPY-LETTERBOX\] applied frame=' "$build/postflight.dex" \
        || die "runtime jar Capybara letterbox marker missing"
    rg -a -q '\[OH_AudioCompat\] bridge loaded' "$build/postflight.dex" \
        || die "runtime jar audio bootstrap marker missing"
}

verify_signal_abi_layouts()
{
    local build=$1 oh_cc
    oh_cc="$OH_SDK/llvm/bin/clang"
    mkdir -p "$build"
    "$ANDROID_NDK_CLANG" -D_GNU_SOURCE -std=gnu11 -Wall -Wextra -Werror \
        -DWESTLAKE_EXPECT_SIGSET_SIZE=8 \
        -DWESTLAKE_EXPECT_SIGACTION_SIZE=32 \
        -c "$SIGNAL_ABI_PROBE_SOURCE" -o "$build/android-bionic.o"
    "$oh_cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -D_GNU_SOURCE -std=gnu11 -Wall -Wextra -Werror \
        -DWESTLAKE_EXPECT_SIGSET_SIZE=128 \
        -DWESTLAKE_EXPECT_SIGACTION_SIZE=152 \
        -c "$SIGNAL_ABI_PROBE_SOURCE" -o "$build/oh-musl.o"
    "$NM" --defined-only "$build/android-bionic.o" \
        | grep -q 'westlake_signal_abi_probe' \
        || die "Android Bionic signal ABI probe did not compile"
    "$NM" --defined-only "$build/oh-musl.o" \
        | grep -q 'westlake_signal_abi_probe' \
        || die "OH musl signal ABI probe did not compile"
    printf '%s\n' \
        'ANDROID_SIGSET_SIZE=8' \
        'ANDROID_SIGACTION_SIZE=32' \
        'OH_SIGSET_SIZE=128' \
        'OH_SIGACTION_SIZE=152' > "$build/layout.env"
}

capture_reverse_analysis()
{
    local candidate=$1 raw_tuanjie=$2 patched_tuanjie=$3 signal_box=$4 reverse apk_build_id hap_build_id
    reverse="$candidate/reverse-analysis"
    mkdir -p "$reverse"

    unzip -p "$ZIGZAG_APK" classes.dex > "$reverse/apk-classes.dex"
    "$DEXDUMP_BIN" -c "$reverse/apk-classes.dex" \
        > "$reverse/apk-dex-check.txt" 2>&1
    "$DEXDUMP_BIN" -f "$reverse/apk-classes.dex" \
        > "$reverse/apk-dex-header.txt"
    JAVA_HOME="$DEV_ECO_JAVA_HOME" "$APKANALYZER_BIN" manifest print "$ZIGZAG_APK" \
        > "$reverse/apk-manifest.xml"
    JAVA_HOME="$DEV_ECO_JAVA_HOME" "$APKANALYZER_BIN" dex code \
        --class com.unity3d.player.UnityPlayerActivity "$ZIGZAG_APK" \
        > "$reverse/UnityPlayerActivity.smali"
    JAVA_HOME="$DEV_ECO_JAVA_HOME" "$APKANALYZER_BIN" dex code \
        --class com.unity3d.player.UnityPlayer "$ZIGZAG_APK" \
        > "$reverse/UnityPlayer.smali"

    unzip -p "$ZIGZAG_CONTROL_HAP" module.json > "$reverse/hap-module.json"
    unzip -p "$ZIGZAG_CONTROL_HAP" ets/modules.abc > "$reverse/hap-modules.abc"
    "$ARK_DISASM_BIN" --quiet "$reverse/hap-modules.abc" \
        "$reverse/hap-modules.pa"
    unzip -p "$ZIGZAG_CONTROL_HAP" libs/arm64-v8a/libtuanjie.so \
        > "$reverse/hap-libtuanjie.so"
    apk_build_id=$(elf_build_id "$raw_tuanjie")
    hap_build_id=$(elf_build_id "$reverse/hap-libtuanjie.so")
    [ "$apk_build_id" = "$ANDROID_TUANJIE_BUILD_ID" ] \
        || die "APK Tuanjie does not match the Android unstripped reference"
    [ "$hap_build_id" = "$OH_TUANJIE_BUILD_ID" ] \
        || die "HAP Tuanjie does not match the OH unstripped reference"
    printf 'APK_TUANJIE_BUILD_ID=%s\nHAP_TUANJIE_BUILD_ID=%s\n' \
        "$apk_build_id" "$hap_build_id" > "$reverse/twin-build-ids.env"

    "$READELF" -dW "$raw_tuanjie" > "$reverse/android-apk-tuanjie-dynamic.txt"
    "$READELF" -rW "$raw_tuanjie" > "$reverse/android-apk-tuanjie-relocations.txt"
    "$NM" -D --undefined-only "$raw_tuanjie" \
        > "$reverse/android-apk-tuanjie-undefined.txt"
    "$OBJDUMP" -d --start-address=0x698238 --stop-address=0x698490 \
        "$raw_tuanjie" > "$reverse/android-apk-signal-callsite.txt"
    "$READELF" -dW "$patched_tuanjie" > "$reverse/patched-tuanjie-dynamic.txt"
    "$READELF" -rW "$patched_tuanjie" > "$reverse/patched-tuanjie-relocations.txt"
    "$NM" -D --undefined-only "$patched_tuanjie" \
        > "$reverse/patched-tuanjie-undefined.txt"
    "$NM" -D --defined-only "$signal_box" \
        > "$reverse/guest-signal-box-defined.txt"
    "$READELF" -dW "$ANDROID_TUANJIE_REFERENCE" \
        > "$reverse/reference-android-tuanjie-dynamic.txt"
    "$READELF" -dW "$OH_TUANJIE_REFERENCE" \
        > "$reverse/reference-oh-tuanjie-dynamic.txt"
    "$OBJDUMP" -d --start-address=0xaaeac0 --stop-address=0xaaeb20 \
        "$ANDROID_TUANJIE_REFERENCE" \
        > "$reverse/reference-android-core-getproc.txt"
    "$OBJDUMP" -d --start-address=0x9818a8 --stop-address=0x9818c8 \
        "$OH_TUANJIE_REFERENCE" \
        > "$reverse/reference-oh-core-getproc.txt"
    "$OBJDUMP" -d --start-address=0xaaeac0 --stop-address=0xaaeb20 \
        "$patched_tuanjie" > "$reverse/patched-core-getproc.txt"
    "$NM" -D --undefined-only "$ANDROID_TUANJIE_REFERENCE" \
        | awk '{print $NF}' | sed 's/@.*//' | LC_ALL=C sort -u \
        > "$reverse/reference-android-imports.txt"
    "$NM" -D --undefined-only "$OH_TUANJIE_REFERENCE" \
        | awk '{print $NF}' | sed 's/@.*//' | LC_ALL=C sort -u \
        > "$reverse/reference-oh-imports.txt"
    LC_ALL=C comm -23 "$reverse/reference-android-imports.txt" \
        "$reverse/reference-oh-imports.txt" > "$reverse/adapter-gap-seed.txt"
    LC_ALL=C comm -13 "$reverse/reference-android-imports.txt" \
        "$reverse/reference-oh-imports.txt" > "$reverse/oh-native-contract.txt"
    LC_ALL=C comm -12 "$reverse/reference-android-imports.txt" \
        "$reverse/reference-oh-imports.txt" > "$reverse/shared-contract.txt"

    rg -q 'android:extractNativeLibs="true"' "$reverse/apk-manifest.xml" \
        || die "APK reverse analysis lost extractNativeLibs=true"
    rg -q 'android:name="com.unity3d.player.UnityPlayerActivity"' \
        "$reverse/apk-manifest.xml" || die "APK reverse analysis lost Unity activity"
    rg -q 'new-instance .*Lcom/unity3d/player/UnityPlayer;' \
        "$reverse/UnityPlayerActivity.smali" \
        || die "DEX reverse analysis lost UnityPlayer construction"
    rg -q 'ApplicationInfo;->nativeLibraryDir' "$reverse/UnityPlayer.smali" \
        || die "DEX reverse analysis lost nativeLibraryDir selection"
    rg -q 'Ljava/lang/System;->load\(Ljava/lang/String;\)V' \
        "$reverse/UnityPlayer.smali" || die "DEX reverse analysis lost System.load"
    rg -q '"mainElement":"TuanjiePlayerAbility"' "$reverse/hap-module.json" \
        || die "HAP reverse analysis lost TuanjiePlayerAbility"
    rg -q 'sigemptyset@LIBC' "$reverse/android-apk-tuanjie-relocations.txt" \
        || die "raw Tuanjie relocation no longer proves sigemptyset@LIBC"
    rg -q 'sigaction@LIBC' "$reverse/android-apk-tuanjie-relocations.txt" \
        || die "raw Tuanjie relocation no longer proves sigaction@LIBC"
    rg -q '6983dc:.*<sigemptyset@plt>' "$reverse/android-apk-signal-callsite.txt" \
        || die "raw Tuanjie signal callsite drifted at 0x6983dc"
    rg -q '698408:.*<sigaction@plt>' "$reverse/android-apk-signal-callsite.txt" \
        || die "raw Tuanjie signal callsite drifted at 0x698408"
    rg -q '698474:.*<__stack_chk_fail@plt>' \
        "$reverse/android-apk-signal-callsite.txt" \
        || die "raw Tuanjie canary failure branch drifted at 0x698474"
    rg -q 'westlake_bionic_sigaction@LIBC' \
        "$reverse/patched-tuanjie-relocations.txt" \
        || die "patched Tuanjie lacks private sigaction relocation"
    rg -q 'aaead4: f81e0ffe.*str' "$reverse/reference-android-core-getproc.txt" \
        || die "Android Tuanjie core resolver prologue drifted"
    rg -q '9818bc: 141a4ac9.*b.*eglGetProcAddress@plt' \
        "$reverse/reference-oh-core-getproc.txt" \
        || die "OH Tuanjie no longer routes core GL lookup to eglGetProcAddress"
    rg -q 'aaead4: 14000011.*b.*0xaaeb18' \
        "$reverse/patched-core-getproc.txt" \
        || die "patched Android Tuanjie core resolver does not match the OH route"
    rg -q '^ANativeWindow_fromSurface$' "$reverse/adapter-gap-seed.txt" \
        || die "Android/OH paired reference lost ANativeWindow gap"
    rg -q '^OH_NativeWindow_NativeWindowHandleOpt$' \
        "$reverse/oh-native-contract.txt" \
        || die "Android/OH paired reference lost OH native-window contract"
}

build_unity_libc_bridge()
{
    local output=$1 build=$2 cc strip header machine needed
    cc="$OH_SDK/llvm/bin/clang"
    strip="$OH_SDK/llvm/bin/llvm-strip"
    mkdir -p "$build"

    "$cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -fPIC -O2 -g -D__OHOS__ -D_GNU_SOURCE -std=c11 \
        -Wall -Wextra -Werror -pedantic -fno-stack-protector \
        -fno-unwind-tables -fno-asynchronous-unwind-tables \
        -mno-outline-atomics -I"$PTHREAD_BRIDGE_ROOT/include" \
        -c "$PTHREAD_BRIDGE_SOURCE" -o "$build/bionic_pthread_bridge.o"
    "$cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -fPIC -O2 -g -D__OHOS__ -D_GNU_SOURCE -std=c11 \
        -Wall -Wextra -Wno-error -I"$PTHREAD_BRIDGE_ROOT/include" \
        -c "$UNITY_LIBC_STUB_SOURCE" -o "$build/unity_libc_stubs.o"
    "$OH_SDK/llvm/bin/clang++" --target=aarch64-linux-ohos \
        --sysroot="$OH_SDK/sysroot" -fPIC -O2 -g -D__OHOS__ -D_GNU_SOURCE \
        -std=c++17 -Wall -Wextra -Wno-error \
        -c "$ABORT_MESSAGE_COMPAT_SOURCE" -o "$build/abort_message_compat.o"
    "$cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -fPIC -O2 -g -D__OHOS__ -D_GNU_SOURCE -std=c11 \
        -Wall -Wextra -Werror -pedantic -fno-stack-protector \
        -fno-unwind-tables -fno-asynchronous-unwind-tables \
        -mno-outline-atomics \
        -c "$PTHREAD_PROPERTY_SOURCE" -o "$build/bionic_property_bridge.o"
    "$cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -B"$OH_SDK/llvm/bin" -fuse-ld=lld -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro -Wl,--no-undefined \
        -Wl,--fatal-warnings -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libwestlake_bionic_pthread_bridge.so \
        -Wl,--version-script="$PTHREAD_BRIDGE_MAP" \
        "$build/bionic_pthread_bridge.o" "$build/unity_libc_stubs.o" \
        "$build/abort_message_compat.o" "$build/bionic_property_bridge.o" \
        -lc -ldl -lpthread -o "$build/libwestlake_bionic_pthread_bridge.so.unstripped"
    cp "$build/libwestlake_bionic_pthread_bridge.so.unstripped" "$output"
    "$strip" --strip-unneeded "$output"

    header=$("$READELF" -hW "$output")
    machine=$(printf '%s\n' "$header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')
    [ "$machine" = "AArch64" ] || die "Unity libc bridge is not AArch64"
    needed=$("$READELF" -dW "$output")
    printf '%s\n' "$needed" | grep -Fq 'Library soname: [libwestlake_bionic_pthread_bridge.so]' \
        || die "Unity libc bridge SONAME drifted"
    printf '%s\n' "$needed" | grep -Fq 'Shared library: [libc.so]' \
        || die "Unity libc bridge does not bind the OH musl provider"
    "$NM" -D --defined-only "$output" > "$build/dynsym.txt"
    rg -q ' __sF@@LIBC$' "$build/dynsym.txt" \
        || die "Unity libc bridge lacks __sF@@LIBC"
    rg -q ' _ctype_@@LIBC$' "$build/dynsym.txt" \
        || die "Unity libc bridge lacks _ctype_@@LIBC"
    rg -q ' android_set_abort_message@@LIBC$' "$build/dynsym.txt" \
        || die "Unity libc bridge lacks android_set_abort_message@@LIBC"
    for property_symbol in __system_property_find __system_property_get __system_property_read; do
        rg -q " ${property_symbol}@@LIBC$" "$build/dynsym.txt" \
            || die "Unity libc bridge lacks ${property_symbol}@@LIBC"
    done
    ! rg -q ' sig(action|emptyset|fillset|addset|delset|ismember|procmask)@@LIBC$' \
        "$build/dynsym.txt" \
        || die "appspawn-wide Unity libc bridge leaks a Bionic signal ABI"
    rg -q ' WLPB_InstallHostOps@@WESTLAKE_WLPB_1$' "$build/dynsym.txt" \
        || die "Unity libc bridge lost WLPB bootstrap"
}

build_bionic_signal_box()
{
    local output=$1 build=$2 cc strip header machine dynamic needed symbols symbol
    cc="$OH_SDK/llvm/bin/clang"
    strip="$OH_SDK/llvm/bin/llvm-strip"
    mkdir -p "$build"

    "$cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -fPIC -O2 -g -D__OHOS__ -D_GNU_SOURCE \
        -DWESTLAKE_SIGNAL_BOX_NAMESPACE=1 -std=c11 \
        -Wall -Wextra -Werror -pedantic -fno-stack-protector \
        -fno-unwind-tables -fno-asynchronous-unwind-tables \
        -mno-outline-atomics \
        -I"$SIGNAL_BOX_ROOT/include" \
        -c "$UNITY_SIGNAL_SOURCE" -o "$build/unity_signal_box.o"
    "$cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -fPIC -O2 -g -D__OHOS__ -D_GNU_SOURCE -std=c11 \
        -Wall -Wextra -Werror -pedantic -fno-stack-protector \
        -fno-unwind-tables -fno-asynchronous-unwind-tables \
        -mno-outline-atomics \
        -I"$SIGNAL_BOX_ROOT/include" \
        -c "$SIGNAL_BACKEND_SOURCE" -o "$build/oh_musl_signal_backend.o"
    "$cc" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -B"$OH_SDK/llvm/bin" -fuse-ld=lld -shared \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro -Wl,--no-undefined \
        -Wl,--fatal-warnings -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libwestlake_bionic_signal_box.so \
        -Wl,--version-script="$SIGNAL_BOX_MAP" \
        "$build/unity_signal_box.o" "$build/oh_musl_signal_backend.o" -lc \
        -o "$build/libwestlake_bionic_signal_box.so.unstripped"
    cp "$build/libwestlake_bionic_signal_box.so.unstripped" "$output"
    "$strip" --strip-unneeded "$output"

    header=$("$READELF" -hW "$output")
    machine=$(printf '%s\n' "$header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')
    [ "$machine" = AArch64 ] || die "guest signal box is not AArch64"
    dynamic=$("$READELF" -dW "$output")
    printf '%s\n' "$dynamic" \
        | grep -Fq 'Library soname: [libwestlake_bionic_signal_box.so]' \
        || die "guest signal-box SONAME drifted"
    needed=$(printf '%s\n' "$dynamic" \
        | awk -F'[][]' '/Shared library:/ {print $2}' | paste -sd, -)
    [ "$needed" = libc.so ] || die "guest signal-box NEEDED closure drifted: $needed"
    symbols="$build/dynsym.txt"
    "$NM" -D --defined-only "$output" > "$symbols"
    for symbol in signal sigaction sigemptyset sigfillset sigaddset sigdelset \
            sigismember sigprocmask pthread_sigmask sigsuspend sigaltstack; do
        rg -q " westlake_bionic_${symbol}@@LIBC$" "$symbols" \
            || die "guest signal box lacks westlake_bionic_${symbol}@@LIBC"
    done
    ! rg -q ' (signal|sig(action|emptyset|fillset|addset|delset|ismember|procmask|suspend|altstack)|pthread_sigmask)@@LIBC$' \
        "$symbols" || die "guest signal box exposes an unscoped signal symbol"
}

build_mediandk_presence()
{
    local output=$1 build=$2 header machine dynamic needed_count tuanjie
    mkdir -p "$build"
    "$ANDROID_NDK_CLANG" -nostdlib -shared -fPIC -O2 \
        -Wall -Wextra -Werror -pedantic \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro -Wl,--no-undefined \
        -Wl,--fatal-warnings -Wl,--build-id=sha1 \
        -Wl,-soname,libmediandk.so \
        "$MEDIANDK_PRESENCE_SOURCE" -o "$output"

    header=$("$READELF" -hW "$output")
    machine=$(printf '%s\n' "$header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')
    [ "$machine" = "AArch64" ] || die "presence-only media provider is not AArch64"
    dynamic=$("$READELF" -dW "$output")
    printf '%s\n' "$dynamic" | grep -Fq 'Library soname: [libmediandk.so]' \
        || die "presence-only media provider SONAME drifted"
    needed_count=$(printf '%s\n' "$dynamic" | awk '/Shared library:/ {count++} END {print count + 0}')
    [ "$needed_count" = 0 ] || die "presence-only media provider unexpectedly depends on another DSO"
    "$NM" -D --defined-only "$output" \
        | rg -q ' westlake_mediandk_presence_provenance$' \
        || die "presence-only media provider lacks its provenance symbol"

    tuanjie="$build/libtuanjie.so"
    unzip -p "$ZIGZAG_APK" 'lib/arm64-v8a/libtuanjie.so' > "$tuanjie"
    [ "$(( $(stat -f '%z' "$tuanjie") ))" -gt 0 ] || die "ZigZag libtuanjie extraction failed"
    [ "$("$READELF" -dW "$tuanjie" | grep -Fc 'Shared library: [libmediandk.so]')" = 1 ] \
        || die "ZigZag libtuanjie does not have exactly one libmediandk DT_NEEDED edge"
    if "$NM" -D --undefined-only "$tuanjie" | rg -q ' (AMedia|AImage)[A-Za-z0-9_]*$'; then
        die "ZigZag libtuanjie now references an NDK media API; presence-only provider is invalid"
    fi
}

build_native_loader()
{
    local output=$1 build=$2 cxx strip source object objects=() dynamic needed
    cxx="$OH_SDK/llvm/bin/clang++"
    strip="$OH_SDK/llvm/bin/llvm-strip"
    mkdir -p "$build"
    for source in native_loader.cpp native_loader_registry.cpp system_loader.cpp; do
        object="$build/${source%.cpp}.o"
        "$cxx" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
            -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE \
            -nostdinc++ -isystem "$LIBCXX_INCLUDE" \
            -std=gnu++17 -fno-exceptions -fno-rtti \
            -Wall -Wextra -Werror \
            -I"$ADAPTER_ROOT/framework/native-loader-oh/include" \
            -I"$ADAPTER_ROOT/framework/native-loader-oh/src" \
            -I"$ADAPTER_ROOT/framework/app-native-loader/include" \
            -I"$PTHREAD_BRIDGE_ROOT/include" \
            -I"$AOSP_ROOT/libnativehelper/include_jni" \
            -c "$ADAPTER_ROOT/framework/native-loader-oh/src/$source" \
            -o "$object"
        objects+=("$object")
    done
    "$cxx" --target=aarch64-linux-ohos --sysroot="$OH_SDK/sysroot" \
        -B"$OH_SDK/llvm/bin" -fuse-ld=lld -shared -nostdlib++ \
        -Wl,-z,defs -Wl,-z,now -Wl,-z,relro \
        -Wl,--no-allow-shlib-undefined -Wl,--no-undefined \
        -Wl,--fatal-warnings -Wl,--build-id=sha1 -Wl,--hash-style=both \
        -Wl,-soname,libnativeloader.so \
        -Wl,--version-script="$ADAPTER_ROOT/framework/native-loader-oh/native_loader.map" \
        "${objects[@]}" -Wl,--no-as-needed \
        "$RAW_PR03/android/lib64/libapp_native_loader.so" \
        -Wl,--as-needed "$LINK_INPUTS/libc++.so" "$LINK_INPUTS/libc.so" \
        -ldl -lpthread -o "$build/libnativeloader.so.unstripped"
    cp "$build/libnativeloader.so.unstripped" "$output"
    "$strip" --strip-unneeded "$output"

    [ "$("$READELF" -hW "$output" \
        | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = AArch64 ] \
        || die "native loader is not AArch64"
    dynamic=$("$READELF" -dW "$output")
    printf '%s\n' "$dynamic" | grep -Fq 'Library soname: [libnativeloader.so]' \
        || die "native loader SONAME drifted"
    needed=$(printf '%s\n' "$dynamic" \
        | awk -F'[][]' '/Shared library:/ {print $2}' | paste -sd, -)
    [ "$needed" = "libapp_native_loader.so,libc++.so,libc.so" ] \
        || die "native loader NEEDED closure drifted: $needed"
    "$NM" -D --defined-only "$output" \
        | rg -q ' CreateClassLoaderNamespace@@WESTLAKE_NATIVELOADER_1$' \
        || die "native loader lacks CreateClassLoaderNamespace"
    "$NM" -D -C "$output" | rg -q 'std::__h::' \
        || die "native loader does not bind the board std::__h ABI"
    ! "$NM" -D -C "$output" | rg -q 'std::__n1::' \
        || die "native loader leaked the SDK std::__n1 ABI"
    strings "$output" | grep -Fxq '/system/lib64/platformsdk' \
        || die "native loader lacks the platform SDK bridge path"
}

verify_unity_android_provider()
{
    local provider=$1 symbols symbol
    [ "$("$READELF" -hW "$provider" \
        | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = AArch64 ] \
        || die "Unity Android provider is not AArch64: $provider"
    symbols=$("$NM" -D --defined-only "$provider" | awk '{print $NF}')
    for symbol in \
        ALooper_acquire ALooper_forThread ALooper_pollOnce ALooper_prepare \
        ALooper_release ALooper_wake ANativeWindow_acquire \
        ANativeWindow_fromSurface ANativeWindow_getHeight ANativeWindow_getWidth \
        ANativeWindow_release ANativeWindow_setBuffersGeometry ASensor_getMinDelay \
        ASensor_getName ASensor_getResolution ASensor_getType ASensor_getVendor \
        ASensorEventQueue_disableSensor ASensorEventQueue_enableSensor \
        ASensorEventQueue_getEvents ASensorEventQueue_hasEvents \
        ASensorEventQueue_setEventRate ASensorManager_createEventQueue \
        ASensorManager_destroyEventQueue ASensorManager_getDefaultSensor \
        ASensorManager_getInstance ASensorManager_getSensorList; do
        printf '%s\n' "$symbols" | grep -qx "$symbol" \
            || die "Unity Android provider lacks $symbol: $provider"
    done
}

build_patched_libmain()
{
    local output=$1 build=$2 original needed_count
    mkdir -p "$build"
    unzip -j -q "$ZIGZAG_APK" 'lib/arm64-v8a/libmain.so' -d "$build"
    original="$build/libmain.so"
    require_hash "$ZIGZAG_LIBMAIN_RAW_SHA" "$original"
    cp "$original" "$output"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_pthread_bridge.so "$output"
    needed_count=$("$READELF" -dW "$output" \
        | grep -Fc 'Shared library: [libwestlake_bionic_pthread_bridge.so]')
    [ "$needed_count" = 1 ] || die "patched libmain lacks one direct pthread-bridge edge"
    [ "$("$READELF" -hW "$output" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = AArch64 ] \
        || die "patched libmain is not AArch64"
}

build_patched_libil2cpp()
{
    local output=$1 build=$2 original needed_count signal_needed_count first_needed symbols
    mkdir -p "$build"
    unzip -j -q "$ZIGZAG_APK" 'lib/arm64-v8a/libil2cpp.so' -d "$build"
    original="$build/libil2cpp.so"
    require_hash "$ZIGZAG_LIBIL2CPP_RAW_SHA" "$original"
    for signal_symbol in signal sigaction sigemptyset sigfillset sigaddset sigdelset \
            pthread_sigmask sigsuspend sigaltstack; do
        "$NM" -D --undefined-only "$original" \
            | rg -q " ${signal_symbol}@LIBC$" \
            || die "raw ZigZag libil2cpp lacks ${signal_symbol}@LIBC"
    done
    cp "$original" "$output"
    "$PATCHELF_BIN" --rename-dynamic-symbols "$SIGNAL_RENAME_MAP" "$output"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_pthread_bridge.so "$output"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_signal_box.so "$output"
    needed_count=$("$READELF" -dW "$output" \
        | grep -Fc 'Shared library: [libwestlake_bionic_pthread_bridge.so]')
    [ "$needed_count" = 1 ] || die "patched libil2cpp lacks one direct Bionic bridge edge"
    signal_needed_count=$("$READELF" -dW "$output" \
        | grep -Fc 'Shared library: [libwestlake_bionic_signal_box.so]')
    [ "$signal_needed_count" = 1 ] \
        || die "patched libil2cpp lacks one direct signal-box edge"
    first_needed=$("$READELF" -dW "$output" \
        | awk -F'[][]' '/Shared library:/ {print $2; exit}')
    [ "$first_needed" = libwestlake_bionic_signal_box.so ] \
        || die "patched libil2cpp does not search the guest signal box first"
    [ "$("$READELF" -dW "$output" \
        | awk -F'[][]' '/Shared library:/ {print $2; exit}')" = \
        libwestlake_bionic_signal_box.so ] \
        || die "patched libil2cpp does not search the signal box first"
    [ "$("$READELF" -hW "$output" \
        | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = AArch64 ] \
        || die "patched libil2cpp is not AArch64"
    "$NM" -D --undefined-only "$output" | rg -q ' __errno@LIBC$' \
        || die "ZigZag libil2cpp no longer has the observed __errno@LIBC edge"
    symbols="$build/patched-undefined.txt"
    "$NM" -D --undefined-only "$output" > "$symbols"
    for signal_symbol in signal sigaction sigemptyset sigfillset sigaddset sigdelset \
            pthread_sigmask sigsuspend sigaltstack; do
        rg -q " westlake_bionic_${signal_symbol}@LIBC$" "$symbols" \
            || die "patched libil2cpp lacks private ${signal_symbol} import"
        ! rg -q " ${signal_symbol}@LIBC$" "$symbols" \
            || die "patched libil2cpp retains raw ${signal_symbol} import"
    done
}

build_patched_libtuanjie()
{
    local output=$1 build=$2 original needed_count first_needed symbols
    mkdir -p "$build"
    unzip -j -q "$ZIGZAG_APK" 'lib/arm64-v8a/libtuanjie.so' -d "$build"
    original="$build/libtuanjie.so"
    require_hash "$ZIGZAG_LIBTUANJIE_RAW_SHA" "$original"
    "$NM" -D --undefined-only "$original" | rg -q ' sigaction@LIBC$' \
        || die "raw ZigZag libtuanjie lacks the observed sigaction@LIBC edge"
    "$NM" -D --undefined-only "$original" | rg -q ' sigemptyset@LIBC$' \
        || die "raw ZigZag libtuanjie lacks the observed sigemptyset@LIBC edge"
    cp "$original" "$output"
    "$PATCHELF_BIN" --rename-dynamic-symbols "$SIGNAL_RENAME_MAP" "$output"
    "$PATCHELF_BIN" --add-needed libwestlake_bionic_signal_box.so "$output"
    patch_binary_hex_exact "$output" "$TUANJIE_CORE_GETPROC_FILE_OFFSET" \
        "$TUANJIE_CORE_GETPROC_OLD_HEX" "$TUANJIE_CORE_GETPROC_EGL_HEX" \
        "Tuanjie GetProcAddress_core -> eglGetProcAddress"
    needed_count=$("$READELF" -dW "$output" \
        | grep -Fc 'Shared library: [libwestlake_bionic_signal_box.so]')
    [ "$needed_count" = 1 ] || die "patched libtuanjie lacks one direct signal-box edge"
    first_needed=$("$READELF" -dW "$output" \
        | awk -F'[][]' '/Shared library:/ {print $2; exit}')
    [ "$first_needed" = libwestlake_bionic_signal_box.so ] \
        || die "patched libtuanjie does not search the guest signal box first"
    [ "$("$READELF" -hW "$output" \
        | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = AArch64 ] \
        || die "patched libtuanjie is not AArch64"
    symbols="$build/patched-undefined.txt"
    "$NM" -D --undefined-only "$output" > "$symbols"
    rg -q ' westlake_bionic_sigaction@LIBC$' "$symbols" \
        || die "patched libtuanjie lacks private sigaction import"
    rg -q ' westlake_bionic_sigemptyset@LIBC$' "$symbols" \
        || die "patched libtuanjie lacks private sigemptyset import"
    rg -q ' westlake_bionic_sigaltstack@LIBC$' "$symbols" \
        || die "patched libtuanjie lacks private sigaltstack import"
    ! rg -q ' sig(action|emptyset|altstack)@LIBC$' "$symbols" \
        || die "patched libtuanjie retains a collision-prone signal import"
    [ "$(binary_hex_at "$output" "$TUANJIE_CORE_GETPROC_FILE_OFFSET" 4)" = \
        "$TUANJIE_CORE_GETPROC_EGL_HEX" ] \
        || die "patched libtuanjie lost its deterministic EGL core resolver"
    "$OBJDUMP" -d --start-address="$TUANJIE_CORE_GETPROC_VADDR" \
        --stop-address=0xaaeb20 "$output" > "$build/core-getproc.txt"
    rg -q 'aaead4: 14000011.*b.*0xaaeb18' "$build/core-getproc.txt" \
        || die "patched libtuanjie core resolver branch is not decodable"
}

build_candidate()
{
    local candidate_id candidate build_out object_out files adapter provider child appspawn runtime_jar pthread_bridge native_loader libandroid mediandk signal_box patched_libmain patched_libil2cpp patched_libtuanjie
    local adapter_sha provider_sha child_sha appspawn_sha runtime_jar_sha pthread_bridge_sha pthread_bridge_build_id native_loader_sha native_loader_build_id libandroid_sha mediandk_sha mediandk_build_id signal_box_sha signal_box_build_id patched_libmain_sha patched_libil2cpp_sha patched_libtuanjie_sha build_id symbols
    verify_local_inputs
    candidate_id="strict-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    candidate="$CANDIDATES_ROOT/$candidate_id"
    build_out="$candidate/build/adapter"
    object_out="$candidate/build/objects"
    files="$candidate/files"
    mkdir -p "$build_out" "$object_out" "$files"
    cp "$RAW_PR03/route/libwestlake_thread_guard_registry.so" \
        "$build_out/libwestlake_thread_guard_registry.so"

    step "strict local adapter build: $candidate_id"
    env \
        BUILD_INNER_INVOKED=1 \
        ADAPTER_ROOT="$ADAPTER_ROOT" \
        ADAPTER_OUT_DIR="$build_out" \
        BRIDGE_OBJ_DIR="$object_out" \
        AOSP_ROOT="$AOSP_ROOT" \
        AOSP_LIB_DIR="$RAW_PR03/android/lib64" \
        OH_ROOT="$OH_ROOT" \
        OH_HEADER_OUT="$OH_HEADER_OUT" \
        OH_SDK="$OH_SDK" \
        OH61_LINK_INPUTS="$LINK_INPUTS" \
        OH_LIBCXX_INCLUDE="$LIBCXX_INCLUDE" \
        OH61_GENERATED_HEADERS="$OH61_GENERATED_HEADERS" \
        FORCE_OH_SDK=1 \
        L03_A12_STRICT_BUILD=1 \
        bash "$ADAPTER_ROOT/build/inner/compile_oh_adapter_bridge_arm64.sh" --clean \
        2>&1 | tee "$candidate/build.log"

    adapter="$files/liboh_adapter_bridge.so"
    provider="$files/libwestlake_android_runtime_provider.so"
    child="$files/libwestlake_android_child.z.so"
    appspawn="$files/appspawn-x"
    runtime_jar="$files/oh-adapter-runtime.jar"
    pthread_bridge="$files/libwestlake_bionic_pthread_bridge.so"
    native_loader="$files/libnativeloader.so"
    libandroid="$files/libandroid.so"
    mediandk="$files/libmediandk.so"
    signal_box="$files/libwestlake_bionic_signal_box.so"
    patched_libmain="$files/libmain.so"
    patched_libil2cpp="$files/libil2cpp.so"
    patched_libtuanjie="$files/libtuanjie.so"
    cp "$build_out/liboh_adapter_bridge.so" "$adapter"
    cp "$RAW_PR03/route/libwestlake_android_runtime_provider.so" "$provider"
    cp "$RAW_PR03/runtime/libwestlake_android_child.z.so" "$child"
    cp "$RAW_PR03/runtime/appspawn-x" "$appspawn"
    cp "$BASELINE_RUNTIME_LOCAL" "$libandroid"
    build_runtime_jar "$runtime_jar" "$candidate/build/runtime-jar"
    verify_signal_abi_layouts "$candidate/build/signal-abi"
    build_unity_libc_bridge "$pthread_bridge" "$candidate/build/pthread-bridge"
    build_native_loader "$native_loader" "$candidate/build/native-loader"
    build_mediandk_presence "$mediandk" "$candidate/build/mediandk-presence"
    build_bionic_signal_box "$signal_box" "$candidate/build/signal-box"
    build_patched_libmain "$patched_libmain" "$candidate/build/patched-libmain"
    build_patched_libil2cpp "$patched_libil2cpp" "$candidate/build/patched-libil2cpp"
    build_patched_libtuanjie "$patched_libtuanjie" "$candidate/build/patched-libtuanjie"
    capture_reverse_analysis "$candidate" \
        "$candidate/build/patched-libtuanjie/libtuanjie.so" \
        "$patched_libtuanjie" "$signal_box"
    runtime_jar_sha=$(sha256_file "$runtime_jar")
    pthread_bridge_sha=$(sha256_file "$pthread_bridge")
    native_loader_sha=$(sha256_file "$native_loader")
    libandroid_sha=$(sha256_file "$libandroid")
    mediandk_sha=$(sha256_file "$mediandk")
    signal_box_sha=$(sha256_file "$signal_box")
    patched_libmain_sha=$(sha256_file "$patched_libmain")
    patched_libil2cpp_sha=$(sha256_file "$patched_libil2cpp")
    patched_libtuanjie_sha=$(sha256_file "$patched_libtuanjie")
    pthread_bridge_build_id=$("$READELF" --notes --wide "$pthread_bridge" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "${#pthread_bridge_build_id}" -eq 40 ] || die "pthread bridge Build-ID is not SHA1"
    native_loader_build_id=$("$READELF" --notes --wide "$native_loader" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "${#native_loader_build_id}" -eq 40 ] || die "native loader Build-ID is not SHA1"
    mediandk_build_id=$("$READELF" --notes --wide "$mediandk" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "${#mediandk_build_id}" -eq 40 ] || die "presence-only media Build-ID is not SHA1"
    signal_box_build_id=$("$READELF" --notes --wide "$signal_box" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "${#signal_box_build_id}" -eq 40 ] || die "guest signal-box Build-ID is not SHA1"
    [ "$libandroid_sha" = "$RUNTIME_SHA" ] || die "Unity Android provider drifted from board baseline"
    verify_unity_android_provider "$libandroid"

    adapter_sha=$(sha256_file "$adapter")
    build_id=$("$READELF" --notes --wide "$adapter" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "${#build_id}" -eq 40 ] || die "adapter Build-ID is not SHA1"
    replace_ascii_exact "$provider" "$RAW_ADAPTER_SHA" "$adapter_sha" 2
    replace_ascii_exact "$provider" "$RAW_ADAPTER_BUILD_ID" "$build_id" 2
    replace_ascii_exact "$provider" "$RAW_RUNTIME_SHA" "$RUNTIME_SHA" 2
    provider_sha=$(sha256_file "$provider")
    replace_ascii_exact "$child" "$RAW_PROVIDER_SHA" "$provider_sha" 1
    replace_ascii_exact "$child" "$RAW_ROUTE_NATIVE_LOADER_SHA" "$native_loader_sha" 1
    replace_ascii_exact "$child" "$RAW_ROUTE_NATIVE_LOADER_BUILD_ID" "$native_loader_build_id" 1
    child_sha=$(sha256_file "$child")
    replace_ascii_exact "$appspawn" "$RAW_CHILD_SHA" "$child_sha" 3
    appspawn_sha=$(sha256_file "$appspawn")

    "$NM" -D -C "$adapter" > "$candidate/adapter-symbols.txt"
    symbols="$candidate/adapter-symbols.txt"
    rg -q 'scheduleAcceptWantDone' "$symbols" || die "adapter lacks scheduleAcceptWantDone symbol"
    rg -q 'ScheduleAcceptWant' "$symbols" || die "adapter lacks ScheduleAcceptWant symbol"
    rg -q 'nativeOpenForegroundTransition' "$symbols" || die "adapter lacks the Fn03 foreground gate JNI"
    rg -q 'fn03_on_app_content_present' "$symbols" || die "adapter lacks the Fn04 present receipt hook"
    ! rg -q 'std::__n1' "$symbols" || die "adapter leaked the SDK std::__n1 ABI"
    rg -a -q 'ScheduleAcceptWantDone' "$adapter" || die "adapter lacks AcceptWantDone call-site marker"
    rg -a -q 'CreateAndConnectSpecificSession' "$adapter" || die "adapter lacks the OH 6.1 SceneBoard session protocol"
    rg -a -q 'FN03_A10_TYPED_RECEIPT_V1' "$adapter" || die "adapter lacks the Fn03/Fn04 first-frame receipt"
    chmod 0444 "$adapter" "$provider" "$child" "$runtime_jar" "$pthread_bridge" \
        "$native_loader" "$libandroid" "$mediandk" "$signal_box" \
        "$patched_libmain" "$patched_libil2cpp" "$patched_libtuanjie"
    chmod 0555 "$appspawn"

    {
        printf 'CANDIDATE_ID=%s\n' "$candidate_id"
        printf 'ADAPTER_SHA=%s\n' "$adapter_sha"
        printf 'ADAPTER_BUILD_ID=%s\n' "$build_id"
        printf 'PROVIDER_SHA=%s\n' "$provider_sha"
        printf 'CHILD_SHA=%s\n' "$child_sha"
        printf 'APPSPAWN_SHA=%s\n' "$appspawn_sha"
        printf 'RUNTIME_SHA=%s\n' "$RUNTIME_SHA"
        printf 'RUNTIME_JAR_SHA=%s\n' "$runtime_jar_sha"
        printf 'PTHREAD_BRIDGE_SHA=%s\n' "$pthread_bridge_sha"
        printf 'PTHREAD_BRIDGE_BUILD_ID=%s\n' "$pthread_bridge_build_id"
        printf 'NATIVE_LOADER_SHA=%s\n' "$native_loader_sha"
        printf 'NATIVE_LOADER_BUILD_ID=%s\n' "$native_loader_build_id"
        printf 'LIBANDROID_SHA=%s\n' "$libandroid_sha"
        printf 'MEDIANDK_SHA=%s\n' "$mediandk_sha"
        printf 'MEDIANDK_BUILD_ID=%s\n' "$mediandk_build_id"
        printf 'SIGNAL_BOX_SHA=%s\n' "$signal_box_sha"
        printf 'SIGNAL_BOX_BUILD_ID=%s\n' "$signal_box_build_id"
        printf 'PATCHED_LIBMAIN_SHA=%s\n' "$patched_libmain_sha"
        printf 'PATCHED_LIBIL2CPP_SHA=%s\n' "$patched_libil2cpp_sha"
        printf 'PATCHED_LIBTUANJIE_SHA=%s\n' "$patched_libtuanjie_sha"
        printf 'TUANJIE_CORE_RESOLVER=%s\n' eglGetProcAddress
        printf 'TUANJIE_CORE_GETPROC_FILE_OFFSET=%s\n' \
            "$TUANJIE_CORE_GETPROC_FILE_OFFSET"
        printf 'TUANJIE_CORE_GETPROC_PATCH_HEX=%s\n' \
            "$TUANJIE_CORE_GETPROC_EGL_HEX"
        printf 'RAW_LIBMAIN_SHA=%s\n' "$ZIGZAG_LIBMAIN_RAW_SHA"
        printf 'RAW_LIBIL2CPP_SHA=%s\n' "$ZIGZAG_LIBIL2CPP_RAW_SHA"
        printf 'RAW_LIBTUANJIE_SHA=%s\n' "$ZIGZAG_LIBTUANJIE_RAW_SHA"
        printf 'ZIGZAG_APK_SHA=%s\n' "$ZIGZAG_SHA"
        printf 'ZIGZAG_CONTROL_HAP_SHA=%s\n' "$ZIGZAG_CONTROL_HAP_SHA"
        printf 'ANDROID_TUANJIE_REFERENCE_SHA=%s\n' "$ANDROID_TUANJIE_REFERENCE_SHA"
        printf 'ANDROID_TUANJIE_BUILD_ID=%s\n' "$ANDROID_TUANJIE_BUILD_ID"
        printf 'OH_TUANJIE_REFERENCE_SHA=%s\n' "$OH_TUANJIE_REFERENCE_SHA"
        printf 'OH_TUANJIE_BUILD_ID=%s\n' "$OH_TUANJIE_BUILD_ID"
        printf 'SKIA_COMMIT=%s\n' "d26e5772d036c6ffe58e6983c79f78bc0b26231f"
        printf 'RESOURCE_COMMIT=%s\n' "6ddc6e6c7437a4cbe61a1e4dc8de90751e295fb6"
        printf 'WINDOW_MANAGER_COMMIT=%s\n' "$WINDOW_MANAGER_COMMIT"
        printf 'MOCK_SESSION_IDL_SHA=%s\n' "$MOCK_SESSION_IDL_SHA"
        printf 'MOCK_SESSION_HEADER_SHA=%s\n' "$MOCK_SESSION_HEADER_SHA"
    } > "$candidate/manifest.env"
    printf '%s\n' "$candidate" > "$CANDIDATES_ROOT/current"

    require_hash "$RAW_ADAPTER_SHA" "$RAW_PR03/android/lib64/liboh_adapter_bridge.so"
    require_hash "$RAW_PROVIDER_SHA" "$RAW_PR03/route/libwestlake_android_runtime_provider.so"
    require_hash "$RAW_CHILD_SHA" "$RAW_PR03/runtime/libwestlake_android_child.z.so"
    require_hash "$RAW_APPSPAWN_SHA" "$RAW_PR03/runtime/appspawn-x"
    step "candidate closure ready"
    printf 'candidate=%s\nadapter=%s\nprovider=%s\nchild=%s\nappspawn-x=%s\nruntime=%s\nruntime-jar=%s\npthread-bridge=%s\nnative-loader=%s\nlibandroid=%s\nmediandk=%s\nsignal-box=%s\npatched-libmain=%s\npatched-libil2cpp=%s\npatched-libtuanjie=%s\n' \
        "$candidate" "$adapter_sha" "$provider_sha" "$child_sha" "$appspawn_sha" \
        "$RUNTIME_SHA" "$runtime_jar_sha" "$pthread_bridge_sha" "$native_loader_sha" \
        "$libandroid_sha" "$mediandk_sha" "$signal_box_sha" "$patched_libmain_sha" \
        "$patched_libil2cpp_sha" "$patched_libtuanjie_sha"
}

build_runtime_candidate()
{
    local requested=${1:-} base candidate_id candidate runtime_jar_sha manifest_tmp
    base=$(resolve_candidate "$requested")
    candidate_id="strict-runtime-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    candidate="$CANDIDATES_ROOT/$candidate_id"
    mkdir -p "$candidate/files" "$candidate/build/runtime-jar" \
        "$candidate/build/signal-abi" "$candidate/reverse-analysis"

    # Runtime-only experiments must not rebuild or drift the accepted native
    # closure. Copy it byte-for-byte and replace only the Java runtime jar.
    cp -p "$base/files/"* "$candidate/files/"
    cp -p "$base/build/signal-abi/layout.env" \
        "$candidate/build/signal-abi/layout.env"
    cp -p "$base/reverse-analysis/twin-build-ids.env" \
        "$base/reverse-analysis/adapter-gap-seed.txt" \
        "$base/reverse-analysis/oh-native-contract.txt" \
        "$candidate/reverse-analysis/"
    mv "$candidate/files/oh-adapter-runtime.jar" \
        "$candidate/build/base-oh-adapter-runtime.jar"
    build_runtime_jar "$candidate/files/oh-adapter-runtime.jar" \
        "$candidate/build/runtime-jar"
    runtime_jar_sha=$(sha256_file "$candidate/files/oh-adapter-runtime.jar")
    chmod 0444 "$candidate/files/oh-adapter-runtime.jar"

    manifest_tmp=$(mktemp "$candidate/.manifest.XXXXXX")
    sed \
        -e "s/^CANDIDATE_ID=.*/CANDIDATE_ID=$candidate_id/" \
        -e "s/^RUNTIME_JAR_SHA=.*/RUNTIME_JAR_SHA=$runtime_jar_sha/" \
        "$base/manifest.env" > "$manifest_tmp"
    mv "$manifest_tmp" "$candidate/manifest.env"
    verify_candidate "$candidate"
    printf '%s\n' "$candidate" > "$CANDIDATES_ROOT/current"
    step "runtime-only candidate ready"
    printf 'candidate=%s\nbase=%s\nruntime-jar=%s\n' \
        "$candidate" "$base" "$runtime_jar_sha"
}

build_input_classname_candidate()
{
    local requested=${1:-} base candidate_id candidate libandroid
    local base_runtime_sha base_libandroid_sha runtime_sha libandroid_sha
    local base_provider_sha provider_sha base_child_sha child_sha
    local base_appspawn_sha appspawn_sha manifest_tmp slash_before dotted_before
    base=$(resolve_candidate "$requested")
    base_runtime_sha=$(manifest_value "$base/manifest.env" RUNTIME_SHA)
    base_libandroid_sha=$(manifest_value "$base/manifest.env" LIBANDROID_SHA)
    [ "$base_runtime_sha" = "$RUNTIME_SHA" ] \
        && [ "$base_libandroid_sha" = "$RUNTIME_SHA" ] \
        || die "input-classname base must use the pinned unmodified runtime pair"
    base_provider_sha=$(manifest_value "$base/manifest.env" PROVIDER_SHA)
    base_child_sha=$(manifest_value "$base/manifest.env" CHILD_SHA)
    base_appspawn_sha=$(manifest_value "$base/manifest.env" APPSPAWN_SHA)

    candidate_id="strict-input-classname-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    candidate="$CANDIDATES_ROOT/$candidate_id"
    mkdir -p "$candidate/files" "$candidate/build/signal-abi" \
        "$candidate/reverse-analysis"

    # Preserve the complete C9 closure and change only the equivalent class
    # name literals in the duplicated Android runtime image. The historical
    # accepted board binary spells the final character as X, so its non-BCP
    # loader and FindClass fallback can never resolve AppSchedulerBridge.
    # libandroid.so is the same image mounted under a second name; use the one
    # corrected file for both targets during deployment.
    cp -p "$base/files/"* "$candidate/files/"
    cp -p "$base/build/signal-abi/layout.env" \
        "$candidate/build/signal-abi/layout.env"
    cp -p "$base/reverse-analysis/twin-build-ids.env" \
        "$base/reverse-analysis/adapter-gap-seed.txt" \
        "$base/reverse-analysis/oh-native-contract.txt" \
        "$candidate/reverse-analysis/"
    libandroid="$candidate/files/libandroid.so"
    chmod u+w "$libandroid"
    slash_before=$(LC_ALL=C grep -a -o 'adapter/activity/AppSchedulerBridgX' \
        "$libandroid" | wc -l | trim)
    dotted_before=$(LC_ALL=C grep -a -o 'adapter.activity.AppSchedulerBridgX' \
        "$libandroid" | wc -l | trim)
    [ "$slash_before" = 1 ] && [ "$dotted_before" = 2 ] \
        || die "unexpected AppSchedulerBridgX literal counts: slash=$slash_before dotted=$dotted_before"
    perl -0pi -e \
        's/adapter\/activity\/AppSchedulerBridgX/adapter\/activity\/AppSchedulerBridge/g; s/adapter\.activity\.AppSchedulerBridgX/adapter.activity.AppSchedulerBridge/g' \
        "$libandroid"
    [ "$(LC_ALL=C grep -a -o 'AppSchedulerBridgX' "$libandroid" \
        | wc -l | trim)" = 0 ] \
        || die "input-classname patch left a BridgX literal"
    [ "$(LC_ALL=C grep -a -o 'adapter/activity/AppSchedulerBridge' \
        "$libandroid" | wc -l | trim)" = 1 ] \
        || die "input-classname slash literal postflight failed"
    [ "$(LC_ALL=C grep -a -o 'adapter.activity.AppSchedulerBridge' \
        "$libandroid" | wc -l | trim)" = 2 ] \
        || die "input-classname dotted literal postflight failed"
    libandroid_sha=$(sha256_file "$libandroid")
    runtime_sha=$libandroid_sha
    chmod 0444 "$libandroid"

    # The runtime provider pins the runtime hash, the child pins the provider,
    # and appspawn-x pins the child. Repin only those integrity literals so the
    # one behavioral change remains the class-name correction above.
    chmod u+w "$candidate/files/libwestlake_android_runtime_provider.so" \
        "$candidate/files/libwestlake_android_child.z.so" \
        "$candidate/files/appspawn-x"
    replace_ascii_exact "$candidate/files/libwestlake_android_runtime_provider.so" \
        "$base_runtime_sha" "$runtime_sha" 2
    provider_sha=$(sha256_file \
        "$candidate/files/libwestlake_android_runtime_provider.so")
    replace_ascii_exact "$candidate/files/libwestlake_android_child.z.so" \
        "$base_provider_sha" "$provider_sha" 1
    child_sha=$(sha256_file "$candidate/files/libwestlake_android_child.z.so")
    replace_ascii_exact "$candidate/files/appspawn-x" \
        "$base_child_sha" "$child_sha" 3
    appspawn_sha=$(sha256_file "$candidate/files/appspawn-x")
    chmod 0444 "$candidate/files/libwestlake_android_runtime_provider.so"
    chmod 0555 "$candidate/files/libwestlake_android_child.z.so" \
        "$candidate/files/appspawn-x"

    manifest_tmp=$(mktemp "$candidate/.manifest.XXXXXX")
    sed \
        -e "s/^CANDIDATE_ID=.*/CANDIDATE_ID=$candidate_id/" \
        -e "s/^PROVIDER_SHA=.*/PROVIDER_SHA=$provider_sha/" \
        -e "s/^CHILD_SHA=.*/CHILD_SHA=$child_sha/" \
        -e "s/^APPSPAWN_SHA=.*/APPSPAWN_SHA=$appspawn_sha/" \
        -e "s/^RUNTIME_SHA=.*/RUNTIME_SHA=$runtime_sha/" \
        -e "s/^LIBANDROID_SHA=.*/LIBANDROID_SHA=$libandroid_sha/" \
        "$base/manifest.env" > "$manifest_tmp"
    {
        printf 'RUNTIME_CLASSNAME_FIX=1\n'
        printf 'RUNTIME_BASE_SHA=%s\n' "$base_runtime_sha"
        printf 'LIBANDROID_CLASSNAME_FIX=1\n'
        printf 'LIBANDROID_BASE_SHA=%s\n' "$base_libandroid_sha"
    } >> "$manifest_tmp"
    mv "$manifest_tmp" "$candidate/manifest.env"
    verify_candidate "$candidate"
    printf '%s\n' "$candidate" > "$CANDIDATES_ROOT/current"
    step "input-classname candidate ready"
    printf 'candidate=%s\nbase=%s\nruntime=%s\nprovider=%s\nchild=%s\nappspawn=%s\n' \
        "$candidate" "$base" "$runtime_sha" "$provider_sha" \
        "$child_sha" "$appspawn_sha"
}

manifest_value()
{
    local manifest=$1 key=$2
    sed -n "s/^${key}=//p" "$manifest" | head -n 1
}

resolve_candidate()
{
    local requested=${1:-} pointer candidate
    if [ -z "$requested" ]; then
        pointer="$CANDIDATES_ROOT/current"
        [ -f "$pointer" ] || die "no current candidate; run build first"
        IFS= read -r requested < "$pointer"
    fi
    [ -d "$requested" ] || die "candidate directory missing: $requested"
    candidate="$(cd "$requested" && pwd -P)"
    case "$candidate" in
        "$CANDIDATES_ROOT"/*|"$PERSISTED_ROOT"/*) ;;
        *) die "candidate must be under $CANDIDATES_ROOT or $PERSISTED_ROOT" ;;
    esac
    verify_candidate "$candidate"
    printf '%s\n' "$candidate"
}

verify_candidate()
{
    local candidate=$1 manifest files runtime_file audio_plugin_sha audio_plugin_path audio_plugin_policy audio_plugin_needed audio_ready_path adapter_sha adapter_build_id actual_build_id provider_sha child_sha appspawn_sha runtime_sha runtime_jar_sha pthread_bridge_sha pthread_bridge_build_id actual_pthread_bridge_build_id native_loader_sha native_loader_build_id actual_native_loader_build_id libandroid_sha mediandk_sha mediandk_build_id actual_mediandk_build_id signal_box_sha signal_box_build_id actual_signal_box_build_id patched_libmain_sha patched_libil2cpp_sha patched_libtuanjie_sha property_symbol signal_symbol dynamic symbols
    manifest="$candidate/manifest.env"
    files="$candidate/files"
    [ -f "$manifest" ] || die "candidate manifest missing: $manifest"
    adapter_sha=$(manifest_value "$manifest" ADAPTER_SHA)
    adapter_build_id=$(manifest_value "$manifest" ADAPTER_BUILD_ID)
    provider_sha=$(manifest_value "$manifest" PROVIDER_SHA)
    child_sha=$(manifest_value "$manifest" CHILD_SHA)
    appspawn_sha=$(manifest_value "$manifest" APPSPAWN_SHA)
    runtime_sha=$(manifest_value "$manifest" RUNTIME_SHA)
    runtime_jar_sha=$(manifest_value "$manifest" RUNTIME_JAR_SHA)
    pthread_bridge_sha=$(manifest_value "$manifest" PTHREAD_BRIDGE_SHA)
    pthread_bridge_build_id=$(manifest_value "$manifest" PTHREAD_BRIDGE_BUILD_ID)
    native_loader_sha=$(manifest_value "$manifest" NATIVE_LOADER_SHA)
    native_loader_build_id=$(manifest_value "$manifest" NATIVE_LOADER_BUILD_ID)
    libandroid_sha=$(manifest_value "$manifest" LIBANDROID_SHA)
    mediandk_sha=$(manifest_value "$manifest" MEDIANDK_SHA)
    mediandk_build_id=$(manifest_value "$manifest" MEDIANDK_BUILD_ID)
    signal_box_sha=$(manifest_value "$manifest" SIGNAL_BOX_SHA)
    signal_box_build_id=$(manifest_value "$manifest" SIGNAL_BOX_BUILD_ID)
    patched_libmain_sha=$(manifest_value "$manifest" PATCHED_LIBMAIN_SHA)
    patched_libil2cpp_sha=$(manifest_value "$manifest" PATCHED_LIBIL2CPP_SHA)
    patched_libtuanjie_sha=$(manifest_value "$manifest" PATCHED_LIBTUANJIE_SHA)
    runtime_file="$files/libandroid.so"
    if [ "$(manifest_value "$manifest" RUNTIME_ALIAS_SPLIT)" = 1 ]; then
        runtime_file="$files/liboh_android_runtime.so"
        [ "$runtime_sha" != "$libandroid_sha" ] \
            || die "split runtime candidate did not separate its alias"
        [ "$(manifest_value "$manifest" RUNTIME_ALIAS_BASE_SHA)" = "$libandroid_sha" ] \
            || die "split runtime candidate has the wrong alias base"
    fi
    if [ "$(manifest_value "$manifest" RUNTIME_CLASSNAME_FIX)" = 1 ]; then
        [ "$(manifest_value "$manifest" RUNTIME_BASE_SHA)" = "$RUNTIME_SHA" ] \
            || die "input-classname candidate has the wrong runtime base"
        if [ "$(manifest_value "$manifest" RUNTIME_ALIAS_SPLIT)" != 1 ]; then
            [ "$runtime_sha" = "$libandroid_sha" ] \
                || die "input-classname runtime/libandroid pair drifted"
        fi
    else
        [ "$(manifest_value "$manifest" RUNTIME_SHA)" = "$RUNTIME_SHA" ] \
            || die "candidate runtime pin drifted"
    fi
    [ "$(manifest_value "$manifest" WINDOW_MANAGER_COMMIT)" = "$WINDOW_MANAGER_COMMIT" ] || die "candidate window-manager source pin drifted"
    [ "$(manifest_value "$manifest" MOCK_SESSION_IDL_SHA)" = "$MOCK_SESSION_IDL_SHA" ] || die "candidate MockSessionManager IDL pin drifted"
    [ "$(manifest_value "$manifest" MOCK_SESSION_HEADER_SHA)" = "$MOCK_SESSION_HEADER_SHA" ] || die "candidate MockSessionManager header pin drifted"
    require_hash "$adapter_sha" "$files/liboh_adapter_bridge.so"
    require_hash "$provider_sha" "$files/libwestlake_android_runtime_provider.so"
    require_hash "$child_sha" "$files/libwestlake_android_child.z.so"
    require_hash "$appspawn_sha" "$files/appspawn-x"
    require_hash "$runtime_sha" "$runtime_file"
    audio_plugin_sha=$(manifest_value "$manifest" RUNTIME_AUDIO_PLUGIN_SHA)
    if [ -n "$audio_plugin_sha" ]; then
        audio_plugin_path=$(manifest_value "$manifest" RUNTIME_AUDIO_PLUGIN_PATH)
        case "$audio_plugin_path" in
            /data/boat-attack-audio-*/libwestlake_audio_caps.so) ;;
            *) die "unsafe runtime audio plugin path: $audio_plugin_path" ;;
        esac
        audio_ready_path=$(manifest_value "$manifest" RUNTIME_AUDIO_READY_PATH)
        case "$audio_ready_path" in
            /data/boat-attack-audio-*/register.env) ;;
            *) die "unsafe runtime audio readiness path: $audio_ready_path" ;;
        esac
        require_hash "$audio_plugin_sha" "$files/libwestlake_audio_caps.so"
        audio_plugin_policy=$(manifest_value "$manifest" RUNTIME_AUDIO_PLUGIN_POLICY)
        audio_plugin_needed=$("$READELF" -dW "$files/libwestlake_audio_caps.so" \
            | awk -F'[][]' '/Shared library:/ {print $2}' | paste -sd, -)
        case "$audio_plugin_policy" in
            '') [ "$audio_plugin_needed" = libc.so ] ;;
            OH_AUDIO_BACKEND)
                [ "$audio_plugin_needed" = "/system/lib64/ndk/libohaudio.so,libc.so" ] ;;
            *) die "unknown runtime audio plugin policy: $audio_plugin_policy" ;;
        esac || die "runtime audio plugin dependency closure drifted"
    fi
    require_hash "$runtime_jar_sha" "$files/oh-adapter-runtime.jar"
    require_hash "$pthread_bridge_sha" "$files/libwestlake_bionic_pthread_bridge.so"
    require_hash "$native_loader_sha" "$files/libnativeloader.so"
    require_hash "$libandroid_sha" "$files/libandroid.so"
    require_hash "$mediandk_sha" "$files/libmediandk.so"
    require_hash "$signal_box_sha" "$files/libwestlake_bionic_signal_box.so"
    require_hash "$patched_libmain_sha" "$files/libmain.so"
    require_hash "$patched_libil2cpp_sha" "$files/libil2cpp.so"
    require_hash "$patched_libtuanjie_sha" "$files/libtuanjie.so"
    if [ "$(manifest_value "$manifest" LIBANDROID_CLASSNAME_FIX)" = 1 ]; then
        [ "$(manifest_value "$manifest" LIBANDROID_BASE_SHA)" = "$RUNTIME_SHA" ] \
            || die "input-classname candidate has the wrong libandroid base"
        [ "$libandroid_sha" != "$RUNTIME_SHA" ] \
            || die "input-classname candidate did not change libandroid"
        [ "$(LC_ALL=C grep -a -o 'AppSchedulerBridgX' \
            "$files/libandroid.so" | wc -l | trim)" = 0 ] \
            || die "input-classname candidate retains BridgX"
        [ "$(LC_ALL=C grep -a -o 'adapter/activity/AppSchedulerBridge' \
            "$files/libandroid.so" | wc -l | trim)" = 1 ] \
            || die "input-classname candidate slash literal drifted"
        [ "$(LC_ALL=C grep -a -o 'adapter.activity.AppSchedulerBridge' \
            "$files/libandroid.so" | wc -l | trim)" = 2 ] \
            || die "input-classname candidate dotted literal drifted"
    else
        [ "$libandroid_sha" = "$RUNTIME_SHA" ] \
            || die "candidate Unity Android provider is not the pinned board runtime"
    fi
    verify_unity_android_provider "$files/libandroid.so"
    [ "$(manifest_value "$manifest" RAW_LIBMAIN_SHA)" = "$ZIGZAG_LIBMAIN_RAW_SHA" ] \
        || die "candidate raw libmain pin drifted"
    [ "$(manifest_value "$manifest" RAW_LIBIL2CPP_SHA)" = "$ZIGZAG_LIBIL2CPP_RAW_SHA" ] \
        || die "candidate raw libil2cpp pin drifted"
    [ "$(manifest_value "$manifest" RAW_LIBTUANJIE_SHA)" = "$ZIGZAG_LIBTUANJIE_RAW_SHA" ] \
        || die "candidate raw libtuanjie pin drifted"
    [ "$(manifest_value "$manifest" TUANJIE_CORE_RESOLVER)" = eglGetProcAddress ] \
        || die "candidate Tuanjie core resolver route is not pinned"
    [ "$(manifest_value "$manifest" TUANJIE_CORE_GETPROC_FILE_OFFSET)" = \
        "$TUANJIE_CORE_GETPROC_FILE_OFFSET" ] \
        || die "candidate Tuanjie core resolver offset drifted"
    [ "$(manifest_value "$manifest" TUANJIE_CORE_GETPROC_PATCH_HEX)" = \
        "$TUANJIE_CORE_GETPROC_EGL_HEX" ] \
        || die "candidate Tuanjie core resolver opcode drifted"
    [ "$(binary_hex_at "$files/libtuanjie.so" \
        "$TUANJIE_CORE_GETPROC_FILE_OFFSET" 4)" = "$TUANJIE_CORE_GETPROC_EGL_HEX" ] \
        || die "candidate Tuanjie core resolver patch is absent"
    [ "$(manifest_value "$manifest" ZIGZAG_CONTROL_HAP_SHA)" = "$ZIGZAG_CONTROL_HAP_SHA" ] \
        || die "candidate ZigZag HAP control pin drifted"
    [ "$(manifest_value "$manifest" ANDROID_TUANJIE_REFERENCE_SHA)" = \
        "$ANDROID_TUANJIE_REFERENCE_SHA" ] \
        || die "candidate Android Tuanjie reference pin drifted"
    [ "$(manifest_value "$manifest" ANDROID_TUANJIE_BUILD_ID)" = \
        "$ANDROID_TUANJIE_BUILD_ID" ] \
        || die "candidate Android Tuanjie Build-ID pin drifted"
    [ "$(manifest_value "$manifest" OH_TUANJIE_REFERENCE_SHA)" = \
        "$OH_TUANJIE_REFERENCE_SHA" ] \
        || die "candidate OH Tuanjie reference pin drifted"
    [ "$(manifest_value "$manifest" OH_TUANJIE_BUILD_ID)" = \
        "$OH_TUANJIE_BUILD_ID" ] \
        || die "candidate OH Tuanjie Build-ID pin drifted"
    rg -q "^APK_TUANJIE_BUILD_ID=${ANDROID_TUANJIE_BUILD_ID}$" \
        "$candidate/reverse-analysis/twin-build-ids.env" \
        || die "candidate APK/reference twin proof is missing"
    rg -q "^HAP_TUANJIE_BUILD_ID=${OH_TUANJIE_BUILD_ID}$" \
        "$candidate/reverse-analysis/twin-build-ids.env" \
        || die "candidate HAP/reference twin proof is missing"
    rg -q '^ANDROID_SIGACTION_SIZE=32$' "$candidate/build/signal-abi/layout.env" \
        || die "candidate lacks Android signal ABI proof"
    rg -q '^OH_SIGACTION_SIZE=152$' "$candidate/build/signal-abi/layout.env" \
        || die "candidate lacks OH signal ABI proof"
    rg -q '^ANativeWindow_fromSurface$' "$candidate/reverse-analysis/adapter-gap-seed.txt" \
        || die "candidate lacks Android/OH adapter gap evidence"
    rg -q '^OH_NativeWindow_NativeWindowHandleOpt$' \
        "$candidate/reverse-analysis/oh-native-contract.txt" \
        || die "candidate lacks OH native-window positive contract"
    [ "$("$READELF" -dW "$files/libmain.so" \
        | grep -Fc 'Shared library: [libwestlake_bionic_pthread_bridge.so]')" = 1 ] \
        || die "candidate libmain lacks its direct Bionic bridge edge"
    [ "$("$READELF" -dW "$files/libil2cpp.so" \
        | grep -Fc 'Shared library: [libwestlake_bionic_pthread_bridge.so]')" = 1 ] \
        || die "candidate libil2cpp lacks its direct Bionic bridge edge"
    [ "$("$READELF" -dW "$files/libil2cpp.so" \
        | grep -Fc 'Shared library: [libwestlake_bionic_signal_box.so]')" = 1 ] \
        || die "candidate libil2cpp lacks its direct signal-box edge"
    [ "$("$READELF" -dW "$files/libtuanjie.so" \
        | grep -Fc 'Shared library: [libwestlake_bionic_signal_box.so]')" = 1 ] \
        || die "candidate libtuanjie lacks its direct signal-box edge"
    [ "$("$READELF" -dW "$files/libtuanjie.so" \
        | awk -F'[][]' '/Shared library:/ {print $2; exit}')" = \
        libwestlake_bionic_signal_box.so ] \
        || die "candidate libtuanjie does not search the signal box first"
    [ "$(unzip -p "$files/oh-adapter-runtime.jar" classes.dex \
        | LC_ALL=C grep -a -o 'extractNativeLibs' | wc -l | trim)" = 2 ] \
        || die "candidate runtime jar lacks the two extractNativeLibs projections"
    [ "$(unzip -p "$files/oh-adapter-runtime.jar" classes.dex \
        | LC_ALL=C grep -a -o '\[ZZ-PM\] projected getApplicationInfo' \
        | wc -l | trim)" = 1 ] \
        || die "candidate runtime jar lacks package-manager projection fix"
    [ "$(unzip -p "$files/oh-adapter-runtime.jar" classes.dex \
        | LC_ALL=C grep -a -o '\[ZZ-PM\] extracted native path selected; apk zip path disabled' \
        | wc -l | trim)" = 1 ] \
        || die "candidate runtime jar lacks extracted-native-path ABI fix"
    [ "$(unzip -p "$files/oh-adapter-runtime.jar" classes.dex \
        | LC_ALL=C grep -a -o 'ZZ-PM:apk-zip-disabled' | wc -l | trim)" = 1 ] \
        || die "candidate runtime jar lacks ABI selector trace marker"
    actual_build_id=$("$READELF" --notes --wide "$files/liboh_adapter_bridge.so" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "$actual_build_id" = "$adapter_build_id" ] || die "adapter Build-ID does not match manifest"
    actual_pthread_bridge_build_id=$("$READELF" --notes --wide "$files/libwestlake_bionic_pthread_bridge.so" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "$actual_pthread_bridge_build_id" = "$pthread_bridge_build_id" ] \
        || die "pthread bridge Build-ID does not match manifest"
    "$NM" -D --defined-only "$files/libwestlake_bionic_pthread_bridge.so" \
        | rg -q ' __sF@@LIBC$' || die "candidate pthread bridge lacks __sF@@LIBC"
    for property_symbol in __system_property_find __system_property_get __system_property_read; do
        "$NM" -D --defined-only "$files/libwestlake_bionic_pthread_bridge.so" \
            | rg -q " ${property_symbol}@@LIBC$" \
            || die "candidate pthread bridge lacks ${property_symbol}@@LIBC"
    done
    ! "$NM" -D --defined-only "$files/libwestlake_bionic_pthread_bridge.so" \
        | rg -q ' sig(action|emptyset|fillset|addset|delset|ismember|procmask)@@LIBC$' \
        || die "candidate pthread bridge leaks a Bionic signal ABI"
    actual_native_loader_build_id=$("$READELF" --notes --wide "$files/libnativeloader.so" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "$actual_native_loader_build_id" = "$native_loader_build_id" ] \
        || die "native loader Build-ID does not match manifest"
    [ "$("$READELF" -dW "$files/libnativeloader.so" \
        | awk -F'[][]' '/Shared library:/ {print $2}' | paste -sd, -)" = \
        "libapp_native_loader.so,libc++.so,libc.so" ] \
        || die "candidate native loader NEEDED closure drifted"
    strings "$files/libnativeloader.so" | grep -Fxq '/system/lib64/platformsdk' \
        || die "candidate native loader lacks the platform SDK path"
    actual_mediandk_build_id=$("$READELF" --notes --wide "$files/libmediandk.so" 2>/dev/null | awk '/Build ID:/ {print $3; exit}')
    [ "$actual_mediandk_build_id" = "$mediandk_build_id" ] \
        || die "presence-only media Build-ID does not match manifest"
    dynamic=$("$READELF" -dW "$files/libmediandk.so")
    printf '%s\n' "$dynamic" | grep -Fq 'Library soname: [libmediandk.so]' \
        || die "candidate media provider SONAME drifted"
    [ "$(printf '%s\n' "$dynamic" | awk '/Shared library:/ {count++} END {print count + 0}')" = 0 ] \
        || die "candidate media provider gained a transitive dependency"
    "$NM" -D --defined-only "$files/libmediandk.so" \
        | rg -q ' westlake_mediandk_presence_provenance$' \
        || die "candidate media provider lacks its provenance marker"
    actual_signal_box_build_id=$("$READELF" --notes --wide \
        "$files/libwestlake_bionic_signal_box.so" 2>/dev/null \
        | awk '/Build ID:/ {print $3; exit}')
    [ "$actual_signal_box_build_id" = "$signal_box_build_id" ] \
        || die "guest signal-box Build-ID does not match manifest"
    dynamic=$("$READELF" -dW "$files/libwestlake_bionic_signal_box.so")
    [ "$(printf '%s\n' "$dynamic" \
        | awk -F'[][]' '/Shared library:/ {print $2}' | paste -sd, -)" = libc.so ] \
        || die "candidate signal-box NEEDED closure drifted"
    symbols="$candidate/signal-box-symbols.txt"
    "$NM" -D --defined-only "$files/libwestlake_bionic_signal_box.so" > "$symbols"
    for signal_symbol in signal sigaction sigemptyset sigfillset sigaddset sigdelset \
            sigismember sigprocmask pthread_sigmask sigsuspend sigaltstack; do
        rg -q " westlake_bionic_${signal_symbol}@@LIBC$" "$symbols" \
            || die "candidate signal box lacks westlake_bionic_${signal_symbol}@@LIBC"
    done
    symbols="$candidate/tuanjie-undefined.txt"
    "$NM" -D --undefined-only "$files/libtuanjie.so" > "$symbols"
    for signal_symbol in sigaction sigaltstack sigemptyset; do
        rg -q " westlake_bionic_${signal_symbol}@LIBC$" "$symbols" \
            || die "candidate libtuanjie lacks private ${signal_symbol} import"
    done
    ! rg -q ' (signal|sig(action|emptyset|fillset|addset|delset|ismember|procmask|suspend|altstack)|pthread_sigmask)@LIBC$' "$symbols" \
        || die "candidate libtuanjie retains collision-prone signal imports"
    symbols="$candidate/il2cpp-undefined.txt"
    "$NM" -D --undefined-only "$files/libil2cpp.so" > "$symbols"
    for signal_symbol in signal sigaction sigemptyset sigfillset sigaddset sigdelset \
            pthread_sigmask sigsuspend sigaltstack; do
        rg -q " westlake_bionic_${signal_symbol}@LIBC$" "$symbols" \
            || die "candidate libil2cpp lacks private ${signal_symbol} import"
    done
    ! rg -q ' (signal|sig(action|emptyset|fillset|addset|delset|ismember|procmask|suspend|altstack)|pthread_sigmask)@LIBC$' "$symbols" \
        || die "candidate libil2cpp retains collision-prone signal imports"
    [ "$(LC_ALL=C grep -a -o "$adapter_sha" "$files/libwestlake_android_runtime_provider.so" | wc -l | trim)" = 2 ] || die "provider does not pin adapter twice"
    [ "$(LC_ALL=C grep -a -o "$adapter_build_id" "$files/libwestlake_android_runtime_provider.so" | wc -l | trim)" = 2 ] || die "provider does not pin adapter Build-ID twice"
    [ "$(LC_ALL=C grep -a -o "$(manifest_value "$manifest" RUNTIME_SHA)" \
        "$files/libwestlake_android_runtime_provider.so" | wc -l | trim)" = 2 ] \
        || die "provider does not pin candidate runtime twice"
    [ "$(LC_ALL=C grep -a -o "$provider_sha" "$files/libwestlake_android_child.z.so" | wc -l | trim)" = 1 ] || die "child does not pin provider"
    [ "$(LC_ALL=C grep -a -o "$native_loader_sha" "$files/libwestlake_android_child.z.so" | wc -l | trim)" = 1 ] \
        || die "child does not pin native loader SHA"
    [ "$(LC_ALL=C grep -a -o "$native_loader_build_id" "$files/libwestlake_android_child.z.so" | wc -l | trim)" = 1 ] \
        || die "child does not pin native loader Build-ID"
    [ "$(LC_ALL=C grep -a -o "$child_sha" "$files/appspawn-x" | wc -l | trim)" = 3 ] || die "appspawn-x does not pin child three times"
}

BOARD=""
CANDIDATE_CHANGED=0
H() { "$HDC_BIN" -t "$BOARD" "$@"; }
D() { H shell "$1" 2>&1 | tr -d '\r'; }
device_hash() { D "sha256sum '$1' 2>/dev/null" | awk 'NR == 1 {print $1}'; }

select_board()
{
    local requested=${1:-$BOARD_ONLY}
    case "$requested" in
        "$BOARD_ONLY") BOARD_LABEL=61ae ;;
        "$BOARD_8605") BOARD_LABEL=8605 ;;
        "$BOARD_5EA1") BOARD_LABEL=5ea1 ;;
        "5ea34a4500000000000000001123012c") BOARD_LABEL=5ea ;;
        "61b0657200000000000000000324012c") BOARD_LABEL=61b ;;
        "5cd1e3dd00000000000000000923012c") BOARD_LABEL=5cd ;;
        *) die "unsupported direct board: $requested" ;;
    esac
    "$HDC_BIN" list targets 2>/dev/null | tr -d '\r' | grep -qx "$requested" || die "requested board is not connected"
    BOARD=$requested
    [ "$(D 'param get const.ohos.fullname' | trim)" = "$ROM_ONLY" ] || die "board ROM is not $ROM_ONLY"
    [ "$(D 'uname -m' | trim)" = aarch64 ] || die "board is not aarch64"
    H target mount >/dev/null 2>&1 || true
}

device_stop_runtime()
{
    D "aa force-stop '$HELLO_BUNDLE' >/dev/null 2>&1 || true; aa force-stop '$ZIGZAG_BUNDLE' >/dev/null 2>&1 || true; begetctl stop_service appspawn-x >/dev/null 2>&1 || true; for pid in \$(pidof appspawn-x 2>/dev/null); do kill -9 \$pid 2>/dev/null || true; done; true" >/dev/null
    local attempt
    for attempt in $(seq 1 20); do
        [ -z "$(D 'pidof appspawn-x 2>/dev/null' | trim)" ] && return 0
        sleep 1
    done
    return 1
}

device_unmount_candidate_layers()
{
    if ! D "for pass in 1 2 3 4 5 6 7 8; do changed=0; for target in '$ADAPTER_TARGET' '$PROVIDER_TARGET' '$CHILD_TARGET' '$APPSPAWN_TARGET' '$RUNTIME_TARGET' '$RUNTIME_JAR_TARGET' '$PTHREAD_BRIDGE_TARGET' '$NATIVE_LOADER_TARGET' '$ROUTE_NATIVE_LOADER_TARGET' '$LIBANDROID_TARGET' '$ZIGZAG_LIBMAIN_TARGET' '$ZIGZAG_LIBIL2CPP_TARGET' '$ZIGZAG_LIBTUANJIE_TARGET' '$ZIGZAG_MEDIANDK_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET'; do if grep -F \" \$target \" /proc/self/mountinfo | grep -q '/zigzag-apk-lightup/'; then umount \"\$target\" || exit 31; changed=1; fi; done; [ \$changed = 0 ] && break; done; ! grep '/zigzag-apk-lightup/' /proc/self/mountinfo | grep -E ' ($ADAPTER_TARGET|$PROVIDER_TARGET|$CHILD_TARGET|$APPSPAWN_TARGET|$RUNTIME_TARGET|$RUNTIME_JAR_TARGET|$PTHREAD_BRIDGE_TARGET|$NATIVE_LOADER_TARGET|$ROUTE_NATIVE_LOADER_TARGET|$LIBANDROID_TARGET|$ZIGZAG_LIBMAIN_TARGET|$ZIGZAG_LIBIL2CPP_TARGET|$ZIGZAG_LIBTUANJIE_TARGET|$ZIGZAG_MEDIANDK_TARGET|$ZIGZAG_SIGNAL_BOX_TARGET) '" >/dev/null; then
        return 1
    fi
    if [ "$(device_hash "$ZIGZAG_MEDIANDK_TARGET")" = \
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" ]; then
        D "rm -f '$ZIGZAG_MEDIANDK_TARGET'" >/dev/null || return 1
    fi
    if [ "$(device_hash "$ZIGZAG_SIGNAL_BOX_TARGET")" = \
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" ]; then
        D "rm -f '$ZIGZAG_SIGNAL_BOX_TARGET'" >/dev/null || return 1
    fi
}

verify_pr03_backing()
{
    local adapter_back provider_back child_back appspawn_back runtime_back runtime_jar_back
    local pthread_bridge_back native_loader_back route_native_loader_back libandroid_back
    adapter_back=$(device_hash "$REMOTE_PR03/android/lib64/liboh_adapter_bridge.so")
    provider_back=$(device_hash "$REMOTE_PR03/route/libwestlake_android_runtime_provider.so")
    child_back=$(device_hash "$REMOTE_PR03/runtime/libwestlake_android_child.z.so")
    appspawn_back=$(device_hash "$REMOTE_PR03/runtime/appspawn-x")
    runtime_back=$(device_hash "$REMOTE_PR03/android/lib64/liboh_android_runtime.so")
    runtime_jar_back=$(device_hash "$REMOTE_PR03/android/framework/oh-adapter-runtime.jar")
    pthread_bridge_back=$(device_hash "$REMOTE_PR03/android/lib64/libwestlake_bionic_pthread_bridge.so")
    native_loader_back=$(device_hash "$REMOTE_PR03/android/lib64/libnativeloader.so")
    route_native_loader_back=$(device_hash "$REMOTE_PR03/route/libnativeloader.so")
    libandroid_back=$(device_hash "$REMOTE_PR03/android/lib64/libandroid.so")
    [ -n "$adapter_back" ] && [ "$(device_hash "$ADAPTER_TARGET")" = "$adapter_back" ] || return 1
    [ -n "$provider_back" ] && [ "$(device_hash "$PROVIDER_TARGET")" = "$provider_back" ] || return 1
    [ -n "$child_back" ] && [ "$(device_hash "$CHILD_TARGET")" = "$child_back" ] || return 1
    [ -n "$appspawn_back" ] && [ "$(device_hash "$APPSPAWN_TARGET")" = "$appspawn_back" ] || return 1
    [ "$runtime_back" = "$RUNTIME_SHA" ] && [ "$(device_hash "$RUNTIME_TARGET")" = "$runtime_back" ] || return 1
    [ -n "$runtime_jar_back" ] && [ "$(device_hash "$RUNTIME_JAR_TARGET")" = "$runtime_jar_back" ] || return 1
    [ -n "$pthread_bridge_back" ] && [ "$(device_hash "$PTHREAD_BRIDGE_TARGET")" = "$pthread_bridge_back" ] || return 1
    [ -n "$native_loader_back" ] && [ "$(device_hash "$NATIVE_LOADER_TARGET")" = "$native_loader_back" ] || return 1
    [ -n "$route_native_loader_back" ] && [ "$(device_hash "$ROUTE_NATIVE_LOADER_TARGET")" = "$route_native_loader_back" ] || return 1
    [ -n "$libandroid_back" ] && [ "$(device_hash "$LIBANDROID_TARGET")" = "$libandroid_back" ] || return 1
}

device_start_appspawn()
{
    local expected=$1 attempt pids count pid last="" stable=0
    D "begetctl start_service appspawn-x" >/dev/null
    for attempt in $(seq 1 40); do
        sleep 1
        pids=$(D 'pidof appspawn-x 2>/dev/null' | tr ' ' '\n' | sed '/^$/d' || true)
        count=$(printf '%s\n' "$pids" | sed '/^$/d' | wc -l | trim)
        pid=$(printf '%s\n' "$pids" | sed '/^$/d' | head -n 1)
        if [ "$count" = 1 ] && [ -n "$pid" ] && [ "$pid" = "$last" ] \
            && [ "$(device_hash "/proc/$pid/exe")" = "$expected" ]; then
            stable=$((stable + 1))
        else
            stable=0
        fi
        last=$pid
        [ "$stable" -ge 2 ] && break
    done
    [ "$stable" -ge 2 ] || return 1
    D "chmod 0660 /dev/unix/socket/AppSpawnX; chown 0:6005 /dev/unix/socket/AppSpawnX; chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX" >/dev/null
    [ "$(D "stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX" | trim)" = "660:0:6005:u:object_r:appspawn_socket:s0" ]
}

device_init_listener_ready()
{
    local flags socket_state
    flags=$(D 'cat /proc/net/unix' \
        | awk '$NF == "/dev/unix/socket/AppSpawnX" {print $4; exit}')
    socket_state=$(D "stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX 2>/dev/null" \
        | trim)
    [ "$flags" = 00010000 ] \
        && [ "$socket_state" = "660:0:6005:u:object_r:appspawn_socket:s0" ]
}

push_candidate()
{
    local candidate=$1 id remote files runtime_file audio_plugin_sha audio_plugin_path
    id=$(manifest_value "$candidate/manifest.env" CANDIDATE_ID)
    case "$id" in ''|*[!A-Za-z0-9._-]*) die "unsafe candidate id: $id" ;; esac
    remote="$REMOTE_ROOT/candidates/$id"
    files="$candidate/files"
    runtime_file="$files/libandroid.so"
    if [ "$(manifest_value "$candidate/manifest.env" RUNTIME_ALIAS_SPLIT)" = 1 ]; then
        runtime_file="$files/liboh_android_runtime.so"
    fi
    audio_plugin_sha=$(manifest_value "$candidate/manifest.env" RUNTIME_AUDIO_PLUGIN_SHA)
    if [ -n "$audio_plugin_sha" ]; then
        audio_plugin_path=$(manifest_value "$candidate/manifest.env" RUNTIME_AUDIO_PLUGIN_PATH)
        if [ "$(device_hash "$audio_plugin_path")" != "$audio_plugin_sha" ]; then
            [ -z "$(D "for maps in /proc/[0-9]*/maps; do grep -l '$audio_plugin_path' \"\$maps\" 2>/dev/null; done" | trim)" ] \
                || die "refusing to replace a mapped runtime audio plugin"
            D "mkdir -p '$(dirname "$audio_plugin_path")'" >/dev/null
            H file send "$files/libwestlake_audio_caps.so" "$audio_plugin_path" >/dev/null
            D "chown 0:0 '$audio_plugin_path'; chmod 0755 '$audio_plugin_path'; chcon u:object_r:system_lib_file:s0 '$audio_plugin_path'" >/dev/null
            [ "$(device_hash "$audio_plugin_path")" = "$audio_plugin_sha" ] \
                || die "runtime audio plugin staging hash mismatch"
        fi
    fi
    D "mkdir -p '$remote'" >/dev/null
    H file send "$files/liboh_adapter_bridge.so" "$remote/liboh_adapter_bridge.so" >/dev/null
    H file send "$files/libwestlake_android_runtime_provider.so" "$remote/libwestlake_android_runtime_provider.so" >/dev/null
    H file send "$files/libwestlake_android_child.z.so" "$remote/libwestlake_android_child.z.so" >/dev/null
    H file send "$files/appspawn-x" "$remote/appspawn-x" >/dev/null
    H file send "$files/oh-adapter-runtime.jar" "$remote/oh-adapter-runtime.jar" >/dev/null
    H file send "$files/libwestlake_bionic_pthread_bridge.so" "$remote/libwestlake_bionic_pthread_bridge.so" >/dev/null
    H file send "$files/libnativeloader.so" "$remote/libnativeloader.so" >/dev/null
    H file send "$files/libandroid.so" "$remote/libandroid.so" >/dev/null
    H file send "$runtime_file" "$remote/liboh_android_runtime.so" >/dev/null
    H file send "$files/libmediandk.so" "$remote/libmediandk.so" >/dev/null
    H file send "$files/libwestlake_bionic_signal_box.so" \
        "$remote/libwestlake_bionic_signal_box.so" >/dev/null
    H file send "$files/libmain.so" "$remote/libmain.so" >/dev/null
    H file send "$files/libil2cpp.so" "$remote/libil2cpp.so" >/dev/null
    H file send "$files/libtuanjie.so" "$remote/libtuanjie.so" >/dev/null
    D "chown 0:0 '$remote/liboh_adapter_bridge.so' '$remote/libwestlake_android_runtime_provider.so' '$remote/libwestlake_android_child.z.so' '$remote/appspawn-x' '$remote/oh-adapter-runtime.jar' '$remote/libwestlake_bionic_pthread_bridge.so' '$remote/libnativeloader.so' '$remote/libandroid.so' '$remote/liboh_android_runtime.so' '$remote/libmediandk.so' '$remote/libwestlake_bionic_signal_box.so' '$remote/libmain.so' '$remote/libil2cpp.so' '$remote/libtuanjie.so'; chmod 0644 '$remote/liboh_adapter_bridge.so' '$remote/libwestlake_android_runtime_provider.so' '$remote/oh-adapter-runtime.jar' '$remote/libwestlake_bionic_pthread_bridge.so' '$remote/libnativeloader.so' '$remote/libandroid.so' '$remote/liboh_android_runtime.so' '$remote/libmediandk.so'; chmod 0755 '$remote/libwestlake_android_child.z.so' '$remote/appspawn-x' '$remote/libwestlake_bionic_signal_box.so' '$remote/libmain.so' '$remote/libil2cpp.so' '$remote/libtuanjie.so'; chcon u:object_r:system_lib_file:s0 '$remote/liboh_adapter_bridge.so' '$remote/libwestlake_android_runtime_provider.so' '$remote/libwestlake_android_child.z.so' '$remote/libwestlake_bionic_pthread_bridge.so' '$remote/libnativeloader.so' '$remote/libandroid.so' '$remote/liboh_android_runtime.so'; chcon u:object_r:data_app_el1_file:s0 '$remote/libmediandk.so' '$remote/libwestlake_bionic_signal_box.so' '$remote/libmain.so' '$remote/libil2cpp.so' '$remote/libtuanjie.so'; chcon u:object_r:system_file:s0 '$remote/oh-adapter-runtime.jar'; chcon u:object_r:appspawn_exec:s0 '$remote/appspawn-x'" >/dev/null
    printf '%s\n' "$remote"
}

deploy_candidate_inner()
{
    local candidate=$1 remote audio_ready_path adapter_sha provider_sha child_sha appspawn_sha runtime_sha runtime_jar_sha pthread_bridge_sha native_loader_sha libandroid_sha mounted expected_mounts
    adapter_sha=$(manifest_value "$candidate/manifest.env" ADAPTER_SHA)
    provider_sha=$(manifest_value "$candidate/manifest.env" PROVIDER_SHA)
    child_sha=$(manifest_value "$candidate/manifest.env" CHILD_SHA)
    appspawn_sha=$(manifest_value "$candidate/manifest.env" APPSPAWN_SHA)
    runtime_sha=$(manifest_value "$candidate/manifest.env" RUNTIME_SHA)
    runtime_jar_sha=$(manifest_value "$candidate/manifest.env" RUNTIME_JAR_SHA)
    pthread_bridge_sha=$(manifest_value "$candidate/manifest.env" PTHREAD_BRIDGE_SHA)
    native_loader_sha=$(manifest_value "$candidate/manifest.env" NATIVE_LOADER_SHA)
    libandroid_sha=$(manifest_value "$candidate/manifest.env" LIBANDROID_SHA)
    remote=$(push_candidate "$candidate")
    device_stop_runtime || return 1
    audio_ready_path=$(manifest_value "$candidate/manifest.env" RUNTIME_AUDIO_READY_PATH)
    if [ -n "$audio_ready_path" ]; then
        D "mkdir -p '$(dirname "$audio_ready_path")'; rm -f '$audio_ready_path'; touch '$audio_ready_path'; chown 0:0 '$audio_ready_path'; chmod 0666 '$audio_ready_path'; chcon u:object_r:data_app_el1_file:s0 '$audio_ready_path'" >/dev/null || return 1
    fi
    device_unmount_candidate_layers || return 1
    verify_pr03_backing || return 1
    D "mount --bind '$remote/liboh_adapter_bridge.so' '$ADAPTER_TARGET' && mount --bind '$remote/libwestlake_android_runtime_provider.so' '$PROVIDER_TARGET' && mount --bind '$remote/libwestlake_android_child.z.so' '$CHILD_TARGET' && mount --bind '$remote/appspawn-x' '$APPSPAWN_TARGET' && mount --bind '$remote/oh-adapter-runtime.jar' '$RUNTIME_JAR_TARGET' && mount --bind '$remote/libwestlake_bionic_pthread_bridge.so' '$PTHREAD_BRIDGE_TARGET' && mount --bind '$remote/libnativeloader.so' '$NATIVE_LOADER_TARGET' && mount --bind '$remote/libnativeloader.so' '$ROUTE_NATIVE_LOADER_TARGET' && mount --bind '$remote/libandroid.so' '$LIBANDROID_TARGET' && chmod 0644 '$ADAPTER_TARGET' '$PROVIDER_TARGET' '$RUNTIME_JAR_TARGET' '$PTHREAD_BRIDGE_TARGET' '$NATIVE_LOADER_TARGET' '$ROUTE_NATIVE_LOADER_TARGET' '$LIBANDROID_TARGET' && chmod 0755 '$CHILD_TARGET' '$APPSPAWN_TARGET' && chcon u:object_r:system_lib_file:s0 '$ADAPTER_TARGET' '$PROVIDER_TARGET' '$CHILD_TARGET' '$PTHREAD_BRIDGE_TARGET' '$NATIVE_LOADER_TARGET' '$ROUTE_NATIVE_LOADER_TARGET' '$LIBANDROID_TARGET' && chcon u:object_r:system_file:s0 '$RUNTIME_JAR_TARGET' && chcon u:object_r:appspawn_exec:s0 '$APPSPAWN_TARGET'" >/dev/null || return 1
    expected_mounts=9
    if [ "$(manifest_value "$candidate/manifest.env" RUNTIME_CLASSNAME_FIX)" = 1 ]; then
        D "mount --bind '$remote/liboh_android_runtime.so' '$RUNTIME_TARGET' && chmod 0644 '$RUNTIME_TARGET' && chcon u:object_r:system_lib_file:s0 '$RUNTIME_TARGET'" >/dev/null \
            || return 1
        expected_mounts=10
    fi
    [ "$(device_hash "$ADAPTER_TARGET")" = "$adapter_sha" ] || return 1
    [ "$(device_hash "$PROVIDER_TARGET")" = "$provider_sha" ] || return 1
    [ "$(device_hash "$CHILD_TARGET")" = "$child_sha" ] || return 1
    [ "$(device_hash "$APPSPAWN_TARGET")" = "$appspawn_sha" ] || return 1
    [ "$(device_hash "$RUNTIME_JAR_TARGET")" = "$runtime_jar_sha" ] || return 1
    [ "$(device_hash "$PTHREAD_BRIDGE_TARGET")" = "$pthread_bridge_sha" ] || return 1
    [ "$(device_hash "$NATIVE_LOADER_TARGET")" = "$native_loader_sha" ] || return 1
    [ "$(device_hash "$ROUTE_NATIVE_LOADER_TARGET")" = "$native_loader_sha" ] || return 1
    [ "$(device_hash "$LIBANDROID_TARGET")" = "$libandroid_sha" ] || return 1
    [ "$(device_hash "$RUNTIME_TARGET")" = "$runtime_sha" ] || return 1
    mounted=$(D "grep -c '/zigzag-apk-lightup/' /proc/self/mountinfo" | trim)
    [ "$mounted" = "$expected_mounts" ] || return 1
    device_start_appspawn "$appspawn_sha" || return 1
}

deploy_candidate()
{
    local candidate=$1
    step "deploy native closure plus runtime-jar candidate to direct $BOARD_LABEL"
    if ! deploy_candidate_inner "$candidate"; then
        echo "candidate deployment failed; restoring visible PR03 mounts" >&2
        rollback_device || true
        die "candidate deployment failed"
    fi
    printf 'deployed candidate=%s adapter=%s provider=%s child=%s appspawn-x=%s runtime=%s runtime-jar=%s pthread-bridge=%s native-loader=%s route-native-loader=%s libandroid=%s\n' \
        "$candidate" \
        "$(device_hash "$ADAPTER_TARGET")" "$(device_hash "$PROVIDER_TARGET")" \
        "$(device_hash "$CHILD_TARGET")" "$(device_hash "$APPSPAWN_TARGET")" \
        "$(device_hash "$RUNTIME_TARGET")" "$(device_hash "$RUNTIME_JAR_TARGET")" \
        "$(device_hash "$PTHREAD_BRIDGE_TARGET")" \
        "$(device_hash "$NATIVE_LOADER_TARGET")" \
        "$(device_hash "$ROUTE_NATIVE_LOADER_TARGET")" "$(device_hash "$LIBANDROID_TARGET")"
}

rollback_device()
{
    local expected
    step "rollback candidate overlays to PR03 backing"
    device_stop_runtime || return 1
    device_unmount_candidate_layers || return 1
    verify_pr03_backing || return 1
    expected=$(device_hash "$REMOTE_PR03/runtime/appspawn-x")
    device_start_appspawn "$expected" || return 1
    printf 'rollback adapter=%s provider=%s child=%s appspawn-x=%s runtime=%s runtime-jar=%s pthread-bridge=%s native-loader=%s route-native-loader=%s libandroid=%s\n' \
        "$(device_hash "$ADAPTER_TARGET")" "$(device_hash "$PROVIDER_TARGET")" \
        "$(device_hash "$CHILD_TARGET")" "$(device_hash "$APPSPAWN_TARGET")" \
        "$(device_hash "$RUNTIME_TARGET")" "$(device_hash "$RUNTIME_JAR_TARGET")" \
        "$(device_hash "$PTHREAD_BRIDGE_TARGET")" "$(device_hash "$NATIVE_LOADER_TARGET")" \
        "$(device_hash "$ROUTE_NATIVE_LOADER_TARGET")" "$(device_hash "$LIBANDROID_TARGET")"
}

ensure_candidate_live()
{
    local candidate=$1 pids count expected audio_plugin_sha audio_plugin_path needs_deploy=0
    CANDIDATE_CHANGED=0
    if [ "$(device_hash "$ADAPTER_TARGET")" != "$(manifest_value "$candidate/manifest.env" ADAPTER_SHA)" ] \
        || [ "$(device_hash "$PROVIDER_TARGET")" != "$(manifest_value "$candidate/manifest.env" PROVIDER_SHA)" ] \
        || [ "$(device_hash "$CHILD_TARGET")" != "$(manifest_value "$candidate/manifest.env" CHILD_SHA)" ] \
        || [ "$(device_hash "$APPSPAWN_TARGET")" != "$(manifest_value "$candidate/manifest.env" APPSPAWN_SHA)" ] \
        || [ "$(device_hash "$RUNTIME_JAR_TARGET")" != "$(manifest_value "$candidate/manifest.env" RUNTIME_JAR_SHA)" ]; then
        needs_deploy=1
    elif [ "$(device_hash "$PTHREAD_BRIDGE_TARGET")" != "$(manifest_value "$candidate/manifest.env" PTHREAD_BRIDGE_SHA)" ]; then
        needs_deploy=1
    elif [ "$(device_hash "$NATIVE_LOADER_TARGET")" != "$(manifest_value "$candidate/manifest.env" NATIVE_LOADER_SHA)" ]; then
        needs_deploy=1
    elif [ "$(device_hash "$ROUTE_NATIVE_LOADER_TARGET")" != "$(manifest_value "$candidate/manifest.env" NATIVE_LOADER_SHA)" ]; then
        needs_deploy=1
    elif [ "$(device_hash "$LIBANDROID_TARGET")" != "$(manifest_value "$candidate/manifest.env" LIBANDROID_SHA)" ]; then
        needs_deploy=1
    elif [ "$(device_hash "$RUNTIME_TARGET")" != "$(manifest_value "$candidate/manifest.env" RUNTIME_SHA)" ]; then
        needs_deploy=1
    fi
    audio_plugin_sha=$(manifest_value "$candidate/manifest.env" RUNTIME_AUDIO_PLUGIN_SHA)
    audio_plugin_path=$(manifest_value "$candidate/manifest.env" RUNTIME_AUDIO_PLUGIN_PATH)
    if [ -n "$audio_plugin_sha" ] \
        && [ "$(device_hash "$audio_plugin_path")" != "$audio_plugin_sha" ]; then
        needs_deploy=1
    fi
    if [ "$needs_deploy" = 1 ]; then
        deploy_candidate "$candidate"
        CANDIDATE_CHANGED=1
    fi
    expected=$(manifest_value "$candidate/manifest.env" APPSPAWN_SHA)
    pids=$(D 'pidof appspawn-x 2>/dev/null' | tr ' ' '\n' | sed '/^$/d' || true)
    count=$(printf '%s\n' "$pids" | sed '/^$/d' | wc -l | trim)
    if [ "$count" = 0 ]; then
        # A clean boot intentionally has no daemon yet.  Preserve init's
        # listening ondemand socket so the first real Android launch receives
        # the inherited control FD; do not replace it with a manual server.
        device_init_listener_ready && return 0
        device_start_appspawn "$expected" || return 1
        CANDIDATE_CHANGED=1
    elif [ "$count" != 1 ] \
        || [ "$(device_hash "/proc/$(printf '%s\n' "$pids" | head -n 1)/exe")" != "$expected" ]; then
        device_stop_runtime || return 1
        device_start_appspawn "$expected" || return 1
        CANDIDATE_CHANGED=1
    fi
}

decoded_frame_md5()
{
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$1" -map 0:v:0 -f md5 - 2>/dev/null | sed -n 's/^MD5=//p' | head -n 1
}

verify_nonblank_jpeg()
{
    local image=$1 stats bytes ymin ymax
    [ -s "$image" ] || return 1
    bytes=$(wc -c < "$image" | trim)
    [ "$bytes" -ge 50000 ] || return 1
    stats="$image.signalstats.txt"
    "$FFMPEG_BIN" -hide_banner -loglevel error -i "$image" \
        -vf "signalstats,metadata=print:file=$stats" -f null - >/dev/null 2>&1 || return 1
    ymin=$(sed -n 's/^lavfi.signalstats.YMIN=//p' "$stats" | head -n 1)
    ymax=$(sed -n 's/^lavfi.signalstats.YMAX=//p' "$stats" | head -n 1)
    [ -n "$ymin" ] && [ -n "$ymax" ] || return 1
    [ "$ymin" -le 30 ] && [ "$ymax" -ge 220 ]
}

bundle_uid()
{
    D "bm dump -n '$1'" | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+$'
}

prepare_sandbox()
{
    local bundle=$1 uid=$2
    D "set -e; for d in /data/app/el1/100/base /data/app/el1/100/database /data/app/el2/100/base /data/app/el2/100/database /data/app/el2/100/sharefiles /data/app/el3/100/base /data/app/el3/100/database /data/app/el4/100/base /data/app/el4/100/database; do mkdir -p \${d}/'$bundle'; done; mkdir -p /data/app/el2/100/log/'$bundle'; for s in cache code_cache databases files haps no_backup preferences shared_prefs temp; do mkdir -p /data/app/el2/100/base/'$bundle'/\${s}; done; chown -R '$uid':'$uid' /data/app/el1/100/base/'$bundle' /data/app/el1/100/database/'$bundle' /data/app/el2/100/base/'$bundle' /data/app/el2/100/database/'$bundle' /data/app/el2/100/sharefiles/'$bundle' /data/app/el3/100/base/'$bundle' /data/app/el3/100/database/'$bundle' /data/app/el4/100/base/'$bundle' /data/app/el4/100/database/'$bundle'; chown '$uid':log /data/app/el2/100/log/'$bundle'; chmod -R 0700 /data/app/el1/100/base/'$bundle' /data/app/el2/100/base/'$bundle' /data/app/el2/100/sharefiles/'$bundle' /data/app/el3/100/base/'$bundle' /data/app/el4/100/base/'$bundle'; chmod 0770 /data/app/el1/100/database/'$bundle' /data/app/el2/100/database/'$bundle' /data/app/el2/100/log/'$bundle' /data/app/el3/100/database/'$bundle' /data/app/el4/100/database/'$bundle'; chcon -R u:object_r:appdat:s0 /data/app/el1/100/base/'$bundle' /data/app/el1/100/database/'$bundle' /data/app/el2/100/base/'$bundle' /data/app/el2/100/database/'$bundle' /data/app/el2/100/sharefiles/'$bundle' /data/app/el3/100/base/'$bundle' /data/app/el3/100/database/'$bundle' /data/app/el4/100/base/'$bundle' /data/app/el4/100/database/'$bundle'; chcon u:object_r:data_app_el2_file:s0 /data/app/el2/100/log/'$bundle'" >/dev/null
}

hello_regression()
{
    local candidate=$1 run uid child="" attempt logs before after
    run="$EVIDENCE_ROOT/ab-compare/$(date +%Y%m%d-%H%M%S)-${BOARD_LABEL}-helloworld-candidate"
    mkdir -p "$run"
    printf '%s\n' "$run" > "$PAYLOAD_ROOT/last-hello-run"
    uid=$(bundle_uid "$HELLO_BUNDLE")
    [ -n "$uid" ] || return 1
    prepare_sandbox "$HELLO_BUNDLE" "$uid"
    D "power-shell wakeup; aa force-stop '$HELLO_BUNDLE' >/dev/null 2>&1 || true; hilog -r >/dev/null 2>&1 || true" >/dev/null
    D "aa start -a '$HELLO_ABILITY' -b '$HELLO_BUNDLE' -W" > "$run/launch.txt"
    for attempt in $(seq 1 20); do
        D "printf 'sample=%s\\n' '$attempt'; date; pidof appspawn-x 2>/dev/null || true; ps -ef | grep -E 'appspawn-x|$HELLO_BUNDLE|^$uid ' | grep -v grep || true" >> "$run/process-timeline.txt" || true
        # The Android child replaces argv[0]/comm with the package name before
        # the first polling interval.  Select it by the bundle's dedicated UID
        # instead of requiring the inherited appspawn-x command line.
        child=$(D "ps -ef | grep '^$uid ' | grep -v grep | head -n 1" || true)
        [ -n "$child" ] && break
        sleep 1
    done
    if [ -z "$child" ]; then
        D "hilog -x | tail -n 5000" > "$run/hilog-failure.log" || true
        D "dmesg | tail -n 2000" > "$run/dmesg-failure.log" || true
        return 1
    fi
    for attempt in $(seq 1 15); do
        logs=$(D "hilog -x | grep -E '$HELLO_BUNDLE|Hello World|mVisibleFromServer' | tail -n 800" || true)
        if printf '%s\n' "$logs" | grep -q 'mVisibleFromServer=true' \
            && printf '%s\n' "$logs" | grep -q 'Hello World'; then
            break
        fi
        sleep 1
    done
    printf '%s\n' "$logs" > "$run/visibility.log"
    printf '%s\n' "$logs" | grep -q 'mVisibleFromServer=true' || return 1
    printf '%s\n' "$logs" | grep -q 'Hello World' || return 1
    D "snapshot_display -f /data/local/tmp/zigzag-hello-before.jpeg" >/dev/null
    H file recv /data/local/tmp/zigzag-hello-before.jpeg "$run/before.jpeg" >/dev/null
    verify_nonblank_jpeg "$run/before.jpeg" || return 1
    D "hilog -r >/dev/null 2>&1 || true; uitest uiInput click 600 500 >/dev/null 2>&1 || uinput -T -c 600 500 100" >/dev/null
    sleep 2
    # hdc logs the diagnostic command itself through HDC_LOG.  Exclude that
    # echo before evaluating fatal markers, otherwise the grep pattern text is
    # misclassified as an application exception after a successful click.
    logs=$(D "hilog -x | grep -E 'Color changed to: RED|AndroidRuntimeException|Animators may only' | grep -v '/HDC_LOG:' | tail -n 200" || true)
    printf '%s\n' "$logs" > "$run/touch.log"
    printf '%s\n' "$logs" | grep -q 'Color changed to: RED' || return 1
    ! printf '%s\n' "$logs" | grep -qE 'AndroidRuntimeException|Animators may only' || return 1
    D "snapshot_display -f /data/local/tmp/zigzag-hello-after.jpeg" >/dev/null
    H file recv /data/local/tmp/zigzag-hello-after.jpeg "$run/after.jpeg" >/dev/null
    verify_nonblank_jpeg "$run/after.jpeg" || return 1
    before=$(decoded_frame_md5 "$run/before.jpeg")
    after=$(decoded_frame_md5 "$run/after.jpeg")
    [ -n "$before" ] && [ -n "$after" ] && [ "$before" != "$after" ] || return 1
    D "aa force-stop '$HELLO_BUNDLE' >/dev/null 2>&1 || true" >/dev/null
    printf 'candidate=%s\nuid=%s\nbefore_md5=%s\nafter_md5=%s\n' "$candidate" "$uid" "$before" "$after" > "$run/result.env"
    printf '%s\n' "$run"
}

install_zigzag()
{
    local remote="$REMOTE_ROOT/zigzag.apk" result dump uid
    require_hash "$ZIGZAG_SHA" "$ZIGZAG_APK"
    D "mkdir -p '$REMOTE_ROOT'" >/dev/null
    H file send "$ZIGZAG_APK" "$remote" >/dev/null
    [ "$(device_hash "$remote")" = "$ZIGZAG_SHA" ] || return 1
    D "aa force-stop '$ZIGZAG_BUNDLE' >/dev/null 2>&1 || true; for target in '$ZIGZAG_LIBMAIN_TARGET' '$ZIGZAG_LIBIL2CPP_TARGET' '$ZIGZAG_LIBTUANJIE_TARGET' '$ZIGZAG_MEDIANDK_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET'; do if grep -F \" \$target \" /proc/self/mountinfo | grep -q '/zigzag-apk-lightup/'; then umount \"\$target\"; fi; done; rm -f '$ZIGZAG_MEDIANDK_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET'; bm uninstall -n '$ZIGZAG_BUNDLE' >/dev/null 2>&1 || true" >/dev/null
    result=$(D "bm install -p '$remote'")
    printf '%s\n' "$result"
    printf '%s\n' "$result" | grep -q 'install bundle successfully' || return 1
    [ "$(device_hash "/data/app/el1/bundle/public/$ZIGZAG_BUNDLE/android/base.apk")" = "$ZIGZAG_SHA" ] || return 1
    dump=$(D "bm dump -n '$ZIGZAG_BUNDLE'")
    printf '%s\n' "$dump" | grep -q '"bundleType": 10' || return 1
    uid=$(printf '%s\n' "$dump" | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+$')
    [ -n "$uid" ] || return 1
    prepare_sandbox "$ZIGZAG_BUNDLE" "$uid"
}

mount_zigzag_native_patch()
{
    local candidate=$1 id remote expected il2cpp_expected tuanjie_expected media_expected signal_expected
    id=$(manifest_value "$candidate/manifest.env" CANDIDATE_ID)
    remote="$REMOTE_ROOT/candidates/$id/libmain.so"
    expected=$(manifest_value "$candidate/manifest.env" PATCHED_LIBMAIN_SHA)
    il2cpp_expected=$(manifest_value "$candidate/manifest.env" PATCHED_LIBIL2CPP_SHA)
    tuanjie_expected=$(manifest_value "$candidate/manifest.env" PATCHED_LIBTUANJIE_SHA)
    media_expected=$(manifest_value "$candidate/manifest.env" MEDIANDK_SHA)
    signal_expected=$(manifest_value "$candidate/manifest.env" SIGNAL_BOX_SHA)
    [ "$(device_hash "$remote")" = "$expected" ] || return 1
    [ "$(device_hash "$REMOTE_ROOT/candidates/$id/libil2cpp.so")" = "$il2cpp_expected" ] \
        || return 1
    [ "$(device_hash "$REMOTE_ROOT/candidates/$id/libtuanjie.so")" = "$tuanjie_expected" ] \
        || return 1
    [ "$(device_hash "$REMOTE_ROOT/candidates/$id/libmediandk.so")" = "$media_expected" ] \
        || return 1
    [ "$(device_hash "$REMOTE_ROOT/candidates/$id/libwestlake_bionic_signal_box.so")" = \
        "$signal_expected" ] || return 1
    [ "$(device_hash "$ZIGZAG_LIBMAIN_TARGET")" = "$ZIGZAG_LIBMAIN_RAW_SHA" ] || return 1
    [ "$(device_hash "$ZIGZAG_LIBIL2CPP_TARGET")" = "$ZIGZAG_LIBIL2CPP_RAW_SHA" ] \
        || return 1
    [ "$(device_hash "$ZIGZAG_LIBTUANJIE_TARGET")" = "$ZIGZAG_LIBTUANJIE_RAW_SHA" ] \
        || return 1
    [ -z "$(device_hash "$ZIGZAG_MEDIANDK_TARGET")" ] || return 1
    [ -z "$(device_hash "$ZIGZAG_SIGNAL_BOX_TARGET")" ] || return 1
    D "touch '$ZIGZAG_MEDIANDK_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET' && chown 0:0 '$ZIGZAG_MEDIANDK_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET' && chmod 0644 '$ZIGZAG_MEDIANDK_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET' && chcon u:object_r:data_app_el1_file:s0 '$ZIGZAG_MEDIANDK_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET' && mount --bind '$REMOTE_ROOT/candidates/$id/libmediandk.so' '$ZIGZAG_MEDIANDK_TARGET' && mount --bind '$REMOTE_ROOT/candidates/$id/libwestlake_bionic_signal_box.so' '$ZIGZAG_SIGNAL_BOX_TARGET' && mount --bind '$remote' '$ZIGZAG_LIBMAIN_TARGET' && mount --bind '$REMOTE_ROOT/candidates/$id/libil2cpp.so' '$ZIGZAG_LIBIL2CPP_TARGET' && mount --bind '$REMOTE_ROOT/candidates/$id/libtuanjie.so' '$ZIGZAG_LIBTUANJIE_TARGET' && chmod 0755 '$ZIGZAG_LIBMAIN_TARGET' '$ZIGZAG_LIBIL2CPP_TARGET' '$ZIGZAG_LIBTUANJIE_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET' && chcon u:object_r:data_app_el1_file:s0 '$ZIGZAG_LIBMAIN_TARGET' '$ZIGZAG_LIBIL2CPP_TARGET' '$ZIGZAG_LIBTUANJIE_TARGET' '$ZIGZAG_SIGNAL_BOX_TARGET'" >/dev/null || return 1
    [ "$(device_hash "$ZIGZAG_LIBMAIN_TARGET")" = "$expected" ] \
        && [ "$(device_hash "$ZIGZAG_LIBIL2CPP_TARGET")" = "$il2cpp_expected" ] \
        && [ "$(device_hash "$ZIGZAG_LIBTUANJIE_TARGET")" = "$tuanjie_expected" ] \
        && [ "$(device_hash "$ZIGZAG_MEDIANDK_TARGET")" = "$media_expected" ] \
        && [ "$(device_hash "$ZIGZAG_SIGNAL_BOX_TARGET")" = "$signal_expected" ]
}

classify_first_bad()
{
    local run=$1 log="$1/hilog.log" trace="$1/framework.ftrace" point reason
    if [ ! -s "$log" ] && [ ! -s "$trace" ]; then
        point="UNOBSERVED"; reason="hilog and ftrace missing"
    elif ! rg -q 'ScheduleAcceptWantDone|scheduleAcceptWantDone' "$log" "$trace" 2>/dev/null; then
        point="AcceptWantDone"; reason="specified-ability completion not observed"
    elif ! rg -q 'ScheduleLaunchAbility|HandleLaunchAbility|handleLaunchActivity' "$log" "$trace" 2>/dev/null; then
        point="HandleLaunchAbility"; reason="launch dispatch not observed"
    elif ! rg -qi 'UnityPlayerActivity.*onCreate|handleLaunchActivity.*UnityPlayerActivity|performCreate.*UnityPlayerActivity|tuanjie_player_loop_(enter|return)|adapter_queue_return' "$log" "$trace" 2>/dev/null; then
        point="UnityPlayerActivity.onCreate"; reason="Unity activity creation not observed"
    elif ! rg -qi 'lib(il2cpp|main|tuanjie|unity).*\.so|ZZ-PM:apk-zip-disabled' "$log" "$trace" 2>/dev/null; then
        point="Tuanjie_SO"; reason="Tuanjie native closure load not observed"
    elif ! rg -qi 'ANativeWindow|egl(CreateWindowSurface|MakeCurrent|SwapBuffers)|OH_NativeWindow|guest_egl_(enter|return)|tuanjie_(render|graphics_startup|display_startup)_(enter|return)' "$log" "$trace" 2>/dev/null; then
        point="Surface_EGL"; reason="window/EGL activity not observed"
    elif ! rg -qi 'FlushBuffer|RequestBuffer|QueueBuffer|present|buffer available|RS.*Buffer|adapter_queue_return|tuanjie_player_loop_(enter|return)' "$log" "$trace" 2>/dev/null; then
        point="buffer_present"; reason="buffer submission not observed"
    elif [ -f "$run/EARLY_EXIT.txt" ]; then
        point="process_exit_after_present"; reason="target exited before t+3 after a buffer submission"
    else
        point="touch_or_pixel"; reason="pipeline reached rendering markers; inspect pixels/input"
    fi
    printf 'first_bad=%s\nreason=%s\n' "$point" "$reason" > "$run/first-bad.env"
    printf '%s: %s\n' "$point" "$reason"
}

verify_zigzag_run()
{
    local run=$1 t3 t9 t15 taps unique before_score after_score input_changed=0
    [ ! -f "$run/INVALID_LAUNCH.txt" ] || return 1
    [ -s "$run/proc-t15.txt" ] || return 1
    [ -s "$run/hilog.log" ] || return 1
    # The buffer is system-wide: a fresh runtime logs android_fdsan_* JNI names,
    # and a previously stopped app can emit LIFECYCLE_HALF_TIMEOUT after hilog
    # reset. Neither is a ZigZag fatal. Explicit launch failures and terminating
    # native markers remain rejecting, while process/pixel checks cover lifecycle.
    if rg -qi 'OnStartSpecifiedFailed|Start Process Specified Ability TimeOut|Add Ability Stage TimeOut|native fatal|Fatal signal|SIGABRT' "$run/hilog.log"; then
        return 1
    fi
    rg -qi 'UnityPlayerActivity|lib(il2cpp|main|tuanjie|unity).*\.so|UnityMain' "$run/hilog.log" || return 1
    assess_zigzag_faultlogs "$run" || return 1
    verify_nonblank_jpeg "$run/screen-t3.jpeg" || return 1
    verify_nonblank_jpeg "$run/screen-t9.jpeg" || return 1
    verify_nonblank_jpeg "$run/screen-t15.jpeg" || return 1
    verify_nonblank_jpeg "$run/screen-after-taps.jpeg" || return 1
    t3=$(decoded_frame_md5 "$run/screen-t3.jpeg")
    t9=$(decoded_frame_md5 "$run/screen-t9.jpeg")
    t15=$(decoded_frame_md5 "$run/screen-t15.jpeg")
    taps=$(decoded_frame_md5 "$run/screen-after-taps.jpeg")
    [ -n "$t3" ] && [ -n "$t9" ] && [ -n "$t15" ] && [ -n "$taps" ] || return 1
    unique=$(printf '%s\n%s\n%s\n' "$t3" "$t9" "$t15" | sort -u | wc -l | trim)
    [ "$unique" = 3 ] || return 1
    [ "$t15" = "$taps" ] || input_changed=1
    if [ -f "$run/touches.env" ]; then
        rg -q '^requested=5$' "$run/touches.env" || return 1
        rg -q '^delivered=5$' "$run/touches.env" || return 1
    fi
    if [ -f "$run/playerprefs-before.xml" ] || [ -f "$run/playerprefs-after-game.xml" ]; then
        [ -f "$run/playerprefs-before.xml" ] || return 1
        [ -s "$run/playerprefs-after-game.xml" ] || return 1
        before_score=$(sed -n 's/.*<int name="TopScore" value="\([0-9][0-9]*\)".*/\1/p' \
            "$run/playerprefs-before.xml" | head -n 1)
        after_score=$(sed -n 's/.*<int name="TopScore" value="\([0-9][0-9]*\)".*/\1/p' \
            "$run/playerprefs-after-game.xml" | head -n 1)
        before_score=${before_score:-0}
        case "$before_score:$after_score" in
            *[!0-9:]*) return 1 ;;
            *:) return 1 ;;
        esac
        [ "$after_score" -gt "$before_score" ] || return 1
        input_changed=1
        printf 'top_score_before=%s\ntop_score_after=%s\n' \
            "$before_score" "$after_score" > "$run/input-state.env"
    fi
    [ "$input_changed" = 1 ] || return 1
    printf 'input_changed=1\n' >> "$run/input-state.env"
    printf 'screen_t3_md5=%s\nscreen_t9_md5=%s\nscreen_t15_md5=%s\nscreen_after_taps_md5=%s\n' \
        "$t3" "$t9" "$t15" "$taps" > "$run/pixel-frames.env"
}

assess_zigzag_faultlogs()
{
    local run=$1 list="$1/faultlogs-new.txt" assessment="$1/faultlog-assessment.env"
    local first_pid faultlog local_fault count=0 recoverable=0
    [ -f "$list" ] || return 1
    first_pid=$(sed -n '1p' "$run/first-pid.txt" 2>/dev/null | trim)
    [ -n "$first_pid" ] || return 1
    : > "$assessment"
    while IFS= read -r faultlog; do
        [ -n "$faultlog" ] || continue
        count=$((count + 1))
        local_fault="$run/faultlog-$(basename "$faultlog")"
        [ -s "$local_fault" ] || {
            printf 'status=REJECTED_MISSING_FAULTLOG\npath=%s\n' "$faultlog" \
                > "$assessment"
            return 1
        }
        if rg -q "^Pid:${first_pid}$" "$local_fault" \
            && rg -q 'Reason:Signal:SIGSEGV\(SEGV_MAPERR\)@0x?0*8[[:space:]]' \
                "$local_fault" \
            && rg -q 'SystemVibrator\.hasVibrator\+124' "$local_fault" \
            && grep -Eq "[[:space:]]${first_pid}[[:space:]]" "$run/proc-t15.txt"; then
            # ART deliberately uses SIGSEGV for implicit Java null checks.  The
            # private signal box preserves ART's handler; the same PID at t+15
            # proves this first-chance report was handled and was not fatal.
            recoverable=$((recoverable + 1))
            printf 'recoverable_%s=ART_IMPLICIT_NULLCHECK_SIGSEGV8:%s\n' \
                "$recoverable" "$(basename "$faultlog")" >> "$assessment"
        else
            printf 'status=REJECTED_UNCLASSIFIED_FAULT\npath=%s\n' "$faultlog" \
                >> "$assessment"
            return 1
        fi
    done < "$list"
    printf 'status=NO_TERMINATING_NATIVE_FATAL\nfaultlog_count=%s\nrecoverable_count=%s\n' \
        "$count" "$recoverable" >> "$assessment"
}

LIGHT_RUN_RESULT=""

collect_zigzag_light_diagnostics()
{
    local run=$1 faultlog fault_name
    D "hilog -x" > "$run/hilog.log" || true
    D "find /data/log/faultlog -type f 2>/dev/null | sort" \
        > "$run/faultlogs-after.txt" || true
    comm -13 "$run/faultlogs-before.txt" "$run/faultlogs-after.txt" \
        > "$run/faultlogs-new.txt" || true
    while IFS= read -r faultlog; do
        [ -n "$faultlog" ] || continue
        fault_name=$(basename "$faultlog")
        H file recv "$faultlog" "$run/faultlog-$fault_name" >/dev/null 2>&1 || true
    done < "$run/faultlogs-new.txt"
}

capture_zigzag_light()
{
    local candidate=$1 reason=${2:-post-reboot} ts run uid early_sample proc first_pid=""
    local delivered=0 i t remote_image
    case "$reason" in *[!A-Za-z0-9._-]*) die "unsafe light-run reason: $reason" ;; esac
    ts=$(date +%Y%m%d-%H%M%S)
    run="$EVIDENCE_ROOT/ab-compare/${ts}-${BOARD_LABEL}-zigzag-apk-light-${reason}"
    mkdir -p "$run"
    printf '%s\n' "$run" > "$PAYLOAD_ROOT/last-light-run"
    uid=$(bundle_uid "$ZIGZAG_BUNDLE")
    [ -n "$uid" ] || return 1
    {
        printf 'capture_mode=light-no-system-trace\n'
        printf 'reason=%s\n' "$reason"
        printf 'ROM=%s\n' "$(D 'param get const.ohos.fullname' | trim)"
        printf 'boot_id=%s\n' "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
        printf 'board=%s\n' "$BOARD"
        printf 'bundle=%s\nability=%s\nuid=%s\n' "$ZIGZAG_BUNDLE" "$ZIGZAG_ABILITY" "$uid"
        printf 'artifact=%s\nartifact_sha256=%s\n' "$ZIGZAG_APK" "$(sha256_file "$ZIGZAG_APK")"
        printf 'candidate=%s\nadapter_sha256=%s\n' "$candidate" "$(device_hash "$ADAPTER_TARGET")"
    } > "$run/envstamp.txt"
    D "find /data/log/faultlog -type f 2>/dev/null | sort" > "$run/faultlogs-before.txt" || true
    D "power-shell wakeup; power-shell timeout -o 86400000; power-shell setmode 602; uitest uiInput keyEvent Home >/dev/null 2>&1 || true; uitest dumpLayout -p /data/local/tmp/zigzag-light-prelaunch.json >/dev/null 2>&1 || true; if grep -q ScreenLockRootComponent /data/local/tmp/zigzag-light-prelaunch.json 2>/dev/null; then uitest uiInput swipe 600 1700 600 300 800 >/dev/null 2>&1 || true; fi" >/dev/null
    D "aa force-stop '$ZIGZAG_BUNDLE' >/dev/null 2>&1 || true; hilog -r >/dev/null 2>&1 || true" >/dev/null
    sleep 2
    D "aa start -a '$ZIGZAG_ABILITY' -b '$ZIGZAG_BUNDLE' -W" > "$run/launch.txt"
    rg -q 'start ability successfully' "$run/launch.txt" || return 1

    : > "$run/proc-early.txt"
    for early_sample in $(seq 1 24); do
        proc=$(D "ps -ef | grep -E '^$uid[[:space:]]|$ZIGZAG_BUNDLE' | grep -v grep" || true)
        printf 'sample=%s\n%s\n' "$early_sample" "$proc" >> "$run/proc-early.txt"
        if [ -z "$first_pid" ] && [ -n "$proc" ]; then
            first_pid=$(printf '%s\n' "$proc" | awk -v uid="$uid" '$1 == uid && $2 ~ /^[0-9]+$/ {print $2; exit}')
            [ -n "$first_pid" ] && printf '%s\n' "$first_pid" > "$run/first-pid.txt"
        fi
        sleep 0.1
    done

    sleep 3
    for t in 3 9 15; do
        remote_image="/data/local/tmp/zigzag-light-${ts}-t${t}.jpeg"
        D "snapshot_display -f '$remote_image'" >/dev/null || return 1
        H file recv "$remote_image" "$run/screen-t${t}.jpeg" >/dev/null || return 1
        D "ps -ef | grep -E '^$uid[[:space:]]|$ZIGZAG_BUNDLE' | grep -v grep" > "$run/proc-t${t}.txt" || true
        if [ "$t" = 3 ]; then
            D "cat '$ZIGZAG_PLAYER_PREFS' 2>/dev/null || true" \
                > "$run/playerprefs-before.xml"
            [ -s "$run/proc-t3.txt" ] || {
                if [ -n "$first_pid" ]; then
                    printf 'EARLY_EXIT first_pid=%s\n' "$first_pid" > "$run/EARLY_EXIT.txt"
                else
                    printf 'INVALID_LAUNCH\n' > "$run/INVALID_LAUNCH.txt"
                fi
                collect_zigzag_light_diagnostics "$run"
                return 1
            }
            for i in 1 2 3; do
                D "uitest uiInput click 600 1320 >/dev/null 2>&1 || uinput -T -c 600 1320 100" >/dev/null || return 1
                delivered=$((delivered + 1))
                sleep 1
            done
            sleep 3
        elif [ "$t" = 9 ]; then
            D "cat '$ZIGZAG_PLAYER_PREFS' 2>/dev/null || true" \
                > "$run/playerprefs-after-game.xml"
            sleep 3
            for i in 4 5; do
                D "uitest uiInput click 600 1320 >/dev/null 2>&1 || uinput -T -c 600 1320 100" >/dev/null || return 1
                delivered=$((delivered + 1))
                sleep 1
            done
            remote_image="/data/local/tmp/zigzag-light-${ts}-taps.jpeg"
            D "snapshot_display -f '$remote_image'" >/dev/null || return 1
            H file recv "$remote_image" "$run/screen-after-taps.jpeg" >/dev/null || return 1
            sleep 1
        fi
    done
    sleep 3
    printf 'requested=5\ndelivered=%s\nx=600\ny=1320\n' "$delivered" > "$run/touches.env"
    collect_zigzag_light_diagnostics "$run"
    printf '# Lightweight device receipt\n\nSystem trace was intentionally omitted; the accepted full-trace run remains the trace authority. This receipt rechecks exact APK identity, process persistence, pixels, five delivered touches, and the resulting game-state change.\n' > "$run/OBSERVABILITY.md"
    LIGHT_RUN_RESULT=$run
}

hello_baseline_matches()
{
    local candidate=$1
    [ -f "$HELLO_BASELINE_STAMP" ] \
        && [ "$(manifest_value "$HELLO_BASELINE_STAMP" board)" = "$BOARD" ] \
        && [ "$(manifest_value "$HELLO_BASELINE_STAMP" boot_id)" = \
            "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)" ] \
        && [ "$(manifest_value "$HELLO_BASELINE_STAMP" candidate_id)" = \
            "$(manifest_value "$candidate/manifest.env" CANDIDATE_ID)" ]
}

record_hello_baseline()
{
    local candidate=$1 evidence=$2 tmp
    mkdir -p "$PAYLOAD_ROOT"
    tmp=$(mktemp "$PAYLOAD_ROOT/.zigzag-hello-baseline.XXXXXX")
    {
        printf 'board=%s\n' "$BOARD"
        printf 'boot_id=%s\n' "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)"
        printf 'candidate_id=%s\n' "$(manifest_value "$candidate/manifest.env" CANDIDATE_ID)"
        printf 'evidence=%s\n' "$evidence"
    } > "$tmp"
    mv "$tmp" "$HELLO_BASELINE_STAMP"
}

run_candidate_light()
{
    local candidate=$1 reason=${2:-post-reboot} hello_policy=${3:-always}
    local hello_run=SKIPPED_ACCEPTED_RUNTIME_UNCHANGED run
    [ -x "$FFMPEG_BIN" ] || die "ffmpeg is required for pixel rejection"
    ensure_candidate_live "$candidate"
    if [ "$hello_policy" != risk ] || [ "$CANDIDATE_CHANGED" = 1 ] \
        || ! hello_baseline_matches "$candidate"; then
        step "HelloWorld first-frame and touch regression ($reason)"
        if ! hello_run=$(hello_regression "$candidate"); then
            rollback_device || true
            die "HelloWorld light regression failed; visible candidate layers rolled back"
        fi
        record_hello_baseline "$candidate" "$hello_run"
    else
        step "reuse accepted HelloWorld baseline; shared runtime and boot are unchanged"
    fi
    step "install byte-identical ZigZag APK ($reason)"
    if ! install_zigzag || ! mount_zigzag_native_patch "$candidate"; then
        rollback_device || true
        die "ZigZag light install/native patch failed; visible candidate layers rolled back"
    fi
    step "ZigZag lightweight t+3/9/15 pixels and five touches ($reason)"
    if ! capture_zigzag_light "$candidate" "$reason"; then
        rollback_device || true
        die "ZigZag lightweight capture failed; visible candidate layers rolled back"
    fi
    run=$LIGHT_RUN_RESULT
    if ! verify_zigzag_run "$run"; then
        rollback_device || true
        die "ZigZag lightweight acceptance not met; evidence=$run"
    fi
    printf 'first_bad=NONE_OBSERVED_LIGHT\nreason=system trace intentionally omitted; pixel, process, game-state and fatal oracles passed\n' \
        > "$run/first-bad.env"
    printf 'NONE_OBSERVED_LIGHT: pixel, process, game-state and fatal oracles passed\n' \
        | tee "$run/first-bad.txt"
    printf 'DEVELOPER_REPRODUCIBLE_LIGHT=1\ncandidate=%s\nhello_evidence=%s\nzigzag_evidence=%s\n' \
        "$candidate" "$hello_run" "$run" > "$run/DEVELOPER-REPRODUCIBLE-LIGHT.env"
    step "lightweight developer acceptance met ($reason)"
    printf 'candidate=%s\nHelloWorld=%s\nZigZag=%s\n' "$candidate" "$hello_run" "$run"
}

run_candidate()
{
    local candidate=$1 hello_run label trace_log trace_rc run
    [ -x "$FFMPEG_BIN" ] || die "ffmpeg is required for pixel rejection"
    ensure_candidate_live "$candidate"
    step "HelloWorld first-frame and touch regression"
    if ! hello_run=$(hello_regression "$candidate"); then
        rollback_device || true
        die "HelloWorld regression failed; candidate rolled back"
    fi
    printf 'HelloWorld evidence=%s\n' "$hello_run"

    step "install byte-identical ZigZag APK"
    if ! install_zigzag; then
        rollback_device || true
        die "ZigZag install/sandbox setup failed; candidate rolled back"
    fi
    if ! mount_zigzag_native_patch "$candidate"; then
        rollback_device || true
        die "ZigZag extracted libmain patch failed; candidate rolled back"
    fi

    label="zigzag-apk-$(manifest_value "$candidate/manifest.env" CANDIDATE_ID)"
    trace_log="$candidate/trace-$(date +%Y%m%d-%H%M%S).log"
    step "ZigZag t+3/9/15 trace, stacks, screenshots and five taps"
    set +e
    "$TOOLS_ROOT/devices/capture-oh-trace.sh" \
        --bundle "$ZIGZAG_BUNDLE" --ability "$ZIGZAG_ABILITY" \
        --label "$label" --board "$BOARD" --artifact "$ZIGZAG_APK" \
        --trace-depth standard --graphics-uprobes --checkpoint-taps \
        --tap-x 600 --tap-y 1320 2>&1 | tee "$trace_log"
    trace_rc=${PIPESTATUS[0]}
    set -e
    run=$(sed -n 's/^== run 目录: //p' "$trace_log" | tail -n 1)
    [ -n "$run" ] && [ -d "$run" ] || {
        rollback_device || true
        die "trace did not return an evidence directory"
    }
    printf '%s\n' "$run" > "$PAYLOAD_ROOT/last-zigzag-run"
    classify_first_bad "$run" | tee "$run/first-bad.txt"
    if [ "$trace_rc" -ne 0 ] || ! verify_zigzag_run "$run"; then
        rollback_device || true
        die "ZigZag acceptance not met; evidence=$run; candidate rolled back"
    fi
    printf 'DEVELOPER_REPRODUCIBLE=1\ncandidate=%s\nhello_evidence=%s\nzigzag_evidence=%s\n' \
        "$candidate" "$hello_run" "$run" > "$run/DEVELOPER-REPRODUCIBLE.env"
    printf '%s\n' "$candidate" > "$PAYLOAD_ROOT/accepted-candidate"
    printf '%s\n' "$run" > "$PAYLOAD_ROOT/accepted-run"
    step "automated developer acceptance met"
    printf 'candidate=%s\nHelloWorld=%s\nZigZag=%s\n' "$candidate" "$hello_run" "$run"
}

LAST_PERSIST_BACKUP=""

render_candidate_recovery()
{
    local candidate=$1 output=$2
    sed \
        -e "s/^APPSPAWN_SHA=.*/APPSPAWN_SHA=$(manifest_value "$candidate/manifest.env" APPSPAWN_SHA)/" \
        -e "s/^CHILD_SHA=.*/CHILD_SHA=$(manifest_value "$candidate/manifest.env" CHILD_SHA)/" \
        -e "s/^PROVIDER_SHA=.*/PROVIDER_SHA=$(manifest_value "$candidate/manifest.env" PROVIDER_SHA)/" \
        -e "s/^ADAPTER_SHA=.*/ADAPTER_SHA=$(manifest_value "$candidate/manifest.env" ADAPTER_SHA)/" \
        -e "s/^RUNTIME_SHA=.*/RUNTIME_SHA=$(manifest_value "$candidate/manifest.env" RUNTIME_SHA)/" \
        -e "s/^RUNTIME_JAR_SHA=.*/RUNTIME_JAR_SHA=$(manifest_value "$candidate/manifest.env" RUNTIME_JAR_SHA)/" \
        -e "s/^PTHREAD_BRIDGE_SHA=.*/PTHREAD_BRIDGE_SHA=$(manifest_value "$candidate/manifest.env" PTHREAD_BRIDGE_SHA)/" \
        -e "s/^NATIVE_LOADER_SHA=.*/NATIVE_LOADER_SHA=$(manifest_value "$candidate/manifest.env" NATIVE_LOADER_SHA)/" \
        -e "s/^ROUTE_NATIVE_LOADER_SHA=.*/ROUTE_NATIVE_LOADER_SHA=$(manifest_value "$candidate/manifest.env" NATIVE_LOADER_SHA)/" \
        -e "s/^LIBANDROID_SHA=.*/LIBANDROID_SHA=$(manifest_value "$candidate/manifest.env" LIBANDROID_SHA)/" \
        "$TOOLS_ROOT/devices/pr03-runtime-recover-device.sh" > "$output"
    chmod 0555 "$output"
    /bin/sh -n "$output"
}

persist_candidate_to_board()
{
    local candidate=$1 recovery=$2 id transaction staging backup copy_ok=1 recovery_sha recovery_cfg_sha
    local adapter_sha provider_sha child_sha appspawn_sha runtime_jar_sha pthread_sha
    local native_loader_sha libandroid_sha backup_appspawn_sha
    id=$(manifest_value "$candidate/manifest.env" CANDIDATE_ID)
    adapter_sha=$(manifest_value "$candidate/manifest.env" ADAPTER_SHA)
    provider_sha=$(manifest_value "$candidate/manifest.env" PROVIDER_SHA)
    child_sha=$(manifest_value "$candidate/manifest.env" CHILD_SHA)
    appspawn_sha=$(manifest_value "$candidate/manifest.env" APPSPAWN_SHA)
    runtime_jar_sha=$(manifest_value "$candidate/manifest.env" RUNTIME_JAR_SHA)
    pthread_sha=$(manifest_value "$candidate/manifest.env" PTHREAD_BRIDGE_SHA)
    native_loader_sha=$(manifest_value "$candidate/manifest.env" NATIVE_LOADER_SHA)
    libandroid_sha=$(manifest_value "$candidate/manifest.env" LIBANDROID_SHA)
    recovery_sha=$(sha256_file "$recovery")
    recovery_cfg_sha=$(sha256_file "$TOOLS_ROOT/devices/pr03-runtime-recovery.cfg")
    transaction="$(date -u +%Y%m%dT%H%M%SZ)-$$-$id"
    staging="$REMOTE_ROOT/persist-staging/$transaction"
    backup="$REMOTE_ROOT/persist-backup/$transaction"
    D "test ! -e '$staging' && test ! -e '$backup' && mkdir -p '$staging' '$backup'" >/dev/null \
        || die "board persistence transaction paths already exist"
    D "set -e; cp '$REMOTE_PR03/android/lib64/liboh_adapter_bridge.so' '$backup/liboh_adapter_bridge.so'; cp '$REMOTE_PR03/route/libwestlake_android_runtime_provider.so' '$backup/libwestlake_android_runtime_provider.so'; cp '$REMOTE_PR03/runtime/libwestlake_android_child.z.so' '$backup/libwestlake_android_child.z.so'; cp '$REMOTE_PR03/runtime/appspawn-x' '$backup/appspawn-x'; cp '$REMOTE_PR03/android/framework/oh-adapter-runtime.jar' '$backup/oh-adapter-runtime.jar'; cp '$REMOTE_PR03/android/lib64/libwestlake_bionic_pthread_bridge.so' '$backup/libwestlake_bionic_pthread_bridge.so'; cp '$REMOTE_PR03/android/lib64/libnativeloader.so' '$backup/libnativeloader-android.so'; cp '$REMOTE_PR03/route/libnativeloader.so' '$backup/libnativeloader-route.so'; cp '$REMOTE_PR03/android/lib64/libandroid.so' '$backup/libandroid.so'; cp /system/etc/pr03-runtime-recover.sh '$backup/pr03-runtime-recover.sh'; cp /system/etc/init/00_pr03_runtime_recovery.cfg '$backup/00_pr03_runtime_recovery.cfg'; cd '$backup'; sha256sum liboh_adapter_bridge.so libwestlake_android_runtime_provider.so libwestlake_android_child.z.so appspawn-x oh-adapter-runtime.jar libwestlake_bionic_pthread_bridge.so libnativeloader-android.so libnativeloader-route.so libandroid.so pr03-runtime-recover.sh 00_pr03_runtime_recovery.cfg > manifest.sha256; sync" >/dev/null \
        || die "could not create a complete board persistence backup"
    backup_appspawn_sha=$(device_hash "$backup/appspawn-x")

    H file send "$candidate/files/liboh_adapter_bridge.so" "$staging/liboh_adapter_bridge.so" >/dev/null
    H file send "$candidate/files/libwestlake_android_runtime_provider.so" "$staging/libwestlake_android_runtime_provider.so" >/dev/null
    H file send "$candidate/files/libwestlake_android_child.z.so" "$staging/libwestlake_android_child.z.so" >/dev/null
    H file send "$candidate/files/appspawn-x" "$staging/appspawn-x" >/dev/null
    H file send "$candidate/files/oh-adapter-runtime.jar" "$staging/oh-adapter-runtime.jar" >/dev/null
    H file send "$candidate/files/libwestlake_bionic_pthread_bridge.so" "$staging/libwestlake_bionic_pthread_bridge.so" >/dev/null
    H file send "$candidate/files/libnativeloader.so" "$staging/libnativeloader.so" >/dev/null
    H file send "$candidate/files/libandroid.so" "$staging/libandroid.so" >/dev/null
    H file send "$recovery" "$staging/pr03-runtime-recover.sh" >/dev/null
    H file send "$TOOLS_ROOT/devices/pr03-runtime-recovery.cfg" "$staging/00_pr03_runtime_recovery.cfg" >/dev/null
    [ "$(device_hash "$staging/liboh_adapter_bridge.so")" = "$adapter_sha" ] \
        && [ "$(device_hash "$staging/libwestlake_android_runtime_provider.so")" = "$provider_sha" ] \
        && [ "$(device_hash "$staging/libwestlake_android_child.z.so")" = "$child_sha" ] \
        && [ "$(device_hash "$staging/appspawn-x")" = "$appspawn_sha" ] \
        && [ "$(device_hash "$staging/oh-adapter-runtime.jar")" = "$runtime_jar_sha" ] \
        && [ "$(device_hash "$staging/libwestlake_bionic_pthread_bridge.so")" = "$pthread_sha" ] \
        && [ "$(device_hash "$staging/libnativeloader.so")" = "$native_loader_sha" ] \
        && [ "$(device_hash "$staging/libandroid.so")" = "$libandroid_sha" ] \
        && [ "$(device_hash "$staging/pr03-runtime-recover.sh")" = "$recovery_sha" ] \
        && [ "$(device_hash "$staging/00_pr03_runtime_recovery.cfg")" = "$recovery_cfg_sha" ] \
        || die "board persistence staging hash mismatch; backing was not changed"

    device_stop_runtime || die "cannot stop appspawn-x for persistence"
    if ! D "set -e; cp '$staging/liboh_adapter_bridge.so' '$REMOTE_PR03/android/lib64/liboh_adapter_bridge.so'; cp '$staging/libwestlake_android_runtime_provider.so' '$REMOTE_PR03/route/libwestlake_android_runtime_provider.so'; cp '$staging/libwestlake_android_child.z.so' '$REMOTE_PR03/runtime/libwestlake_android_child.z.so'; cp '$staging/appspawn-x' '$REMOTE_PR03/runtime/appspawn-x'; cp '$staging/oh-adapter-runtime.jar' '$REMOTE_PR03/android/framework/oh-adapter-runtime.jar'; cp '$staging/libwestlake_bionic_pthread_bridge.so' '$REMOTE_PR03/android/lib64/libwestlake_bionic_pthread_bridge.so'; cp '$staging/libnativeloader.so' '$REMOTE_PR03/android/lib64/libnativeloader.so'; cp '$staging/libnativeloader.so' '$REMOTE_PR03/route/libnativeloader.so'; cp '$staging/libandroid.so' '$REMOTE_PR03/android/lib64/libandroid.so'; cp '$staging/pr03-runtime-recover.sh' /system/etc/pr03-runtime-recover.sh; cp '$staging/00_pr03_runtime_recovery.cfg' /system/etc/init/00_pr03_runtime_recovery.cfg; chmod 0644 '$REMOTE_PR03/android/lib64/liboh_adapter_bridge.so' '$REMOTE_PR03/route/libwestlake_android_runtime_provider.so' '$REMOTE_PR03/android/framework/oh-adapter-runtime.jar' '$REMOTE_PR03/android/lib64/libwestlake_bionic_pthread_bridge.so' '$REMOTE_PR03/android/lib64/libnativeloader.so' '$REMOTE_PR03/route/libnativeloader.so' '$REMOTE_PR03/android/lib64/libandroid.so'; chmod 0755 '$REMOTE_PR03/runtime/libwestlake_android_child.z.so' '$REMOTE_PR03/runtime/appspawn-x'; chmod 0550 /system/etc/pr03-runtime-recover.sh /system/etc/init/00_pr03_runtime_recovery.cfg; chcon u:object_r:system_etc_file:s0 /system/etc/pr03-runtime-recover.sh /system/etc/init/00_pr03_runtime_recovery.cfg; sync" >/dev/null; then
        copy_ok=0
    fi
    if [ "$copy_ok" != 1 ] \
        || [ "$(device_hash "$REMOTE_PR03/android/lib64/liboh_adapter_bridge.so")" != "$adapter_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/route/libwestlake_android_runtime_provider.so")" != "$provider_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/runtime/libwestlake_android_child.z.so")" != "$child_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/runtime/appspawn-x")" != "$appspawn_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/android/framework/oh-adapter-runtime.jar")" != "$runtime_jar_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/android/lib64/libwestlake_bionic_pthread_bridge.so")" != "$pthread_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/android/lib64/libnativeloader.so")" != "$native_loader_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/route/libnativeloader.so")" != "$native_loader_sha" ] \
        || [ "$(device_hash "$REMOTE_PR03/android/lib64/libandroid.so")" != "$libandroid_sha" ] \
        || [ "$(device_hash /system/etc/pr03-runtime-recover.sh)" != "$recovery_sha" ] \
        || [ "$(device_hash /system/etc/init/00_pr03_runtime_recovery.cfg)" != "$recovery_cfg_sha" ]; then
        D "set -e; cp '$backup/liboh_adapter_bridge.so' '$REMOTE_PR03/android/lib64/liboh_adapter_bridge.so'; cp '$backup/libwestlake_android_runtime_provider.so' '$REMOTE_PR03/route/libwestlake_android_runtime_provider.so'; cp '$backup/libwestlake_android_child.z.so' '$REMOTE_PR03/runtime/libwestlake_android_child.z.so'; cp '$backup/appspawn-x' '$REMOTE_PR03/runtime/appspawn-x'; cp '$backup/oh-adapter-runtime.jar' '$REMOTE_PR03/android/framework/oh-adapter-runtime.jar'; cp '$backup/libwestlake_bionic_pthread_bridge.so' '$REMOTE_PR03/android/lib64/libwestlake_bionic_pthread_bridge.so'; cp '$backup/libnativeloader-android.so' '$REMOTE_PR03/android/lib64/libnativeloader.so'; cp '$backup/libnativeloader-route.so' '$REMOTE_PR03/route/libnativeloader.so'; cp '$backup/libandroid.so' '$REMOTE_PR03/android/lib64/libandroid.so'; cp '$backup/pr03-runtime-recover.sh' /system/etc/pr03-runtime-recover.sh; cp '$backup/00_pr03_runtime_recovery.cfg' /system/etc/init/00_pr03_runtime_recovery.cfg; sync" >/dev/null || true
        device_unmount_candidate_layers || true
        verify_pr03_backing || die "persistence failed and restored backing is not visible; backup=$backup"
        device_start_appspawn "$backup_appspawn_sha" || die "persistence failed and restored appspawn-x did not settle; backup=$backup"
        die "persistence readback failed; complete backup restored from $backup"
    fi
    device_unmount_candidate_layers || die "could not remove trial overlays after persistence"
    verify_pr03_backing || die "persisted PR03 backing is not visible"
    device_start_appspawn "$appspawn_sha" || die "persisted appspawn-x did not settle"
    D "printf 'transaction=%s\ncandidate=%s\nbackup=%s\nstate=READY\n' '$transaction' '$id' '$backup' > '$REMOTE_ROOT/persist-current.env'; sync" >/dev/null
    LAST_PERSIST_BACKUP=$backup
}

persist_candidate()
{
    local candidate=$1 accepted accepted_run id persisted local_staging recovery recovery_staging
    [ -f "$PAYLOAD_ROOT/accepted-candidate" ] || die "no accepted candidate; run must meet acceptance first"
    IFS= read -r accepted < "$PAYLOAD_ROOT/accepted-candidate"
    [ "$(cd "$accepted" && pwd -P)" = "$candidate" ] || die "persist candidate is not the accepted candidate"
    IFS= read -r accepted_run < "$PAYLOAD_ROOT/accepted-run"
    [ -f "$accepted_run/DEVELOPER-REPRODUCIBLE.env" ] || die "accepted run marker missing"
    id=$(manifest_value "$candidate/manifest.env" CANDIDATE_ID)
    persisted="$PERSISTED_ROOT/$id"
    local_staging="$PERSISTED_ROOT/.${id}.staging.$$"
    if [ -e "$persisted" ]; then
        [ -d "$persisted" ] || die "persisted candidate path is not a directory: $persisted"
        verify_candidate "$persisted"
        [ "$(manifest_value "$persisted/manifest.env" PERSISTED_FROM)" = "$candidate" ] \
            || die "existing persisted candidate has different provenance"
        [ "$(manifest_value "$persisted/manifest.env" ACCEPTED_RUN)" = "$accepted_run" ] \
            || die "existing persisted candidate has different accepted evidence"
    else
        [ ! -e "$local_staging" ] || die "local persistence staging already exists: $local_staging"
        mkdir -p "$local_staging/build"
        cp -R "$candidate/files" "$local_staging/files"
        cp -R "$candidate/reverse-analysis" "$local_staging/reverse-analysis"
        cp -R "$candidate/build/signal-abi" "$local_staging/build/signal-abi"
        cp "$candidate/manifest.env" "$local_staging/manifest.env"
        printf 'PERSISTED_FROM=%s\nACCEPTED_RUN=%s\n' "$candidate" "$accepted_run" >> "$local_staging/manifest.env"
        (cd "$local_staging/files" && shasum -a 256 * | LC_ALL=C sort) > "$local_staging/files.sha256"
        verify_candidate "$local_staging"
        mkdir -p "$PERSISTED_ROOT"
        mv "$local_staging" "$persisted"
    fi
    recovery="$persisted/pr03-runtime-recover.sh"
    recovery_staging="$persisted/.pr03-runtime-recover.sh.staging.$$"
    [ ! -e "$recovery_staging" ] || die "candidate recovery staging already exists"
    render_candidate_recovery "$persisted" "$recovery_staging"
    mv -f "$recovery_staging" "$recovery"
    chmod 0555 "$recovery"

    persist_candidate_to_board "$persisted" "$recovery"
    {
        printf 'candidate=%s\naccepted_run=%s\n' "$persisted" "$accepted_run"
        printf 'board=%s\nboot_id=%s\nbackup=%s\n' "$BOARD" "$(D 'cat /proc/sys/kernel/random/boot_id' | trim)" "$LAST_PERSIST_BACKUP"
        printf 'recovery_sha256=%s\nstate=READY\n' "$(sha256_file "$recovery")"
    } > "$persisted/board-persist.env"
    printf '%s\n' "$persisted" > "$PERSISTED_ROOT/current"
    step "candidate persisted into the Mac payload and board boot payload"
    printf 'persisted=%s\nbackup=%s\n' "$persisted" "$LAST_PERSIST_BACKUP"
}

restore_persisted()
{
    local pointer persisted
    pointer="$PERSISTED_ROOT/current"
    [ -f "$pointer" ] || die "no persisted candidate"
    IFS= read -r persisted < "$pointer"
    persisted=$(resolve_candidate "$persisted")
    "$TOOLS_ROOT/devices/restore-pr03-helloworld-5min.sh" "$BOARD"
    select_board "$BOARD"
    deploy_candidate "$persisted"
    persist_candidate_to_board "$persisted" "$persisted/pr03-runtime-recover.sh"
    run_candidate_light "$persisted" restore
}

main()
{
    local command=${1:-} board_arg candidate_arg candidate
    [ -n "$command" ] || { usage; exit 2; }
    shift || true
    case "$command" in
        build)
            [ "$#" -eq 0 ] || die "build takes no arguments"
            build_candidate
            ;;
        build-runtime)
            candidate_arg=${1:-}
            [ "$#" -le 1 ] || die "build-runtime takes at most a base candidate"
            build_runtime_candidate "$candidate_arg"
            ;;
        build-input-classname)
            candidate_arg=${1:-}
            [ "$#" -le 1 ] \
                || die "build-input-classname takes at most a base candidate"
            build_input_classname_candidate "$candidate_arg"
            ;;
        check-candidate)
            candidate_arg=${1:-}
            [ "$#" -le 1 ] || die "check-candidate takes at most a candidate"
            candidate=$(resolve_candidate "$candidate_arg")
            printf 'candidate-check=PASS candidate=%s\n' "$candidate"
            ;;
        deploy|run|run-light|run-light-risk|persist)
            board_arg=${1:-$BOARD_ONLY}
            candidate_arg=${2:-}
            [ "$#" -le 2 ] || die "$command takes at most board and candidate"
            select_board "$board_arg"
            candidate=$(resolve_candidate "$candidate_arg")
            case "$command" in
                deploy) deploy_candidate "$candidate" ;;
                run) run_candidate "$candidate" ;;
                run-light) run_candidate_light "$candidate" manual ;;
                run-light-risk) run_candidate_light "$candidate" manual risk ;;
                persist) persist_candidate "$candidate" ;;
            esac
            ;;
        rollback)
            board_arg=${1:-$BOARD_ONLY}
            [ "$#" -le 1 ] || die "rollback takes at most a board"
            select_board "$board_arg"
            rollback_device || die "rollback failed"
            ;;
        restore)
            board_arg=${1:-$BOARD_ONLY}
            [ "$#" -le 1 ] || die "restore takes at most a board"
            select_board "$board_arg"
            restore_persisted
            ;;
        -h|--help|help) usage ;;
        *) usage; die "unknown command: $command" ;;
    esac
}

main "$@"
