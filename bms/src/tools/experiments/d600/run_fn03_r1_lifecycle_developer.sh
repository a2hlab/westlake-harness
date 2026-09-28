#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 DEVICE_SERIAL [EXPECTED_RUNTIME_DIR]" >&2
  exit 2
fi

SERIAL="$1"
EXPECTED_RUNTIME_DIR="${2:-/opt/Bridge/.work/fn03-candidate-current-20260728-r31}"
ROOT="/opt/Bridge"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
SCREEN_CONTENT_CHECKER="$ROOT/tools/experiments/d600/check_screenshot_content.py"
PACKAGE="com.example.helloworld"
ACTIVITY="com.example.helloworld.MainActivity"
SHORT="${SERIAL:0:8}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$ROOT/evidence/runs/fn03-r1-lifecycle-developer-${SHORT}-${TS}"
REMOTE_SCREEN="/data/local/tmp/fn03-r1-lifecycle-${TS}.png"

mkdir -p "$OUT"

dev()
{
  "$HDC" -t "$SERIAL" shell "$1"
}

local_sha()
{
  shasum -a 256 "$1" | awk '{print $1}'
}

device_sha()
{
  dev "sha256sum '$1'" | awk '{print $1}' | tr -d '\r'
}

count_log()
{
  local pattern="$1"
  local file="$2"
  grep -cF "$pattern" "$file" 2>/dev/null || true
}

pid_exists()
{
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] &&
    [ "$(dev "test -d /proc/$pid && echo PRESENT || true" | tr -d '\r ')" = "PRESENT" ]
}

