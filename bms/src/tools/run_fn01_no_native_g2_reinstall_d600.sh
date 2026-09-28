#!/usr/bin/env bash

set -euo pipefail

usage()
{
    cat <<'EOF'
Usage:
  src/tools/run_fn01_no_native_g2_reinstall_d600.sh \
    --hdc PATH --serial D600_SERIAL \
    --stack-manifest PATH \
    --run-id YYYYMMDDTHHMMSSZ-label [--execute]

Without --execute this performs a read-only preflight. With --execute it backs
up any byte-identical installed G2 Minimal Tap base.apk, removes the test
package, establishes a clean-absent state, and reinstalls the unchanged
no-native APK through the live platform stack. It proves installation,
registration, managed-byte identity, and absence of native .so payloads. It
does not claim Android process launch, Unity execution, or a formal Action
verdict.
EOF
}

HDC_BIN=""
SERIAL=""
STACK_MANIFEST=""
RUN_ID=""
EXECUTE=0

while (($#)); do
    case "$1" in
        --hdc) HDC_BIN="$2"; shift 2 ;;
        --serial) SERIAL="$2"; shift 2 ;;
        --stack-manifest) STACK_MANIFEST="$2"; shift 2 ;;
        --run-id) RUN_ID="$2"; shift 2 ;;
        --execute) EXECUTE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -x "$HDC_BIN" && -n "$SERIAL" && -f "$STACK_MANIFEST" &&
   -n "$RUN_ID" ]] || {
    usage >&2
    exit 2
}
[[ "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z-[a-z0-9][a-z0-9._-]*$ ]] || {
    echo "ERROR: invalid run id: $RUN_ID" >&2
    exit 2
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APK="$ROOT_DIR/APKS/G2-Minimal-Tap/dist/g2-minimal-tap.apk"
PACKAGE="com.a2hlab.bridge.g2.minimaltap"
ACTIVITY="com.a2hlab.bridge.g2.minimaltap.MainActivity"
EXPECTED_APK_SHA="511f3b0c692e1a546008ce52d325b3b5350651dd0538deddd96d553951f3cb08"
MANAGED_ROOT="/data/app/el1/bundle/public/$PACKAGE"
MANAGED_APK="$MANAGED_ROOT/android/base.apk"
REMOTE_ROOT="/data/local/tmp/$RUN_ID-fn01-no-native-g2"
REMOTE_APK="$REMOTE_ROOT/g2-minimal-tap.apk"

OUT_DIR="$ROOT_DIR/evidence/atoms/Fn01/A01/runs/$RUN_ID-no-native-g2-$SERIAL"
HOST_DIR="$OUT_DIR/host"
DEVICE_DIR="$OUT_DIR/device"
BACKUP_DIR="$OUT_DIR/backup"
[[ ! -e "$OUT_DIR" ]] || {
    echo "ERROR: evidence output already exists; choose a fresh run id: $OUT_DIR" >&2
    exit 2
}
mkdir -p "$HOST_DIR" "$DEVICE_DIR" "$BACKUP_DIR"

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

device()
{
    "$HDC_BIN" -t "$SERIAL" shell "$1"
}

require_text()
{
    grep -Fq "$2" "$1" || {
        echo "ERROR: $3 expected=$2 file=$1" >&2
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
    echo "ERROR: frozen no-native APK identity mismatch: $HOST_APK_SHA" >&2
    exit 1
}

capture "$HOST_DIR/apk.sha256" "$HOST_DIR/apk.sha256.rc" \
    shasum -a 256 "$APK"
capture "$HOST_DIR/apk-entries.txt" "$HOST_DIR/apk-entries.rc" \
    unzip -Z1 "$APK"
capture "$HOST_DIR/apk-integrity.txt" "$HOST_DIR/apk-integrity.rc" \
    unzip -t "$APK"
capture "$HOST_DIR/stack-manifest.sha256" \
    "$HOST_DIR/stack-manifest.sha256.rc" \
    shasum -a 256 "$STACK_MANIFEST"

if grep -Eq '^lib/[^/]+/.*\.so$' "$HOST_DIR/apk-entries.txt"; then
    echo "ERROR: frozen ordinary APK unexpectedly contains native .so files" >&2
    exit 1
fi

capture "$DEVICE_DIR/target-list.txt" "$DEVICE_DIR/target-list.rc" \
    "$HDC_BIN" list targets -v
require_text "$DEVICE_DIR/target-list.txt" "$SERIAL" "D600 is not online"

capture_device preflight-identity \
    "echo BOOT_ID=\$(cat /proc/sys/kernel/random/boot_id); echo OS=\$(param get const.product.software.version); echo ARCH=\$(uname -m); echo SELINUX=\$(getenforce)"
capture_device preflight-stack \
    "sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so; for pid in \$(pidof foundation); do grep -F '/system/lib64/libbms.z.so' /proc/\$pid/maps && break; done"
capture_device preflight-package \
    "bm dump -n '$PACKAGE'; sha256sum '$MANAGED_APK' 2>/dev/null; find '$MANAGED_ROOT' -maxdepth 6 -print 2>/dev/null | sort"

require_text "$DEVICE_DIR/preflight-identity.txt" \
    "OS=OpenHarmony 6.1.0.31" "firmware mismatch"
require_text "$DEVICE_DIR/preflight-identity.txt" \
    "ARCH=aarch64" "architecture mismatch"
require_text "$DEVICE_DIR/preflight-identity.txt" \
    "SELINUX=Enforcing" "SELinux mismatch"
require_text "$DEVICE_DIR/preflight-stack.txt" \
    "$EXPECTED_INSTALLER_SHA" "installer generation mismatch"
require_text "$DEVICE_DIR/preflight-stack.txt" \
    "$EXPECTED_BMS_SHA" "BMS generation mismatch"
require_text "$DEVICE_DIR/preflight-stack.txt" \
    "$EXPECTED_INSTALLS_SHA" "installs generation mismatch"
require_text "$DEVICE_DIR/preflight-stack.txt" \
    "/system/lib64/libbms.z.so" "foundation did not load the expected BMS path"

PREEXISTING=0
if grep -Fq "\"bundleName\": \"$PACKAGE\"" \
    "$DEVICE_DIR/preflight-package.txt"; then
    PREEXISTING=1
    require_text "$DEVICE_DIR/preflight-package.txt" \
        "$EXPECTED_APK_SHA" "preexisting managed APK is not the frozen input"
fi

{
    printf 'run_id=%s\n' "$RUN_ID"
    printf 'serial=%s\n' "$SERIAL"
    printf 'execute=%s\n' "$EXECUTE"
    printf 'apk=%s\n' "$APK"
    printf 'apk_sha256=%s\n' "$EXPECTED_APK_SHA"
    printf 'package=%s\n' "$PACKAGE"
    printf 'activity=%s\n' "$ACTIVITY"
    printf 'native_so_count=0\n'
    printf 'stack_manifest=%s\n' "$STACK_MANIFEST"
    printf 'stack_installer_sha256=%s\n' "$EXPECTED_INSTALLER_SHA"
    printf 'stack_bms_sha256=%s\n' "$EXPECTED_BMS_SHA"
    printf 'stack_installs_sha256=%s\n' "$EXPECTED_INSTALLS_SHA"
    printf 'preexisting=%s\n' "$PREEXISTING"
    printf 'clean_absent_definition=UNREGISTERED_NO_MANAGED_BASE_APK_NO_NATIVE_SO\n'
} >"$OUT_DIR/inputs.env"

if [[ "$EXECUTE" -ne 1 ]]; then
    {
        printf 'result=PASS_HW248_NO_NATIVE_G2_PRECHECK\n'
        printf 'claim_boundary=READ_ONLY_INPUT_DEVICE_STACK_AND_PACKAGE_PREFLIGHT\n'
        printf 'formal_action_verdict=NOT_ISSUED\n'
        printf 'apk_sha256=%s\n' "$EXPECTED_APK_SHA"
        printf 'serial=%s\n' "$SERIAL"
    } >"$OUT_DIR/RESULT.txt"
    (
        cd "$OUT_DIR"
        find . -type f ! -name SHA256SUMS -print0 |
            sort -z |
            xargs -0 shasum -a 256 >SHA256SUMS
    )
    echo "FN01_NO_NATIVE_G2_PRECHECK=PASS add=--execute"
    echo "EVIDENCE=$OUT_DIR"
    exit 0
fi

PACKAGE_REMOVED=0
COMPLETED=0

restore_preexisting()
{
    [[ "$PREEXISTING" -eq 1 && "$PACKAGE_REMOVED" -eq 1 &&
       "$COMPLETED" -eq 0 ]] || return 0

    echo "RECOVERY: attempting to restore the byte-identical preexisting test package" >&2
    set +e
    if ! device "bm dump -n '$PACKAGE'" 2>/dev/null |
        grep -Fq "\"bundleName\": \"$PACKAGE\""; then
        "$HDC_BIN" -t "$SERIAL" shell "mkdir -p '$REMOTE_ROOT'"
        "$HDC_BIN" -t "$SERIAL" file send \
            "$BACKUP_DIR/preexisting-base.apk" \
            "$REMOTE_APK"
        "$HDC_BIN" -t "$SERIAL" shell \
            "bm install -p '$REMOTE_APK'"
    fi
    set -e
}

on_exit()
{
    local rc=$?
    if [[ "$rc" -ne 0 ]]; then
        restore_preexisting
    fi
}
trap on_exit EXIT

device "mkdir -p '$REMOTE_ROOT'; chmod 700 '$REMOTE_ROOT'"

if [[ "$PREEXISTING" -eq 1 ]]; then
    capture "$DEVICE_DIR/preexisting-base-recv.txt" \
        "$DEVICE_DIR/preexisting-base-recv.rc" \
        "$HDC_BIN" -t "$SERIAL" file recv "$MANAGED_APK" \
        "$BACKUP_DIR/preexisting-base.apk"
    BACKUP_SHA="$(shasum -a 256 "$BACKUP_DIR/preexisting-base.apk" |
        awk '{print $1}')"
    [[ "$BACKUP_SHA" == "$EXPECTED_APK_SHA" ]] || {
        echo "ERROR: received preexisting APK identity mismatch" >&2
        exit 1
    }
    PACKAGE_REMOVED=1
    capture_device uninstall-preexisting \
        "aa force-stop '$PACKAGE' >/dev/null 2>&1 || true; bm uninstall -n '$PACKAGE'"
    require_text "$DEVICE_DIR/uninstall-preexisting.txt" \
        "uninstall bundle successfully" "test package uninstall failed"
fi

capture_device clean-absent \
    "bm dump -n '$PACKAGE'; echo RESIDUAL_LAYOUT_BEGIN; if test -e '$MANAGED_ROOT'; then find '$MANAGED_ROOT' -maxdepth 6 -print | sort; fi; echo RESIDUAL_LAYOUT_END; echo RESIDUAL_NATIVE_SO_BEGIN; find '$MANAGED_ROOT' -type f -name '*.so' -print 2>/dev/null | sort; echo RESIDUAL_NATIVE_SO_END"
if grep -Fq "\"bundleName\": \"$PACKAGE\"" "$DEVICE_DIR/clean-absent.txt"; then
    echo "ERROR: package remains registered after uninstall" >&2
    exit 1
fi
if grep -Fxq "$MANAGED_APK" "$DEVICE_DIR/clean-absent.txt"; then
    echo "ERROR: managed Android base.apk remains after uninstall" >&2
    exit 1
fi
if sed -n '/^RESIDUAL_NATIVE_SO_BEGIN$/,/^RESIDUAL_NATIVE_SO_END$/p' \
    "$DEVICE_DIR/clean-absent.txt" |
    grep -Eq '\.so$'; then
    echo "ERROR: native .so payload remains after uninstall" >&2
    exit 1
fi

capture "$DEVICE_DIR/stage-send.txt" "$DEVICE_DIR/stage-send.rc" \
    "$HDC_BIN" -t "$SERIAL" file send "$APK" "$REMOTE_APK"
capture_device staged-input \
    "sha256sum '$REMOTE_APK'; ls -lnZ '$REMOTE_APK'"
require_text "$DEVICE_DIR/staged-input.txt" \
    "$EXPECTED_APK_SHA" "staged APK mismatch"

capture_device hilog-clear "hilog -r"
capture_device install "bm install -p '$REMOTE_APK'"
capture_device package-dump "bm dump -n '$PACKAGE'"
capture_device managed-layout \
    "sha256sum '$MANAGED_APK' 2>/dev/null; find '$MANAGED_ROOT' -maxdepth 8 -print 2>/dev/null | sort; echo NATIVE_SO_BEGIN; find '$MANAGED_ROOT' -type f -name '*.so' -print 2>/dev/null | sort; echo NATIVE_SO_END"
capture_device install-hilog \
    "hilog -x -v year -v time | grep -E '$PACKAGE|Apk|APK|BMS|Installd|installd|Install|CFI|SIGTRAP' | tail -4000"
capture_device post-install-stack \
    "sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so; pidof foundation"

require_text "$DEVICE_DIR/install.txt" \
    "install bundle successfully" "bm install failed"
require_text "$DEVICE_DIR/package-dump.txt" \
    "\"bundleName\": \"$PACKAGE\"" "package was not registered"
require_text "$DEVICE_DIR/package-dump.txt" \
    "$ACTIVITY" "launcher activity is missing"
require_text "$DEVICE_DIR/managed-layout.txt" \
    "$EXPECTED_APK_SHA" "managed base.apk mismatch"
require_text "$DEVICE_DIR/post-install-stack.txt" \
    "$EXPECTED_INSTALLER_SHA" "installer drifted during install"
require_text "$DEVICE_DIR/post-install-stack.txt" \
    "$EXPECTED_BMS_SHA" "BMS drifted during install"
require_text "$DEVICE_DIR/post-install-stack.txt" \
    "$EXPECTED_INSTALLS_SHA" "installs drifted during install"

if sed -n '/^NATIVE_SO_BEGIN$/,/^NATIVE_SO_END$/p' \
    "$DEVICE_DIR/managed-layout.txt" |
    grep -Eq '\.so$'; then
    echo "ERROR: managed package unexpectedly contains native .so files" >&2
    exit 1
fi

COMPLETED=1
trap - EXIT

{
    printf 'result=PASS_HW248_NO_NATIVE_G2_CLEAN_REINSTALL\n'
    printf 'claim_boundary=UNREGISTER_INSTALL_REGISTER_MANAGED_BYTE_IDENTITY_NO_NATIVE_SINGLE_SESSION\n'
    printf 'clean_absent_definition=UNREGISTERED_NO_MANAGED_BASE_APK_NO_NATIVE_SO\n'
    printf 'formal_action_verdict=NOT_ISSUED\n'
    printf 'apk_sha256=%s\n' "$EXPECTED_APK_SHA"
    printf 'native_so_count=0\n'
    printf 'package=%s\n' "$PACKAGE"
    printf 'serial=%s\n' "$SERIAL"
} >"$OUT_DIR/RESULT.txt"

(
    cd "$OUT_DIR"
    find . -type f ! -name SHA256SUMS -print0 |
        sort -z |
        xargs -0 shasum -a 256 >SHA256SUMS
)

echo "FN01_NO_NATIVE_G2_VERDICT=PASS_CLEAN_REINSTALL"
echo "EVIDENCE=$OUT_DIR"
