#!/usr/bin/env bash
# Capture one bounded CardWords launch as an immutable L01-L14 evidence capsule.
#
# This script intentionally does not install an APK, deploy adapter files, clear
# hilog, reboot, kill a device process, or modify the package.  It records the
# current generation as-is, including an ineligible-generation launch failure
# when CAPTURE_INELIGIBLE_RUN=1 is explicitly supplied by the owning lane.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$ROOT/.." && pwd -P)"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
SERIAL="${D600_SERIAL:-5bb5b1ae00000000000000000823012c}"
EXPECTED_SERIAL="5bb5b1ae00000000000000000823012c"
PACKAGE="com.CardWordsStudio.CardWords"
ACTIVITY="com.unity3d.player.UnityPlayerActivity"
CANONICAL_APK="${CANONICAL_APK:-$ROOT/frozen/product_inputs/cardwords-current/canonical/selfcontained_cardwords.apk}"
RUN_ID="${CARDWORDS_RUN_ID:-cardwords-d600a-$(date -u '+%Y%m%dT%H%M%SZ')}"
RUN_DIR="${CARDWORDS_RUN_DIR:-$ROOT/research/runs/$RUN_ID}"
OBSERVE_SECONDS="${CARDWORDS_OBSERVE_SECONDS:-8}"
HILOG_LINES="${CARDWORDS_HILOG_LINES:-30000}"
CAPTURE_INELIGIBLE_RUN="${CAPTURE_INELIGIBLE_RUN:-0}"

rfc3339_now() {
  local raw
  raw="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  printf '%s:%s\n' "${raw%??}" "${raw: -2}"
}

case "$RUN_ID" in
  *[!A-Za-z0-9._-]*|'')
    echo "invalid CARDWORDS_RUN_ID: $RUN_ID" >&2
    exit 2
    ;;
esac

if [[ "$SERIAL" != "$EXPECTED_SERIAL" ]]; then
  echo "refusing non-D600-A serial: $SERIAL" >&2
  exit 3
fi
if [[ ! -x "$HDC" ]]; then
  echo "HDC is not executable: $HDC" >&2
  exit 4
fi
if [[ ! -f "$CANONICAL_APK" ]]; then
  echo "canonical APK is missing: $CANONICAL_APK" >&2
  exit 5