app_pid()
{
  local pid
  pid="$(dev "pidof $PACKAGE || true" | tr -d '\r ')"
  if pid_exists "$pid"; then
    printf '%s\n' "$pid"
    return 0
  fi

  # The current appspawn-x child keeps its Linux comm/argv as appspawn-x.
  # AppMS remains the authoritative package-to-process owner and exposes that
  # identity through aa dump.
  pid="$(
    dev "aa dump -a 2>/dev/null" |
    tr -d '\r' |
    awk -v package="$PACKAGE" '
      /process name \[/ {
        owner = index($0, "[" package "]") > 0
        next
      }
      owner && match($0, /pid #[0-9]+/) {
        value = substr($0, RSTART, RLENGTH)
        sub(/^pid #/, "", value)
        print value
        exit
      }
    '
  )"
  if pid_exists "$pid"; then
    printf '%s\n' "$pid"
  fi
}

appspawn_parent_pid()
{
  dev "ps -A -o PID,PPID,UID,NAME,ARGS" |
    tr -d '\r' |
    awk '$2 == 1 && $4 == "appspawn-x" { print $1; exit }'
}

stop_app_instance()
{
  local label="$1"
  local pid=""

  dev "aa force-stop $PACKAGE" >"$OUT/force-stop-$label.txt" 2>&1 || true
  for _ in $(seq 1 5); do
    pid="$(app_pid)"
    [ -z "$pid" ] && return 0
    sleep 1
  done

  # A stale appspawn-x child cannot be killed directly without leaving AppMS
  # and SceneBoard ownership behind. Uninstall/reinstall is also forbidden
  # here: it mutates Fn01 package prestate and can make a lifecycle test pass
  # for the wrong reason. Fail closed and require a fresh deploy/reboot.
  echo "cold_precondition_blocked_by_stale_pid=$pid" \
    >>"$OUT/force-stop-$label.txt"
  return 1
}

test -x "$HDC"
test -x "$SCREEN_CONTENT_CHECKER"
test -d "$EXPECTED_RUNTIME_DIR/system/android"
test -f "$EXPECTED_RUNTIME_DIR/system/android/lib64/libhwui.so"
test -f "$EXPECTED_RUNTIME_DIR/system/android/lib64/liboh_adapter_bridge.so"
test -f "$EXPECTED_RUNTIME_DIR/HelloWorld.apk"

expected_hwui="$(local_sha "$EXPECTED_RUNTIME_DIR/system/android/lib64/libhwui.so")"
expected_bridge="$(local_sha "$EXPECTED_RUNTIME_DIR/system/android/lib64/liboh_adapter_bridge.so")"
expected_apk="$(local_sha "$EXPECTED_RUNTIME_DIR/HelloWorld.apk")"

device_hwui="$(device_sha /system/android/lib64/libhwui.so)"
device_bridge="$(device_sha /system/android/lib64/liboh_adapter_bridge.so)"
device_apk="$(device_sha "/data/app/el1/bundle/public/$PACKAGE/android/base.apk")"

{
  echo "run_kind: FN03_R1_IMPLEMENTER_DEVICE_DEVELOPER_TEST"
  echo "formal_verdict_authorized: false"
  echo "device_serial: $SERIAL"
  echo "runtime_dir: $EXPECTED_RUNTIME_DIR"
  echo "package: $PACKAGE"
  echo "activity: $ACTIVITY"
  echo "expected_hwui_sha256: $expected_hwui"
  echo "device_hwui_sha256: $device_hwui"
  echo "expected_bridge_sha256: $expected_bridge"
  echo "device_bridge_sha256: $device_bridge"
  echo "expected_apk_sha256: $expected_apk"
  echo "device_apk_sha256: $device_apk"
  echo "started_at_utc: '$TS'"
} >"$OUT/MANIFEST.yaml"

if [ "$device_hwui" != "$expected_hwui" ] ||
   [ "$device_bridge" != "$expected_bridge" ] ||
   [ "$device_apk" != "$expected_apk" ]; then
  {
    echo "developer_verdict: BLOCK_ARTIFACT_IDENTITY_MISMATCH"
    echo "claim_boundary: IMPLEMENTER_DEVICE_TEST_ONLY"
  } >"$OUT/DEVELOPER-VERDICT.yaml"
  echo "BLOCK_ARTIFACT_IDENTITY_MISMATCH: $OUT"
  exit 1
fi

dev "
cat /proc/sys/kernel/random/boot_id
cat /proc/uptime
param get const.ohos.fullname
getenforce
begetctl start_service appspawn-x >/dev/null 2>&1 || true
pidof appspawn-x || true
mount | grep ' /system/android ' || true
bm dump -n $PACKAGE
" >"$OUT/preflight.txt" 2>&1

parent_before=""
for _ in $(seq 1 20); do
  parent_before="$(appspawn_parent_pid)"
  [ -n "$parent_before" ] && break
  sleep 1
done
if [ -z "$parent_before" ]; then
  {
    echo "developer_verdict: BLOCK_NO_APPSPAWN_X_PARENT"
    echo "claim_boundary: IMPLEMENTER_DEVICE_TEST_ONLY"
  } >"$OUT/DEVELOPER-VERDICT.yaml"
  echo "BLOCK_NO_APPSPAWN_X_PARENT: $OUT"
  exit 1
fi

dev "xargs -0 -n 1 < /proc/$parent_before/environ" \
  >"$OUT/appspawn-parent-environ.txt" 2>&1 || true
no_jit_count="$(
  count_log 'APPSPAWNX_NO_JIT=1' "$OUT/appspawn-parent-environ.txt"
)"
if [ "$no_jit_count" -ne 1 ]; then
  {
    echo "developer_verdict: BLOCK_NOT_TRUE_COLD_NO_JIT"
    echo "formal_action_verdict: NOT_ISSUED"
    echo "appspawn_x_pid: '$parent_before'"
    echo "appspawnx_no_jit_count: $no_jit_count"
    echo "claim_boundary: IMPLEMENTER_DEVICE_TEST_ONLY"
  } >"$OUT/DEVELOPER-VERDICT.yaml"
  echo "BLOCK_NOT_TRUE_COLD_NO_JIT: $OUT"
  exit 1
fi

if ! stop_app_instance before; then
  {
    echo "developer_verdict: BLOCK_CANNOT_ESTABLISH_PROCESS_COLD_PRECONDITION"
    echo "formal_action_verdict: NOT_ISSUED"
    echo "claim_boundary: IMPLEMENTER_DEVICE_TEST_ONLY"
  } >"$OUT/DEVELOPER-VERDICT.yaml"
  echo "BLOCK_CANNOT_ESTABLISH_PROCESS_COLD_PRECONDITION: $OUT"
  exit 1
