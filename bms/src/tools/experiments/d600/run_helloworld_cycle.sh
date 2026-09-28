#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 RUN_ID SERIAL" >&2
  exit 2
fi

RUN_ID="$1"
SERIAL="$2"
EXPECTED_SERIAL="654b3a6b00000000000000000824012c"
EXPECTED_APK_SHA256="2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
EXPECTED_APPSPAWN_SHA256="2e78d89f81b48192c815eea3d982c6e1d9df44897c8356e735cdad47944a3737"
BRIDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
OUT="$BRIDGE_ROOT/evidence/concepts/fn08-fn12-d600-early/$RUN_ID/$SERIAL"
REMOTE_PNG="/data/local/tmp/${RUN_ID}.png"
PACKAGE="com.example.helloworld"
ABILITY="com.example.helloworld.MainActivity"

case "$RUN_ID" in
  *[!A-Za-z0-9._-]* | "")
    echo "RUN_ID contains unsafe characters: $RUN_ID" >&2
    exit 2
    ;;
esac

[ "$SERIAL" = "$EXPECTED_SERIAL" ]
[ -x "$HDC_BIN" ]
mkdir -p "$OUT"

dev()
{
  "$HDC_BIN" -t "$SERIAL" shell "$1"
}

boot_before="$(dev "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"
parent_before="$(dev "pidof appspawn-x || true" | tr -d '\r ')"
appspawn_sha256="$(dev "sha256sum /system/bin/appspawn-x" | awk '{print $1}' | tr -d '\r')"
apk_sha256="$(dev "sha256sum /data/app/el1/bundle/public/$PACKAGE/android/base.apk" | awk '{print $1}' | tr -d '\r')"
no_jit="$(dev "strings /proc/$parent_before/environ | grep '^APPSPAWNX_NO_JIT=' || true" | tr -d '\r')"

dev "bm dump -n $PACKAGE" > "$OUT/pre-bm-dump.txt" 2>&1
{
  echo "boot_id: $boot_before"
  echo "appspawn_pid: '$parent_before'"
  echo "appspawn_sha256: $appspawn_sha256"
  echo "installed_apk_sha256: $apk_sha256"
  echo "appspawn_environment: '$no_jit'"
  dev "find /sys/fs/pstore -maxdepth 1 -type f -print"
  dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|$PACKAGE' || true"
} > "$OUT/cold-start-precheck.txt" 2>&1

[ -n "$parent_before" ]
[ "$appspawn_sha256" = "$EXPECTED_APPSPAWN_SHA256" ]
[ "$apk_sha256" = "$EXPECTED_APK_SHA256" ]
[ "$no_jit" = "APPSPAWNX_NO_JIT=1" ]
grep -Fq "$ABILITY" "$OUT/pre-bm-dump.txt"

dev "aa force-stop $PACKAGE" > "$OUT/force-stop-before.txt" 2>&1 || true
old_pid=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  old_pid="$(dev "pidof $PACKAGE || true" | tr -d '\r ')"
  [ -z "$old_pid" ] && break
  sleep 1
done

if [ -n "$old_pid" ]; then
  {
    echo "experiment: E01"
    echo "verdict: BLOCK"
    echo "reason: pre-existing process did not stop within 10 seconds"
    echo "claim_boundary: MACHINE_GATES_ONLY_VISUAL_REVIEW_REQUIRED"
  } > "$OUT/E01-VERDICT.yaml"
  exit 1
fi

dev "hilog -r" > "$OUT/hilog-clear-before-cold-start.txt" 2>&1 || true
sleep 1
host_start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set +e
dev "aa start -a $ABILITY -b $PACKAGE -W" > "$OUT/aa-start.txt" 2>&1
start_rc=$?
set -e

: > "$OUT/app-pid-samples.txt"
new_pid=""
for second in $(seq 1 30); do
  new_pid="$(dev "pidof $PACKAGE || true" | tr -d '\r ')"
  echo "$second ${new_pid:-ABSENT}" >> "$OUT/app-pid-samples.txt"
  [ -n "$new_pid" ] && break
  sleep 1
done
echo "$new_pid" > "$OUT/app-pid.txt"

if [ -n "$new_pid" ]; then
  sleep 5
  render_pid="$(dev "pidof $PACKAGE || true" | tr -d '\r ')"
  dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|$PACKAGE' || true; cat /proc/$new_pid/status; cat /proc/$new_pid/maps" \
    > "$OUT/app-process-and-maps.txt" 2>&1 || true
  dev "hilog -x 2>/dev/null | grep -E '(^|[[:space:]])$new_pid([[:space:]]|$)' | tail -2400" \
    > "$OUT/app-pid-hilog.txt" 2>&1 || true
