#!/usr/bin/env bash

set -euo pipefail

usage()
{
    cat <<'EOF'
Usage:
  src/tools/deploy_fn01_hw248_r6_legacy_d600.sh \
    --hdc PATH --serial D600_SERIAL \
    --candidate-dir PATH --stack-manifest PATH \
    --run-id YYYYMMDDTHHMMSSZ-label [--execute]

Without --execute this is a read-only preflight. With --execute it backs up the
exact live Attempt17 trio, deploys one manifest-bound hw248 r6-legacy provider,
BMS, and installs trio, reboots, and verifies that foundation and installs load
the deployed libraries. A deployment failure restores the exact prestate and
reboots. APK installation is a separate follow-on probe.
EOF
}

HDC_BIN=""
SERIAL=""
CANDIDATE_DIR=""
STACK_MANIFEST=""
RUN_ID=""
EXECUTE=0

while (($#)); do
    case "$1" in
        --hdc) HDC_BIN="$2"; shift 2 ;;
        --serial) SERIAL="$2"; shift 2 ;;
        --candidate-dir) CANDIDATE_DIR="$2"; shift 2 ;;
        --stack-manifest) STACK_MANIFEST="$2"; shift 2 ;;
        --run-id) RUN_ID="$2"; shift 2 ;;
        --execute) EXECUTE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -x "$HDC_BIN" && -n "$SERIAL" && -d "$CANDIDATE_DIR" &&
   -f "$STACK_MANIFEST" && -n "$RUN_ID" ]] || {
    usage >&2
    exit 2
}
[[ "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z-[a-z0-9][a-z0-9._-]*$ ]] || {
    echo "ERROR: invalid run id: $RUN_ID" >&2
    exit 2
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/evidence/atoms/Fn01/A01/runs/$RUN_ID-hw248-r6-legacy-$SERIAL"
HOST_DIR="$OUT_DIR/host"
DEVICE_DIR="$OUT_DIR/device"
BACKUP_DIR="$OUT_DIR/backup"
[[ ! -e "$OUT_DIR" ]] || {
    echo "ERROR: evidence output already exists; choose a fresh run id: $OUT_DIR" >&2
    exit 2
}
mkdir -p "$HOST_DIR" "$DEVICE_DIR" "$BACKUP_DIR"

REMOTE_ROOT="/data/local/tmp/$RUN_ID-hw248-r6-legacy"
REMOTE_STAGE="$REMOTE_ROOT/stage"
REMOTE_BACKUP="$REMOTE_ROOT/backup"

NAMES=(libapk_installer.so libbms.z.so libinstalls.z.so)
DESTINATIONS=(
    /system/lib64/libapk_installer.so
    /system/lib64/libbms.z.so
    /system/lib64/libinstalls.z.so
)
ATTEMPT17_SHA=(
    c05ef4bbb33064785cc39e0d8c2778a54e6d9ec9967ae0268b97cab3aaaec0af
    89207567ad797acf379c9f5795e5c45cb38c4e207d73644a11e105da12a48c57
    979c89960cbace3067194bbf1c955b356b1d56b8bbb59a2a0bb40812c4c303a9
)
R6_PARTIAL_INGRESS_SHA=(
    ba42b28e8e47df7b53367dd6c991f26067961149f2e1619df0b83e43a4378a3f
    ee781f029008491fcf256bfb2f3e9034482f92dcfd3cb2c7036c4dc5823d8aec
    9b451b3145728313103576161146efa26a450f2a6b70c640bf3a4521f3b3fa3d
)

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

CANDIDATE_SHA=(
    "$(manifest_sha_for libapk_installer.so)"
    "$(manifest_sha_for libbms.z.so)"
    "$(manifest_sha_for libinstalls.z.so)"
)

for index in "${!NAMES[@]}"; do
    name="${NAMES[$index]}"
    path="$CANDIDATE_DIR/$name"
    expected="${CANDIDATE_SHA[$index]}"
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || {
        echo "ERROR: stack manifest must name $name exactly once" >&2
        exit 1
    }
    [[ -f "$path" ]] || {
        echo "ERROR: candidate is missing: $path" >&2
        exit 1
    }
    actual="$(shasum -a 256 "$path" | awk '{print $1}')"
    [[ "$actual" == "$expected" ]] || {
        echo "ERROR: candidate hash mismatch: $path" >&2
        exit 1
    }
done

capture "$HOST_DIR/candidate.sha256" "$HOST_DIR/candidate.sha256.rc" \
    shasum -a 256 \
    "$CANDIDATE_DIR/libapk_installer.so" \
    "$CANDIDATE_DIR/libbms.z.so" \
    "$CANDIDATE_DIR/libinstalls.z.so"
capture "$HOST_DIR/stack-manifest.sha256" \
    "$HOST_DIR/stack-manifest.sha256.rc" \
    shasum -a 256 "$STACK_MANIFEST"
capture "$DEVICE_DIR/target-list.txt" "$DEVICE_DIR/target-list.rc" \
    "$HDC_BIN" list targets -v
capture_device preflight \
    "echo OS=\$(param get const.product.software.version); echo ARCH=\$(uname -m); echo SELINUX=\$(getenforce); echo BOOT_ID=\$(cat /proc/sys/kernel/random/boot_id); cat /proc/mounts; sha256sum ${DESTINATIONS[*]}; ls -lnZ ${DESTINATIONS[*]}"

require_text "$DEVICE_DIR/target-list.txt" "$SERIAL" "D600 is not online"
require_text "$DEVICE_DIR/preflight.txt" \
    "OS=OpenHarmony 6.1.0.31" "firmware mismatch"
require_text "$DEVICE_DIR/preflight.txt" "ARCH=aarch64" "architecture mismatch"
require_text "$DEVICE_DIR/preflight.txt" \
    "SELINUX=Enforcing" "SELinux mismatch"

ALREADY_ACTIVE=1
ATTEMPT17_ACTIVE=1
R6_PARTIAL_INGRESS_ACTIVE=1
for sha in "${CANDIDATE_SHA[@]}"; do
    if ! grep -Fq "$sha" "$DEVICE_DIR/preflight.txt"; then
        ALREADY_ACTIVE=0
    fi
done
for sha in "${ATTEMPT17_SHA[@]}"; do
    if ! grep -Fq "$sha" "$DEVICE_DIR/preflight.txt"; then
        ATTEMPT17_ACTIVE=0
    fi
done
for sha in "${R6_PARTIAL_INGRESS_SHA[@]}"; do
    if ! grep -Fq "$sha" "$DEVICE_DIR/preflight.txt"; then
        R6_PARTIAL_INGRESS_ACTIVE=0
    fi
done
if [[ "$ALREADY_ACTIVE" -ne 1 && "$ATTEMPT17_ACTIVE" -ne 1 &&
      "$R6_PARTIAL_INGRESS_ACTIVE" -ne 1 ]]; then
    echo "ERROR: live platform trio is not an approved exact prestate or this candidate" >&2
    exit 1
fi

ROLLBACK_SHA=("${ATTEMPT17_SHA[@]}")
ROLLBACK_LABEL="attempt17"
if [[ "$R6_PARTIAL_INGRESS_ACTIVE" -eq 1 ]]; then
    ROLLBACK_SHA=("${R6_PARTIAL_INGRESS_SHA[@]}")
    ROLLBACK_LABEL="r6-partial-ingress"
fi

{
    printf 'profile=hw248-r6-legacy\n'
    printf 'serial=%s\n' "$SERIAL"
    printf 'execute=%s\n' "$EXECUTE"
    printf 'candidate_dir=%s\n' "$CANDIDATE_DIR"
    printf 'stack_manifest=%s\n' "$STACK_MANIFEST"
    printf 'candidate_installer_sha256=%s\n' "${CANDIDATE_SHA[0]}"
    printf 'candidate_bms_sha256=%s\n' "${CANDIDATE_SHA[1]}"
    printf 'candidate_installs_sha256=%s\n' "${CANDIDATE_SHA[2]}"
    printf 'already_active=%s\n' "$ALREADY_ACTIVE"
    printf 'attempt17_active=%s\n' "$ATTEMPT17_ACTIVE"
    printf 'r6_partial_ingress_active=%s\n' "$R6_PARTIAL_INGRESS_ACTIVE"
    printf 'rollback_label=%s\n' "$ROLLBACK_LABEL"
} >"$OUT_DIR/inputs.env"

if [[ "$EXECUTE" -ne 1 ]]; then
    {
        printf 'result=PASS_HW248_R6_LEGACY_DEPLOY_PRECHECK\n'
        printf 'claim_boundary=READ_ONLY_DEVICE_AND_CANDIDATE_PREFLIGHT\n'
        printf 'formal_action_verdict=NOT_ISSUED\n'
        printf 'serial=%s\n' "$SERIAL"
    } >"$OUT_DIR/RESULT.txt"
    (
        cd "$OUT_DIR"
        find . -type f ! -name SHA256SUMS -print0 |
            sort -z |
            xargs -0 shasum -a 256 >SHA256SUMS
    )
    echo "HW248_R6_LEGACY_PRECHECK=PASS add=--execute"
    echo "EVIDENCE=$OUT_DIR"
    exit 0
fi

wait_device()
{
    local probe
    for _ in $(seq 1 120); do
        probe="$(device "cat /proc/sys/kernel/random/boot_id" 2>&1 || true)"
        if [[ "$probe" =~ ^[0-9a-f-]{36}$ ]]; then
            return 0
        fi
        sleep 2
    done
    return 1
}

wait_platform()
{
    local boot_complete foundation_pid
    for _ in $(seq 1 120); do
        boot_complete="$(device "param get bootevent.boot.completed" 2>&1 || true)"
        foundation_pid="$(device "pidof foundation" 2>&1 || true)"
        if [[ "$boot_complete" == *"true"* &&
              "$foundation_pid" =~ [0-9]+ ]]; then
            return 0
        fi
        sleep 2
    done
    return 1
}

if [[ "$ALREADY_ACTIVE" -eq 1 ]]; then
    capture_device runtime-health \
        "bm dump -a >/dev/null; begetctl start_service installs; i=0; while test \"\$i\" -lt 30; do for pid in \$(pidof installs 2>/dev/null); do grep -F '/system/lib64/libinstalls.z.so' /proc/\$pid/maps && exit 0; done; i=\$((i+1)); sleep 1; done; exit 1"
    [[ "$(cat "$DEVICE_DIR/runtime-health.rc")" == "0" ]] || {
        echo "ERROR: already-active candidate failed runtime health" >&2
        exit 1
    }
    {
        printf 'result=PASS_HW248_R6_LEGACY_ALREADY_ACTIVE\n'
        printf 'formal_action_verdict=NOT_ISSUED\n'
    } >"$OUT_DIR/RESULT.txt"
    (
        cd "$OUT_DIR"
        find . -type f ! -name SHA256SUMS -print0 |
            sort -z |
            xargs -0 shasum -a 256 >SHA256SUMS
    )
    echo "HW248_R6_LEGACY_DEPLOY_VERDICT=PASS_ALREADY_ACTIVE"
    echo "EVIDENCE=$OUT_DIR"
    exit 0
fi

MUTATED=0
COMPLETED=0

rollback()
{
    [[ "$MUTATED" -eq 1 && "$COMPLETED" -eq 0 ]] || return 0
    echo "ROLLBACK: restoring the exact three-library prestate" >&2
    set +e
    wait_device
    "$HDC_BIN" -t "$SERIAL" target mount
    device "begetctl stop_service foundation >/dev/null 2>&1 || true"
    for index in "${!NAMES[@]}"; do
        "$HDC_BIN" -t "$SERIAL" file send \
            "$BACKUP_DIR/${NAMES[$index]}" \
            "$REMOTE_STAGE/rollback-${NAMES[$index]}"
        device "cp '$REMOTE_STAGE/rollback-${NAMES[$index]}' '${DESTINATIONS[$index]}'"
    done
    device "chown 0:0 ${DESTINATIONS[*]}; chmod 0644 ${DESTINATIONS[*]}; chcon u:object_r:system_lib_file:s0 ${DESTINATIONS[*]}; sync"
    "$HDC_BIN" -t "$SERIAL" target boot
    set -e
}

on_exit()
{
    local rc=$?
    if [[ "$rc" -ne 0 ]]; then
        rollback
    fi
}
trap on_exit EXIT

"$HDC_BIN" -t "$SERIAL" target mount \
    >"$DEVICE_DIR/target-mount.txt" 2>&1
device "mkdir -p '$REMOTE_STAGE' '$REMOTE_BACKUP'; chmod 700 '$REMOTE_ROOT' '$REMOTE_STAGE' '$REMOTE_BACKUP'"

for index in "${!NAMES[@]}"; do
    name="${NAMES[$index]}"
    destination="${DESTINATIONS[$index]}"
    device "cp -p '$destination' '$REMOTE_BACKUP/$name'"
    "$HDC_BIN" -t "$SERIAL" file recv \
        "$REMOTE_BACKUP/$name" "$BACKUP_DIR/$name" \
        >"$DEVICE_DIR/recv-$name.txt" 2>&1
    backup_sha="$(shasum -a 256 "$BACKUP_DIR/$name" | awk '{print $1}')"
    [[ "$backup_sha" == "${ROLLBACK_SHA[$index]}" ]] || {
        echo "ERROR: rollback backup mismatch: $name" >&2
        exit 1
    }
    "$HDC_BIN" -t "$SERIAL" file send \
        "$CANDIDATE_DIR/$name" "$REMOTE_STAGE/$name" \
        >"$DEVICE_DIR/send-$name.txt" 2>&1
done
shasum -a 256 "$BACKUP_DIR"/* >"$BACKUP_DIR/SHA256SUMS"

capture_device staged \
    "sha256sum '$REMOTE_STAGE/libapk_installer.so' '$REMOTE_STAGE/libbms.z.so' '$REMOTE_STAGE/libinstalls.z.so'"
for sha in "${CANDIDATE_SHA[@]}"; do
    require_text "$DEVICE_DIR/staged.txt" "$sha" "staged candidate mismatch"
done

MUTATED=1
device "begetctl stop_service foundation >/dev/null 2>&1 || true"
device "i=0; while test \"\$i\" -lt 30; do test -z \"\$(pidof foundation || true)\" && exit 0; i=\$((i+1)); sleep 1; done; exit 1"

HIDDEN_PREFIX=".fn01-hw248-r6-${CANDIDATE_SHA[1]:0:12}"
for name in "${NAMES[@]}"; do
    device "cp '$REMOTE_STAGE/$name' '/system/lib64/$HIDDEN_PREFIX-$name'; chown 0:0 '/system/lib64/$HIDDEN_PREFIX-$name'; chmod 0644 '/system/lib64/$HIDDEN_PREFIX-$name'; chcon u:object_r:system_lib_file:s0 '/system/lib64/$HIDDEN_PREFIX-$name'"
done

device "mv '/system/lib64/$HIDDEN_PREFIX-libapk_installer.so' /system/lib64/libapk_installer.so && mv '/system/lib64/$HIDDEN_PREFIX-libbms.z.so' /system/lib64/libbms.z.so && mv '/system/lib64/$HIDDEN_PREFIX-libinstalls.z.so' /system/lib64/libinstalls.z.so && sync"
capture_device candidate-before-reboot \
    "sha256sum ${DESTINATIONS[*]}; ls -lnZ ${DESTINATIONS[*]}"
for sha in "${CANDIDATE_SHA[@]}"; do
    require_text "$DEVICE_DIR/candidate-before-reboot.txt" \
        "$sha" "candidate readback mismatch"
done

capture "$DEVICE_DIR/target-boot.txt" "$DEVICE_DIR/target-boot.rc" \
    "$HDC_BIN" -t "$SERIAL" target boot
wait_device
wait_platform

capture_device candidate-after-reboot \
    "echo BOOT_ID=\$(cat /proc/sys/kernel/random/boot_id); echo SELINUX=\$(getenforce); cat /proc/mounts; sha256sum ${DESTINATIONS[*]}; ls -lnZ ${DESTINATIONS[*]}; for pid in \$(pidof foundation); do grep -F '/system/lib64/libbms.z.so' /proc/\$pid/maps && break; done"
for sha in "${CANDIDATE_SHA[@]}"; do
    require_text "$DEVICE_DIR/candidate-after-reboot.txt" \
        "$sha" "post-reboot candidate mismatch"
done
require_text "$DEVICE_DIR/candidate-after-reboot.txt" \
    "SELINUX=Enforcing" "post-reboot SELinux mismatch"
require_text "$DEVICE_DIR/candidate-after-reboot.txt" \
    " / ext4 ro," "root is not read-only"
require_text "$DEVICE_DIR/candidate-after-reboot.txt" \
    "/system/lib64/libbms.z.so" "foundation did not load BMS"

capture_device runtime-health \
    "bm dump -a >/dev/null; begetctl start_service installs; i=0; while test \"\$i\" -lt 30; do for pid in \$(pidof installs 2>/dev/null); do grep -F '/system/lib64/libinstalls.z.so' /proc/\$pid/maps && exit 0; done; i=\$((i+1)); sleep 1; done; exit 1"
[[ "$(cat "$DEVICE_DIR/runtime-health.rc")" == "0" ]] || {
    echo "ERROR: platform health check failed" >&2
    exit 1
}

COMPLETED=1
trap - EXIT

{
    printf 'result=PASS_HW248_R6_LEGACY_DEPLOYED\n'
    printf 'claim_boundary=PLATFORM_TRIO_DEPLOY_AND_LOAD\n'
    printf 'formal_action_verdict=NOT_ISSUED\n'
    printf 'serial=%s\n' "$SERIAL"
} >"$OUT_DIR/RESULT.txt"

(
    cd "$OUT_DIR"
    find . -type f ! -name SHA256SUMS -print0 |
        sort -z |
        xargs -0 shasum -a 256 >SHA256SUMS
)

echo "HW248_R6_LEGACY_DEPLOY_VERDICT=PASS"
echo "EVIDENCE=$OUT_DIR"
