#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 RUN_ID SERIAL" >&2
  exit 2
fi

RUN_ID="$1"
SERIAL="$2"
BRIDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
OUT="$BRIDGE_ROOT/evidence/concepts/fn08-fn12-d600-early/$RUN_ID/$SERIAL"

mkdir -p "$OUT"

device_online()
{
  "$HDC_BIN" list targets | awk -v serial="$SERIAL" \
    '$1 == serial { found=1 } END { exit !found }'
}

dev()
{
  "$HDC_BIN" -t "$SERIAL" shell "$1"
}

device_online
boot_before="$(dev "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"
selinux="$(dev "getenforce" | tr -d '\r')"
pid_before="$(dev "pidof appspawn-x || true" | tr -d '\r ')"
pstore_before="$(dev "find /sys/fs/pstore -maxdepth 1 -type f -print" | tr -d '\r')"

{
  echo "boot_id: $boot_before"
  echo "selinux: $selinux"
  echo "pid_before: '$pid_before'"
  echo "pstore_before: '$pstore_before'"
  dev "sha256sum /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/android/lib64/libart.so /system/android/lib64/liboh_adapter_bridge.so /system/android/framework/arm64/boot.art"
  dev "ls -ldZ /system/android /system/android/framework /system/android/framework/arm64 /system/android/lib64"
  dev "ls -lZ /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/android/lib64/libart.so /system/android/framework/arm64/boot.art"
} > "$OUT/pre-start.txt"

[ "$selinux" = "Enforcing" ]
[ -z "$pid_before" ]
[ -z "$pstore_before" ]

dev "hilog -r" > "$OUT/hilog-clear.txt" 2>&1 || true
dev "begetctl start_service appspawn-x" > "$OUT/start-service.txt" 2>&1

: > "$OUT/pid-samples.txt"
stable_pid=""
verdict="PASS_STABLE_10S"
reason="one appspawn-x PID remained stable for all samples"
for sample_index in $(seq 1 40); do
  sample_time="$(date +%s.%N)"
  if ! device_online; then
    echo "$sample_time $sample_index HDC_DISCONNECTED" >> "$OUT/pid-samples.txt"
    verdict="BLOCK_DEVICE_DISCONNECT"
    reason="device disappeared from HDC during bounded start"
    break
  fi

  sample_pid="$(dev "pidof appspawn-x || true" 2>/dev/null | tr -d '\r ')"
  echo "$sample_time $sample_index ${sample_pid:-ABSENT}" >> "$OUT/pid-samples.txt"
  if [ -z "$sample_pid" ]; then
    verdict="BLOCK_PARENT_ABSENT"
    reason="appspawn-x disappeared during bounded start"
    break
  fi
  if [ -z "$stable_pid" ]; then
    stable_pid="$sample_pid"
  elif [ "$sample_pid" != "$stable_pid" ]; then
    verdict="BLOCK_PID_CHANGED"
    reason="appspawn-x PID changed during bounded start"
    break
  fi
  sleep 0.25
done

if device_online; then
  {
    dev "cat /proc/sys/kernel/random/boot_id; cat /proc/uptime; pidof appspawn-x || true"
    dev "ps -A -o PID,PPID,UID,NAME,CMDLINE | grep appspawn-x || true"
    dev "ls -lZ /dev/unix/socket/AppSpawnX 2>/dev/null || true"
    dev "grep AppSpawnX /proc/net/unix 2>/dev/null || true"
  } > "$OUT/post-start-state.txt" 2>&1
  dev "dmesg | grep -iE 'appspawn-x|JNI_CreateJavaVM|avc:.*denied|signal|SIGABRT|panic|watchdog' | tail -300" \
    > "$OUT/dmesg-post-start.txt" 2>&1 || true
  dev "hilog -x | tail -4000" > "$OUT/hilog-post-start.txt" 2>&1 || true

  boot_after="$(dev "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"
  if [ "$boot_after" != "$boot_before" ]; then
    verdict="BLOCK_BOOT_CHANGED"
    reason="boot ID changed during bounded start"
  fi

  if [ "$verdict" != "PASS_STABLE_10S" ]; then
    dev "begetctl stop_service appspawn-x 2>/dev/null || true"
  fi
fi

{
  echo "experiment: one-appspawn-parent-start"
  echo "verdict: $verdict"
  echo "risk: R1_REVERSIBLE_DEVICE_WRITE"
  echo "device_serial: $SERIAL"
  echo "boot_id_before: $boot_before"
  echo "stable_pid: '${stable_pid}'"
  echo "reason: $reason"
  echo "claim_boundary: APPSPAWN_PARENT_BOUNDED_START_ONLY"
} > "$OUT/START-VERDICT.yaml"

echo "$verdict: $reason"
[ "$verdict" = "PASS_STABLE_10S" ]