else
  render_pid=""
  : > "$OUT/app-process-and-maps.txt"
  : > "$OUT/app-pid-hilog.txt"
fi

dev "hilog -x 2>/dev/null | tail -8000" > "$OUT/hilog-after-cold-start.txt" 2>&1 || true
dev "dmesg | grep -iE 'appspawn-x|$PACKAGE|signal|SIGABRT|SIGSEGV|panic|watchdog|avc:.*denied' | tail -1200" \
  > "$OUT/dmesg-after-cold-start.txt" 2>&1 || true

set +e
dev "snapshot_display -f $REMOTE_PNG -t png" > "$OUT/snapshot-command.txt" 2>&1
snapshot_rc=$?
"$HDC_BIN" -t "$SERIAL" file recv "$REMOTE_PNG" "$OUT/screen.png" > "$OUT/snapshot-recv.txt" 2>&1
recv_rc=$?
dev "rm -f $REMOTE_PNG" > "$OUT/snapshot-cleanup.txt" 2>&1
set -e

screen_size=0
screen_sha256=""
if [ -f "$OUT/screen.png" ]; then
  screen_size="$(wc -c < "$OUT/screen.png" | tr -d ' ')"
  screen_sha256="$(sha256sum "$OUT/screen.png" | awk '{print $1}')"
fi

parent_after_render="$(dev "pidof appspawn-x || true" | tr -d '\r ')"
boot_after_render="$(dev "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"

dev "aa force-stop $PACKAGE" > "$OUT/force-stop-after.txt" 2>&1 || true
cleanup_pid=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  cleanup_pid="$(dev "pidof $PACKAGE || true" | tr -d '\r ')"
  [ -z "$cleanup_pid" ] && break
  sleep 1
done

machine_verdict="PASS_CAPTURE_READY"
reason="exact process-cold NO_JIT launch, stable child, screenshot capture and cleanup passed machine gates"
if [ "$start_rc" -ne 0 ]; then
  machine_verdict="FAIL"
  reason="aa start returned non-zero"
elif [ -z "$new_pid" ]; then
  machine_verdict="FAIL"
  reason="no app PID appeared within 30 seconds"
elif [ "$(echo "$new_pid" | awk '{print NF}')" -ne 1 ]; then
  machine_verdict="BLOCK"
  reason="multiple app PIDs make correlation ambiguous"
elif [ "$render_pid" != "$new_pid" ]; then
  machine_verdict="FAIL"
  reason="app PID did not remain stable through the render wait"
elif [ "$parent_after_render" != "$parent_before" ]; then
  machine_verdict="BLOCK"
  reason="appspawn-x parent identity changed during the launch"
elif [ "$boot_after_render" != "$boot_before" ]; then
  machine_verdict="BLOCK"
  reason="device rebooted during the experiment"
elif [ "$snapshot_rc" -ne 0 ] || [ "$recv_rc" -ne 0 ] || [ "$screen_size" -le 0 ]; then
  machine_verdict="FAIL"
  reason="non-empty screenshot was not captured"
elif [ -n "$cleanup_pid" ]; then
  machine_verdict="FAIL"
  reason="app PID remained after cleanup timeout"
fi

{
  echo "experiment: E01"
  echo "verdict: REVIEW_REQUIRED"
  echo "machine_verdict: $machine_verdict"
  echo "risk: R1_TEMPORARY_PROCESS_UI"
  echo "device_serial: $SERIAL"
  echo "boot_id_before: $boot_before"
  echo "boot_id_after_render: $boot_after_render"
  echo "host_start_utc: '$host_start_utc'"
  echo "appspawn_pid_before: '$parent_before'"
  echo "appspawn_pid_after_render: '$parent_after_render'"
  echo "appspawn_sha256: $appspawn_sha256"
  echo "installed_apk_sha256: $apk_sha256"
  echo "appspawn_environment: '$no_jit'"
  echo "start_rc: $start_rc"
  echo "app_pid: '$new_pid'"
  echo "app_pid_after_render_wait: '$render_pid'"
  echo "snapshot_rc: $snapshot_rc"
  echo "snapshot_recv_rc: $recv_rc"
  echo "snapshot_bytes: $screen_size"
  echo "snapshot_sha256: '$screen_sha256'"
  echo "cleanup_pid: '$cleanup_pid'"
  echo "reason: $reason"
  echo "claim_boundary: MACHINE_GATES_ONLY_VISUAL_REVIEW_REQUIRED"
} > "$OUT/E01-VERDICT.yaml"

echo "$machine_verdict: $reason"
test "$machine_verdict" = "PASS_CAPTURE_READY"
