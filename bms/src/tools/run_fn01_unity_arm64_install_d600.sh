#!/usr/bin/env bash
set -euo pipefail

usage()
{
    cat <<'EOF'
Usage:
  src/tools/run_fn01_unity_arm64_install_d600.sh \
    --hdc PATH --serial D600_SERIAL --stack-manifest PATH \
    --run-id YYYYMMDDTHHMMSSZ-label [--execute]

Without --execute the script is read-only. With --execute it sends and installs
the exact version-controlled G2.U02 APK. It never replaces D600 system
libraries. This is a development probe: failure evidence is preserved, but
formal P/N/F, rollback, recovery, launch, and first-frame verdicts remain
outside this script.
EOF
}

HDC_BIN=""
SERIAL=""
STACK_MANIFEST=""
RUN_ID=""
EXECUTE=0

while (($#)); do
    case "$1" in
        --hdc)
            HDC_BIN="$2"
            shift 2
            ;;
        --serial)
            SERIAL="$2"
            shift 2
            ;;
        --stack-manifest)
            STACK_MANIFEST="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            shift 2
            ;;
        --execute)
            EXECUTE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "$HDC_BIN" || -z "$SERIAL" || -z "$STACK_MANIFEST" ||
      -z "$RUN_ID" ]]; then
    usage >&2
    exit 2