fi
dev "hilog -r" >"$OUT/hilog-clear.txt" 2>&1 || true
dev "aa start -a $ACTIVITY -b $PACKAGE" >"$OUT/start-cold.txt" 2>&1 || true

app_pid=""
for second in $(seq 1 15); do
  app_pid="$(app_pid)"
  echo "$second ${app_pid:-ABSENT}" >>"$OUT/pid-samples-cold.txt"
  [ -n "$app_pid" ] && break
  sleep 1
done
sleep 5

dev "hilog -x" >"$OUT/hilog-cold.txt" 2>&1 || true
dev "ps -A -o PID,PPID,UID,NAME,ARGS | grep -E 'appspawn-x|$PACKAGE' || true" \
  >"$OUT/processes-cold.txt" 2>&1 || true

set +e
dev "snapshot_display -f $REMOTE_SCREEN -t png" >"$OUT/snapshot-command.txt" 2>&1
snapshot_rc=$?
"$HDC" -t "$SERIAL" file recv "$REMOTE_SCREEN" "$OUT/screen-cold.png" \
  >"$OUT/snapshot-recv.txt" 2>&1
snapshot_recv_rc=$?
dev "rm -f $REMOTE_SCREEN" >"$OUT/snapshot-cleanup.txt" 2>&1
set -e

screen_bytes=0
screen_content_rc=1
if [ -f "$OUT/screen-cold.png" ]; then
  screen_bytes="$(wc -c <"$OUT/screen-cold.png" | tr -d ' ')"
  set +e
  "$SCREEN_CONTENT_CHECKER" "$OUT/screen-cold.png" >"$OUT/screen-content.txt" 2>&1
  screen_content_rc=$?
  set -e
fi

oncreate_cold="$(count_log '=== MainActivity.onCreate() ===' "$OUT/hilog-cold.txt")"
onresume_cold="$(count_log '=== MainActivity.onResume() ===' "$OUT/hilog-cold.txt")"
fn04_present_cold="$(
  count_log 'FN04_A02_PRESENT_V1' "$OUT/hilog-cold.txt"
)"
typed_receipt_cold="$(
  count_log 'FN03_A10_TYPED_RECEIPT_V1' "$OUT/hilog-cold.txt"
)"
ack_success_cold="$(
  count_log 'FN03_A07_ACK_RESULT_V1 rc=0' "$OUT/hilog-cold.txt"
)"
oh_state5_cold="$(
  count_log "AbilityTransitionDone, ability:$PACKAGE/$ACTIVITY, state:5" \
    "$OUT/hilog-cold.txt"
)"
app_pid_after_cold="$(app_pid)"

background_executed=false
if [ -n "$app_pid_after_cold" ] && [ "$onresume_cold" -ge 1 ]; then
  background_executed=true
  # D600 uinput uses the OH keyboard key code; KEYCODE_HOME is 1.
  dev "uinput -K -d 1 -u 1" >"$OUT/home-key.txt" 2>&1 || true
  sleep 3
  dev "hilog -x" >"$OUT/hilog-background.txt" 2>&1 || true
  dev "aa start -a $ACTIVITY -b $PACKAGE" >"$OUT/start-resume.txt" 2>&1 || true
  sleep 3
  dev "hilog -x" >"$OUT/hilog-resume.txt" 2>&1 || true
else
  : >"$OUT/hilog-background.txt"
  : >"$OUT/hilog-resume.txt"
fi

onpause="$(count_log '=== MainActivity.onPause() ===' "$OUT/hilog-background.txt")"
onstop="$(count_log '=== MainActivity.onStop() ===' "$OUT/hilog-background.txt")"
onresume_after_background="$(count_log '=== MainActivity.onResume() ===' "$OUT/hilog-resume.txt")"
fn04_present_resume="$(
  count_log 'FN04_A02_PRESENT_V1' "$OUT/hilog-resume.txt"
)"
typed_receipt_resume="$(
  count_log 'FN03_A10_TYPED_RECEIPT_V1' "$OUT/hilog-resume.txt"
)"
ack_success_resume="$(
  count_log 'FN03_A07_ACK_RESULT_V1 rc=0' "$OUT/hilog-resume.txt"
)"
oh_state5_resume="$(
  count_log "AbilityTransitionDone, ability:$PACKAGE/$ACTIVITY, state:5" \
    "$OUT/hilog-resume.txt"
)"
parent_after="$(appspawn_parent_pid)"
app_pid_final="$(app_pid)"