fi
CANONICAL_APK="$(realpath "$CANONICAL_APK")"
case "$CANONICAL_APK" in
  "$PROJECT_ROOT"/*) ;;
  *)
    echo "canonical APK must resolve inside project root: $CANONICAL_APK" >&2
    exit 5
    ;;
esac
RUN_PARENT="$(realpath "$(dirname "$RUN_DIR")")"
RUN_DIR="$RUN_PARENT/$(basename "$RUN_DIR")"
case "$RUN_DIR" in
  "$PROJECT_ROOT"/*) ;;
  *)
    echo "run directory must resolve inside project root: $RUN_DIR" >&2
    exit 6
    ;;
esac
if [[ -e "$RUN_DIR" ]]; then
  echo "run directory already exists: $RUN_DIR" >&2
  exit 6
fi
if ! [[ "$OBSERVE_SECONDS" =~ ^[0-9]+$ ]] || (( OBSERVE_SECONDS < 1 || OBSERVE_SECONDS > 30 )); then
  echo "CARDWORDS_OBSERVE_SECONDS must be an integer in [1, 30]" >&2
  exit 7
fi
if ! [[ "$HILOG_LINES" =~ ^[0-9]+$ ]] || (( HILOG_LINES < 1000 || HILOG_LINES > 100000 )); then
  echo "CARDWORDS_HILOG_LINES must be an integer in [1000, 100000]" >&2
  exit 8
fi

HOST_STARTED_AT="$(rfc3339_now)"
HOST_STARTED_EPOCH="$(date '+%s')"
mkdir -p "$RUN_DIR"
COMMANDS="$RUN_DIR/commands.log"
: > "$COMMANDS"

"$ROOT/scripts/capture_cardwords_apk_inspection.sh" "$RUN_DIR"

record_command() {
  printf '%s\n' "$*" >> "$COMMANDS"
}

remote_to_file() {
  local output_file="$1"
  local command="$2"
  local rc
  record_command "hdc -t $SERIAL shell $command"
  set +e
  "$HDC" -t "$SERIAL" shell "$command" > "$output_file" 2>&1
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$output_file.rc"
  return "$rc"
}

HOST_APK_SHA256="$(sha256sum "$CANONICAL_APK" | awk '{print $1}')"
SOURCE_REVISION="$(git -C "$ROOT" rev-parse HEAD)"

{
  printf 'run_id=%s\n' "$RUN_ID"
  printf 'host_started_at=%s\n' "$HOST_STARTED_AT"
  printf 'host_started_epoch=%s\n' "$HOST_STARTED_EPOCH"
  printf 'adapter_root=%s\n' "$ROOT"
  printf 'source_revision=%s\n' "$SOURCE_REVISION"
  printf 'git_dirty_entries=%s\n' "$(git -C "$ROOT" status --short | wc -l | tr -d ' ')"
  printf 'hdc=%s\n' "$HDC"
  printf 'hdc_version=%s\n' "$($HDC -v 2>&1 | tr '\n' ' ')"
  printf 'device_serial=%s\n' "$SERIAL"
  printf 'package=%s\n' "$PACKAGE"
  printf 'activity=%s\n' "$ACTIVITY"
  printf 'canonical_apk=%s\n' "$CANONICAL_APK"
  printf 'canonical_apk_sha256=%s\n' "$HOST_APK_SHA256"
  printf 'observe_seconds=%s\n' "$OBSERVE_SECONDS"
  printf 'capture_ineligible_run=%s\n' "$CAPTURE_INELIGIBLE_RUN"
} > "$RUN_DIR/host_identity.env"

record_command "hdc list targets"
"$HDC" list targets > "$RUN_DIR/targets.txt"
grep -Fx "$SERIAL" "$RUN_DIR/targets.txt" >/dev/null

PRE_COMMAND="printf 'BOOT_ID='; cat /proc/sys/kernel/random/boot_id; printf 'UPTIME='; cut -d' ' -f1 /proc/uptime; printf 'UNAME='; uname -a; printf 'SELINUX='; getenforce 2>/dev/null || cat /sys/fs/selinux/enforce 2>/dev/null; printf 'APK_SHA='; sha256sum /data/app/el1/bundle/public/$PACKAGE/android/base.apk 2>&1; printf 'PIDS_BEFORE='; pidof appspawn-x $PACKAGE 2>/dev/null; printf '\\n'; for f in /system/bin/appspawn-x /system/android/lib64/libart.so /system/android/lib64/libnativeloader.so /system/android/lib64/libapp_native_loader.so /system/android/lib64/libart_runtime_stubs.so /system/android/lib64/libbionic_compat.so /system/android/lib64/liboh_android_runtime.so /system/android/lib64/libsigchain.so; do if test -f \"\$f\"; then sha256sum \"\$f\"; else printf 'ABSENT  %s\\n' \"\$f\"; fi; done"
remote_to_file "$RUN_DIR/device_preflight.txt" "$PRE_COMMAND"

BOOT_ID_START="$(sed -n 's/^BOOT_ID=//p' "$RUN_DIR/device_preflight.txt" | head -1 | tr -d '\r')"
MONOTONIC_START="$(sed -n 's/^UPTIME=//p' "$RUN_DIR/device_preflight.txt" | head -1 | tr -d '\r')"
DEVICE_APK_SHA256="$(sed -n 's/^APK_SHA=\([0-9a-f]\{64\}\).*/\1/p' "$RUN_DIR/device_preflight.txt" | head -1)"
if [[ -z "$BOOT_ID_START" || -z "$MONOTONIC_START" ]]; then
  echo "could not read boot identity or monotonic start" >&2
  exit 9