fi
[[ -x "$HDC_BIN" ]] || {
    echo "ERROR: hdc is not executable: $HDC_BIN" >&2
    exit 2
}
[[ -f "$STACK_MANIFEST" ]] || {
    echo "ERROR: stack manifest is missing: $STACK_MANIFEST" >&2
    exit 2
}
[[ "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z-[a-z0-9][a-z0-9._-]*$ ]] || {
    echo "ERROR: invalid run id: $RUN_ID" >&2
    exit 2
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APK="$ROOT_DIR/evidence/fixtures/unity/G2.U02/UnityHelloWorld-arm64-il2cpp.apk"
PACKAGE="com.westlake.l03a15.unityhelloworld"
ACTIVITY="com.unity3d.player.UnityPlayerGameActivity"
LABEL="UnityHelloWorld"

EXPECTED_APK_SHA="1b90458f6f47a6fbb39786e8f5418212a7f86a376be066851035b92fe10d59ee"
EXPECTED_LIBCXX_SHA="4397241b4bd20a8e579bfb41d21107857e12985f6a01ca0c2a5f83380d1270b4"
EXPECTED_LIBGAME_SHA="0f7819f624f8761048da4035ee4a47cb7f910687d5d96ec4ca7dbd5dc10084e7"
EXPECTED_LIBMAIN_SHA="db864f23088195e79a6869b876f2f357249515be240a7cec23c2455deac3146a"
EXPECTED_LIBUNITY_SHA="21b03d9771267751a7916a889dec38183e93a3155e28988a8c6e522e3dd2db96"
EXPECTED_LIBIL2CPP_SHA="5a42ecc7e70ff4728eea39016707849cdbc997698f66700aa0ca066660b96e1f"
EXPECTED_LIBSWAPPY_SHA="be6fe5f369c91658aede1b48a9506d3a1cfa476f81c4f0794dc8cf53fb66c083"

OUT_DIR="$ROOT_DIR/evidence/atoms/Fn01/A01/runs/$RUN_ID-unity-g2-u02-$SERIAL"
HOST_DIR="$OUT_DIR/host"
DEVICE_DIR="$OUT_DIR/device"
[[ ! -e "$OUT_DIR" ]] || {
    echo "ERROR: evidence output already exists; choose a fresh run id: $OUT_DIR" >&2
    exit 2
}
mkdir -p "$HOST_DIR" "$DEVICE_DIR"

REMOTE_ROOT="/data/local/tmp/$RUN_ID-unity-g2-u02"
REMOTE_APK="$REMOTE_ROOT/UnityHelloWorld-arm64-il2cpp.apk"
MANAGED_ROOT="/data/app/el1/bundle/public/$PACKAGE"
MANAGED_ANDROID="$MANAGED_ROOT/android"
MANAGED_NATIVE="$MANAGED_ANDROID/lib/arm64-v8a"

capture()
{
    local output_path="$1"
    local rc_path="$2"
    shift 2
    set +e
    "$@" >"$output_path" 2>&1
    local command_rc=$?
    set -e
    printf '%s\n' "$command_rc" >"$rc_path"
}

capture_device()
{
    local name="$1"
    local command="$2"
    capture "$DEVICE_DIR/$name.txt" "$DEVICE_DIR/$name.rc" \
        "$HDC_BIN" -t "$SERIAL" shell "$command"
}

require_text()
{
    local path="$1"
    local expected="$2"
    local reason="$3"
    grep -Fq "$expected" "$path" || {
        echo "ERROR: $reason expected=$expected file=$path" >&2
        exit 1
    }
}

manifest_sha_for()
{
    local name="$1"
    awk -v wanted="$name" '
        {
            path = $2
            sub(/^\*/, "", path)
            count = split(path, parts, "/")
            if (parts[count] == wanted) {
                print $1
            }
        }
    ' "$STACK_MANIFEST"
}

EXPECTED_INSTALLER_SHA="$(manifest_sha_for libapk_installer.so)"
EXPECTED_BMS_SHA="$(manifest_sha_for libbms.z.so)"
EXPECTED_INSTALLS_SHA="$(manifest_sha_for libinstalls.z.so)"
for value in \
    "$EXPECTED_INSTALLER_SHA" "$EXPECTED_BMS_SHA" "$EXPECTED_INSTALLS_SHA"; do
    [[ "$value" =~ ^[0-9a-f]{64}$ ]] || {
        echo "ERROR: stack manifest must name each platform library exactly once" >&2
        exit 1
    }
done

HOST_APK_SHA="$(shasum -a 256 "$APK" | awk '{print $1}')"
[[ "$HOST_APK_SHA" == "$EXPECTED_APK_SHA" ]] || {
    echo "ERROR: frozen APK identity mismatch: $HOST_APK_SHA" >&2
    exit 1
}

capture "$HOST_DIR/input-verifier.txt" "$HOST_DIR/input-verifier.rc" \
    bash "$ROOT_DIR/tools/verify_fn01_unity_arm64_input.sh" --apk "$APK"
require_text "$HOST_DIR/input-verifier.txt" \
    "UNITY_INPUT_VERDICT=PASS artifact=G2.U02" \
    "host input gate failed"

capture "$DEVICE_DIR/target-list.txt" "$DEVICE_DIR/target-list.rc" \
    "$HDC_BIN" list targets -v
require_text "$DEVICE_DIR/target-list.txt" "$SERIAL" "target is not online"

capture_device preflight-identity \
    "echo BOOT_ID=\$(cat /proc/sys/kernel/random/boot_id); echo UNAME=\$(uname -m); echo OS=\$(param get const.product.software.version); echo SELINUX=\$(getenforce 2>/dev/null || cat /sys/fs/selinux/enforce 2>/dev/null); df -k /data"
capture_device preflight-package \
    "bm dump -n $PACKAGE"
capture_device preflight-package-stack \
    "sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so; ls -lnZ /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so; for pid in \$(pidof foundation); do grep -F '/system/lib64/libbms.z.so' /proc/\$pid/maps && break; done; for pid in \$(pidof installs); do grep -F '/system/lib64/libinstalls.z.so' /proc/\$pid/maps && break; done"
capture_device preflight-layout \
    "find $MANAGED_ROOT -maxdepth 6 -print 2>/dev/null | sort"

require_text "$DEVICE_DIR/preflight-identity.txt" "UNAME=aarch64" "D600 is not aarch64"
require_text "$DEVICE_DIR/preflight-identity.txt" "OS=OpenHarmony 6.1.0.31" "firmware mismatch"
require_text "$DEVICE_DIR/preflight-identity.txt" "SELINUX=Enforcing" "SELinux is not Enforcing"
require_text "$DEVICE_DIR/preflight-package-stack.txt" "$EXPECTED_INSTALLER_SHA" "installer generation mismatch"
require_text "$DEVICE_DIR/preflight-package-stack.txt" "$EXPECTED_BMS_SHA" "BMS generation mismatch"
require_text "$DEVICE_DIR/preflight-package-stack.txt" "$EXPECTED_INSTALLS_SHA" "installd generation mismatch"
require_text "$DEVICE_DIR/preflight-package-stack.txt" "/system/lib64/libbms.z.so" "foundation BMS load path missing"
require_text "$DEVICE_DIR/preflight-package-stack.txt" "/system/lib64/libinstalls.z.so" "installs load path missing"

if grep -Fq "$PACKAGE" "$DEVICE_DIR/preflight-package.txt" ||
   [[ -s "$DEVICE_DIR/preflight-layout.txt" ]]; then
    echo "ERROR: target package is not fresh-absent: $PACKAGE" >&2
    exit 1
fi

{
    printf 'mvp=MVP-U1\n'
    printf 'artifact=G2.U02\n'
    printf 'run_id=%s\n' "$RUN_ID"
    printf 'serial=%s\n' "$SERIAL"
    printf 'execute=%s\n' "$EXECUTE"
    printf 'package=%s\n' "$PACKAGE"
    printf 'activity=%s\n' "$ACTIVITY"
    printf 'label=%s\n' "$LABEL"
    printf 'apk_sha256=%s\n' "$EXPECTED_APK_SHA"
    printf 'stack_manifest=%s\n' "$STACK_MANIFEST"
    printf 'stack_installer_sha256=%s\n' "$EXPECTED_INSTALLER_SHA"
    printf 'stack_bms_sha256=%s\n' "$EXPECTED_BMS_SHA"
    printf 'stack_installs_sha256=%s\n' "$EXPECTED_INSTALLS_SHA"
} >"$OUT_DIR/inputs.env"

if [[ "$EXECUTE" -ne 1 ]]; then
    {
        printf 'result=PASS_UNITY_G2_U02_PRECHECK\n'
        printf 'claim_boundary=READ_ONLY_INPUT_DEVICE_STACK_AND_FRESH_ABSENT_PREFLIGHT\n'
        printf 'formal_action_verdict=NOT_ISSUED\n'
        printf 'artifact=G2.U02\n'
        printf 'apk_sha256=%s\n' "$EXPECTED_APK_SHA"
        printf 'serial=%s\n' "$SERIAL"
    } >"$OUT_DIR/RESULT.txt"
    (
        cd "$OUT_DIR"
        find . -type f ! -name SHA256SUMS -print0 |
            sort -z |
            xargs -0 shasum -a 256 >SHA256SUMS
    )
    echo "UNITY_D600_PRECHECK=PASS add=--execute"
    echo "EVIDENCE=$OUT_DIR"
    exit 0
fi

"$HDC_BIN" -t "$SERIAL" shell "mkdir -p $REMOTE_ROOT"
"$HDC_BIN" -t "$SERIAL" file send "$APK" "$REMOTE_APK" \
    >"$DEVICE_DIR/stage-send.txt" 2>&1
printf '%s\n' "$?" >"$DEVICE_DIR/stage-send.rc"
capture_device staged-input \
    "sha256sum $REMOTE_APK; ls -lnZ $REMOTE_APK"
require_text "$DEVICE_DIR/staged-input.txt" "$EXPECTED_APK_SHA" "staged APK identity mismatch"

date -u '+%Y-%m-%dT%H:%M:%SZ' >"$HOST_DIR/install-started-at.txt"
capture_device install "bm install -p $REMOTE_APK"
capture_device package-dump "bm dump -n $PACKAGE"
capture_device managed-layout \
    "sha256sum $MANAGED_ANDROID/base.apk $MANAGED_NATIVE/libc++_shared.so $MANAGED_NATIVE/libgame.so $MANAGED_NATIVE/libmain.so $MANAGED_NATIVE/libunity.so $MANAGED_NATIVE/libil2cpp.so $MANAGED_NATIVE/libswappywrapper.so 2>/dev/null; find $MANAGED_ROOT -maxdepth 6 -print 2>/dev/null | sort; ls -lnZ $MANAGED_ANDROID/base.apk $MANAGED_NATIVE/libc++_shared.so $MANAGED_NATIVE/libgame.so $MANAGED_NATIVE/libmain.so $MANAGED_NATIVE/libunity.so $MANAGED_NATIVE/libil2cpp.so $MANAGED_NATIVE/libswappywrapper.so 2>/dev/null"
capture_device install-hilog \
    "hilog -x -v year -v time | grep -E '$PACKAGE|UnityHelloWorld|Apk|APK|BMSInstalld|Install' | tail -4000"
capture_device post-install-identity \
    "echo BOOT_ID=\$(cat /proc/sys/kernel/random/boot_id); sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"

require_text "$DEVICE_DIR/install.txt" "install bundle successfully" "bm install did not succeed"
require_text "$DEVICE_DIR/package-dump.txt" "$PACKAGE" "package query missing package"
require_text "$DEVICE_DIR/package-dump.txt" "$ACTIVITY" "package query missing Unity activity"
require_text "$DEVICE_DIR/package-dump.txt" "\"cpuAbi\": \"arm64-v8a\"" "package query missing ARM64 ABI"
require_text "$DEVICE_DIR/package-dump.txt" \
    "\"nativeLibraryPath\": \"$MANAGED_NATIVE\"" \
    "package query missing native library path"
require_text "$DEVICE_DIR/managed-layout.txt" "$EXPECTED_APK_SHA" "managed base.apk mismatch"
require_text "$DEVICE_DIR/managed-layout.txt" "$EXPECTED_LIBCXX_SHA" "managed libc++_shared mismatch"
require_text "$DEVICE_DIR/managed-layout.txt" "$EXPECTED_LIBGAME_SHA" "managed libgame mismatch"
require_text "$DEVICE_DIR/managed-layout.txt" "$EXPECTED_LIBMAIN_SHA" "managed libmain mismatch"
require_text "$DEVICE_DIR/managed-layout.txt" "$EXPECTED_LIBUNITY_SHA" "managed libunity mismatch"
require_text "$DEVICE_DIR/managed-layout.txt" "$EXPECTED_LIBIL2CPP_SHA" "managed libil2cpp mismatch"
require_text "$DEVICE_DIR/managed-layout.txt" "$EXPECTED_LIBSWAPPY_SHA" "managed libswappywrapper mismatch"
require_text "$DEVICE_DIR/post-install-identity.txt" "$EXPECTED_INSTALLER_SHA" "installer drifted"
require_text "$DEVICE_DIR/post-install-identity.txt" "$EXPECTED_BMS_SHA" "BMS drifted"
require_text "$DEVICE_DIR/post-install-identity.txt" "$EXPECTED_INSTALLS_SHA" "installd drifted"

{
    printf 'result=PASS_UNITY_ARM64_PACKAGE_INSTALL\n'
    printf 'claim_boundary=UNITY_ARM64_PACKAGE_INSTALL_SINGLE_SESSION\n'
    printf 'formal_action_verdict=NOT_ISSUED\n'
    printf 'artifact=G2.U02\n'
    printf 'apk_sha256=%s\n' "$EXPECTED_APK_SHA"
    printf 'package=%s\n' "$PACKAGE"
    printf 'activity=%s\n' "$ACTIVITY"
    printf 'label=%s\n' "$LABEL"
    printf 'desktop_label_boundary=VERIFY_WITH_LAUNCHER_PRESENTATION_EVIDENCE\n'
    printf 'bm_dump_application_label_is_not_desktop_label=true\n'
    printf 'serial=%s\n' "$SERIAL"
} >"$OUT_DIR/RESULT.txt"

(
    cd "$OUT_DIR"
    find . -type f ! -name SHA256SUMS -print0 |
        sort -z |
        xargs -0 shasum -a 256 >SHA256SUMS
)

echo "UNITY_D600_INSTALL_VERDICT=PASS_UNITY_ARM64_PACKAGE_INSTALL"
echo "EVIDENCE=$OUT_DIR"