dev "aa force-stop $PACKAGE" >"$OUT/force-stop-after.txt" 2>&1 || true
sleep 2
dev "hilog -x" >"$OUT/hilog-final.txt" 2>&1 || true

developer_verdict="PARTIAL_FIRST_WALL_CAPTURED"
reason="cold lifecycle did not reach a stable onCreate/onResume application state"
if [ "$oncreate_cold" -eq 1 ] &&
   [ "$onresume_cold" -ge 1 ] &&
   [ "$fn04_present_cold" -ge 1 ] &&
   [ "$typed_receipt_cold" -eq 1 ] &&
   [ "$ack_success_cold" -eq 1 ] &&
   [ "$oh_state5_cold" -eq 1 ] &&
   [ -n "$app_pid_after_cold" ] &&
   [ "$snapshot_rc" -eq 0 ] &&
   [ "$snapshot_recv_rc" -eq 0 ] &&
   [ "$screen_bytes" -gt 0 ] &&
   [ "$screen_content_rc" -eq 0 ] &&
   [ "$background_executed" = true ] &&
   [ "$onpause" -ge 1 ] &&
   [ "$onstop" -ge 1 ] &&
   [ "$onresume_after_background" -ge 1 ] &&
   [ "$fn04_present_resume" -ge 1 ] &&
   [ "$typed_receipt_resume" -eq 1 ] &&
   [ "$ack_success_resume" -eq 1 ] &&
   [ "$oh_state5_resume" -eq 1 ] &&
   [ "$parent_after" = "$parent_before" ]; then
  developer_verdict="DEVELOPER_LIFECYCLE_SMOKE_PASS"
  reason="true-cold no-JIT create/resume, typed APP_CONTENT receipt and ACK, HOME pause/stop, foreground resume, non-flat screenshot and stable parent observed"
fi

{
  echo "developer_verdict: $developer_verdict"
  echo "formal_action_verdict: NOT_ISSUED"
  echo "reason: $reason"
  echo "appspawn_x_pid_before: '$parent_before'"
  echo "appspawn_x_pid_after: '$parent_after'"
  echo "app_pid_after_cold: '$app_pid_after_cold'"
  echo "app_pid_final: '$app_pid_final'"
  echo "oncreate_cold_count: $oncreate_cold"
  echo "onresume_cold_count: $onresume_cold"
  echo "onpause_count: $onpause"
  echo "onstop_count: $onstop"
  echo "onresume_after_background_count: $onresume_after_background"
  echo "appspawnx_no_jit_count: $no_jit_count"
  echo "fn04_present_cold_count: $fn04_present_cold"
  echo "typed_receipt_cold_count: $typed_receipt_cold"
  echo "ack_success_cold_count: $ack_success_cold"
  echo "oh_state5_cold_count: $oh_state5_cold"
  echo "fn04_present_resume_count: $fn04_present_resume"
  echo "typed_receipt_resume_count: $typed_receipt_resume"
  echo "ack_success_resume_count: $ack_success_resume"
  echo "oh_state5_resume_count: $oh_state5_resume"
  echo "snapshot_rc: $snapshot_rc"
  echo "snapshot_recv_rc: $snapshot_recv_rc"
  echo "snapshot_bytes: $screen_bytes"
  echo "snapshot_content_rc: $screen_content_rc"
  echo "claim_boundary: IMPLEMENTER_DEVICE_TEST_ONLY"
} >"$OUT/DEVELOPER-VERDICT.yaml"

echo "$developer_verdict: $reason"
echo "Evidence=$OUT"
test "$developer_verdict" = "DEVELOPER_LIFECYCLE_SMOKE_PASS"