fi
if [[ -n "$DEVICE_APK_SHA256" && "$DEVICE_APK_SHA256" != "$HOST_APK_SHA256" ]]; then
  echo "installed APK does not match canonical APK" >&2
  exit 10
fi

remote_to_file "$RUN_DIR/package_dump.json" "bm dump -n $PACKAGE"

record_command "hdc -t $SERIAL shell pidof $PACKAGE"
EXISTING_APP_PID="$("$HDC" -t "$SERIAL" shell "pidof $PACKAGE 2>/dev/null" | tr -d '\r\n ' || true)"
printf '%s\n' "$EXISTING_APP_PID" > "$RUN_DIR/app_pid_before.txt"
if [[ -n "$EXISTING_APP_PID" ]]; then
  echo "CardWords is already running; refusing to mix an existing process into this run: $EXISTING_APP_PID" >&2
  exit 11
fi

if grep -q '^ABSENT  /system/android/lib64/' "$RUN_DIR/device_preflight.txt" && [[ "$CAPTURE_INELIGIBLE_RUN" != "1" ]]; then
  echo "current generation lacks the fixed adapter closure; set CAPTURE_INELIGIBLE_RUN=1 to capture a bounded failure run" >&2
  exit 12
fi

LAUNCH_COMMAND="aa start -a $ACTIVITY -b $PACKAGE -W"
record_command "hdc -t $SERIAL shell $LAUNCH_COMMAND"
set +e
"$HDC" -t "$SERIAL" shell "$LAUNCH_COMMAND" > "$RUN_DIR/launch.txt" 2>&1
LAUNCH_RC=$?
set -e
printf '%s\n' "$LAUNCH_RC" > "$RUN_DIR/launch.rc"

sleep "$OBSERVE_SECONDS"

POST_COMMAND="printf 'BOOT_ID='; cat /proc/sys/kernel/random/boot_id; printf 'UPTIME='; cut -d' ' -f1 /proc/uptime; printf 'PIDS_AFTER='; pidof appspawn-x $PACKAGE 2>/dev/null; printf '\\n'; ps -ef | grep -E 'appspawn-x|$PACKAGE|UnityPlayerActivity' | grep -v grep || true"
remote_to_file "$RUN_DIR/device_postflight.txt" "$POST_COMMAND"

APP_PID="$("$HDC" -t "$SERIAL" shell "pidof $PACKAGE 2>/dev/null" | tr -d '\r\n ' || true)"
printf '%s\n' "$APP_PID" > "$RUN_DIR/app_pid.txt"
if [[ "$APP_PID" =~ ^[0-9]+$ ]]; then
  remote_to_file "$RUN_DIR/app_maps.txt" "cat /proc/$APP_PID/maps"
  remote_to_file "$RUN_DIR/app_status.txt" "cat /proc/$APP_PID/status"
else
  printf 'No surviving CardWords PID after %s seconds.\n' "$OBSERVE_SECONDS" > "$RUN_DIR/app_maps.txt"
  printf '1\n' > "$RUN_DIR/app_maps.txt.rc"
  printf 'No surviving CardWords PID after %s seconds.\n' "$OBSERVE_SECONDS" > "$RUN_DIR/app_status.txt"
  printf '1\n' > "$RUN_DIR/app_status.txt.rc"
fi

record_command "hdc -t $SERIAL shell hilog -z $HILOG_LINES -v monotonic"
"$HDC" -t "$SERIAL" shell "hilog -z $HILOG_LINES -v monotonic" > "$RUN_DIR/hilog_tail.txt" 2>&1
printf '0\n' > "$RUN_DIR/hilog_tail.txt.rc"
awk -v start="$MONOTONIC_START" '
  /^[[:space:]]*[0-9]+[.][0-9]+[[:space:]]/ {
    keep = (($1 + 0) >= (start - 0.100))
  }
  keep { print }
' "$RUN_DIR/hilog_tail.txt" > "$RUN_DIR/hilog_window.txt"
rm -f "$RUN_DIR/hilog_tail.txt" "$RUN_DIR/hilog_tail.txt.rc"

DEVICE_SCREENSHOT="/data/local/tmp/${RUN_ID}.jpeg"
record_command "hdc -t $SERIAL shell snapshot_display -f $DEVICE_SCREENSHOT"
set +e
"$HDC" -t "$SERIAL" shell "snapshot_display -f $DEVICE_SCREENSHOT" > "$RUN_DIR/screenshot_capture.txt" 2>&1
SCREENSHOT_RC=$?
if (( SCREENSHOT_RC == 0 )); then
  record_command "hdc -t $SERIAL file recv $DEVICE_SCREENSHOT $RUN_DIR/screen.jpeg"
  "$HDC" -t "$SERIAL" file recv "$DEVICE_SCREENSHOT" "$RUN_DIR/screen.jpeg" >> "$RUN_DIR/screenshot_capture.txt" 2>&1
  SCREENSHOT_RC=$?
fi
record_command "hdc -t $SERIAL shell rm -f $DEVICE_SCREENSHOT"
"$HDC" -t "$SERIAL" shell "rm -f $DEVICE_SCREENSHOT" >> "$RUN_DIR/screenshot_capture.txt" 2>&1
set -e
printf '%s\n' "$SCREENSHOT_RC" > "$RUN_DIR/screenshot_capture.txt.rc"

BOOT_ID_END="$(sed -n 's/^BOOT_ID=//p' "$RUN_DIR/device_postflight.txt" | head -1 | tr -d '\r')"
if [[ "$BOOT_ID_END" != "$BOOT_ID_START" ]]; then
  echo "boot identity changed during run: $BOOT_ID_START -> $BOOT_ID_END" >&2
  exit 13
fi

HOST_ENDED_AT="$(rfc3339_now)"
HOST_ENDED_EPOCH="$(date '+%s')"
{
  printf 'run_id=%s\n' "$RUN_ID"
  printf 'host_started_at=%s\n' "$HOST_STARTED_AT"
  printf 'host_ended_at=%s\n' "$HOST_ENDED_AT"
  printf 'host_started_epoch=%s\n' "$HOST_STARTED_EPOCH"
  printf 'host_ended_epoch=%s\n' "$HOST_ENDED_EPOCH"
  printf 'source_revision=%s\n' "$SOURCE_REVISION"
  printf 'device_serial=%s\n' "$SERIAL"
  printf 'boot_id=%s\n' "$BOOT_ID_START"
  printf 'monotonic_start=%s\n' "$MONOTONIC_START"
  printf 'canonical_apk_sha256=%s\n' "$HOST_APK_SHA256"
  printf 'installed_apk_sha256=%s\n' "$DEVICE_APK_SHA256"
  printf 'launch_command=%s\n' "$LAUNCH_COMMAND"
  printf 'launch_rc=%s\n' "$LAUNCH_RC"
  printf 'surviving_app_pid=%s\n' "$APP_PID"
  printf 'cold_start=not_cold\n'
  printf 'generation=current-boot-observed-as-is\n'
} > "$RUN_DIR/run_identity.env"

"$ROOT/scripts/project_cardwords_staircase_run.py" "$RUN_DIR"
"$ROOT/scripts/update_cardwords_run_kanban_data.py" "$RUN_DIR"

(
  cd "$RUN_DIR"
  find . -maxdepth 1 -type f ! -name manifest.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > manifest.sha256
)

printf 'CARDWORDS_STAIRCASE_RUN_CAPTURED run_id=%s run_dir=%s launch_rc=%s app_pid=%s\n' \
  "$RUN_ID" "$RUN_DIR" "$LAUNCH_RC" "${APP_PID:-none}"
