#!/usr/bin/env bash
set -euo pipefail

# Deterministic E1/E3 runtime runner. It supports only the two explicit D600
# allowlist serials and never writes outside /data/local/tmp.

ALLOW_TARGET_61B0=61b0657200000000000000000324012c
ALLOW_TARGET_654B=654b3a6b00000000000000000824012c
PRIVATE_SA_ID=127233
EXPECTED_ARTIFACT_SHA256=842167d5f00037e97250e93d23e43d9be1dd87cc3f4bb196d214e24964bb7dad
HDC=${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
TARGET=${1:-}
ARTIFACT=${2:-}
RUN_ROOT=${3:-}

if [[ -z "$TARGET" || -z "$ARTIFACT" || -z "$RUN_ROOT" ]]; then
  echo "usage: $0 <allowlisted-serial> <artifact> <evidence-run-root>" >&2
  exit 64
fi
TARGET=$(printf '%s' "$TARGET" | tr '[:upper:]' '[:lower:]')
if [[ "$TARGET" == 5eab* ]]; then
  echo "REFUSE_5EAB target=$TARGET" >&2
  exit 65
fi
if [[ "$TARGET" != "$ALLOW_TARGET_61B0" &&
      "$TARGET" != "$ALLOW_TARGET_654B" ]]; then
  echo "REFUSE_NON_ALLOWLISTED_TARGET target=$TARGET" >&2
  exit 66
fi
if [[ ! -x "$HDC" ]]; then
  echo "HDC_NOT_EXECUTABLE path=$HDC" >&2
  exit 67
fi
if [[ ! -f "$ARTIFACT" ]]; then
  echo "ARTIFACT_NOT_FOUND path=$ARTIFACT" >&2
  exit 68
fi

RAW=$RUN_ROOT/raw
COMMANDS=$RUN_ROOT/COMMANDS.log
STATUS=$RUN_ROOT/step-status.tsv
if [[ -e "$RAW" ]] && find "$RAW" -mindepth 1 -print -quit | grep -q .; then
  echo "REFUSE_NONEMPTY_RAW path=$RAW" >&2
  exit 69
fi
mkdir -p "$RAW"
: >"$COMMANDS"
printf 'step\tlocal_rc\tremote_rc\texpectation\n' >"$STATUS"

artifact_sha=$(shasum -a 256 "$ARTIFACT" | awk '{print $1}')
if [[ "$artifact_sha" != "$EXPECTED_ARTIFACT_SHA256" ]]; then
  echo "ARTIFACT_SHA_MISMATCH actual=$artifact_sha expected=$EXPECTED_ARTIFACT_SHA256" >&2
  exit 70
fi

REMOTE_ARTIFACT="/data/local/tmp/fn01_topology_probe-${artifact_sha}"
REMOTE_SERVER_LOG="/data/local/tmp/fn01_topology_probe-${artifact_sha}.server.log"
REMOTE_STORE=/data/local/tmp/fn01_topology_probe_store
SERVER_PID=
CLEANUP_DONE=0

log_command()
{
  printf '[%s] ' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$COMMANDS"
  printf '%q ' "$@" >>"$COMMANDS"
  printf '\n' >>"$COMMANDS"
}

record_status()
{
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >>"$STATUS"
}

run_local_capture()
{
  local step=$1
  local output=$2
  shift 2
  log_command "$@"
  set +e
  "$@" >"$output" 2>&1
  local rc=$?
  set -e
  record_status "$step" "$rc" n/a "local rc=0"
  return "$rc"
}

run_remote_capture()
{
  local step=$1
  local output=$2
  local command=$3
  local wrapped="${command}; fn01_remote_rc=\$?; printf '\\n__FN01_REMOTE_RC=%s\\n' \"\$fn01_remote_rc\""
  log_command "$HDC" -t "$TARGET" shell "$wrapped"
  set +e
  "$HDC" -t "$TARGET" shell "$wrapped" >"$output" 2>&1
  local local_rc=$?
  set -e
  local remote_rc
  remote_rc=$(
    tr -d '\r' <"$output" |
      sed -n 's/^__FN01_REMOTE_RC=\([0-9][0-9]*\)$/\1/p' |
      tail -1
  )
  if [[ -z "$remote_rc" ]]; then
    remote_rc=missing
  fi
  record_status "$step" "$local_rc" "$remote_rc" "caller evaluates"
  printf '%s\n' "$remote_rc"
}

refresh_server_log()
{
  run_remote_capture server_log_snapshot "$RAW/server.log" \
    "if [ -f '$REMOTE_SERVER_LOG' ]; then cat '$REMOTE_SERVER_LOG'; else echo SERVER_LOG_MISSING; false; fi" \
    >/dev/null
}

cleanup()
{
  local original_rc=$?
  if [[ "$CLEANUP_DONE" == 1 ]]; then
    return "$original_rc"
  fi
  CLEANUP_DONE=1
  set +e

  if [[ -n "$SERVER_PID" && "$SERVER_PID" =~ ^[0-9]+$ ]]; then
    refresh_server_log
    run_remote_capture cleanup_term "$RAW/cleanup-term.log" \
      "if [ ! -d /proc/$SERVER_PID ]; then echo PROCESS_ALREADY_ABSENT pid=$SERVER_PID; elif [ \"\$(readlink /proc/$SERVER_PID/exe 2>/dev/null)\" = '$REMOTE_ARTIFACT' ]; then echo PROCESS_MATCH pid=$SERVER_PID; kill -TERM $SERVER_PID; else echo PID_IDENTITY_MISMATCH pid=$SERVER_PID exe=\"\$(readlink /proc/$SERVER_PID/exe 2>/dev/null)\"; false; fi" \
      >/dev/null
    local tries
    for tries in 1 2 3 4 5 6 7 8 9 10; do
      local process_state
      process_state=$(
        "$HDC" -t "$TARGET" shell \
          "if [ ! -d /proc/$SERVER_PID ]; then echo PROCESS_ABSENT; elif [ \"\$(readlink /proc/$SERVER_PID/exe 2>/dev/null)\" = '$REMOTE_ARTIFACT' ]; then echo PROCESS_MATCH; else echo PID_IDENTITY_MISMATCH; fi" \
          2>/dev/null
      )
      if [[ "$process_state" == *PROCESS_ABSENT* ]]; then
        break
      fi
      sleep 0.2
    done
    process_state=$(
      "$HDC" -t "$TARGET" shell \
        "if [ ! -d /proc/$SERVER_PID ]; then echo PROCESS_ABSENT; elif [ \"\$(readlink /proc/$SERVER_PID/exe 2>/dev/null)\" = '$REMOTE_ARTIFACT' ]; then echo PROCESS_MATCH; else echo PID_IDENTITY_MISMATCH; fi" \
        2>/dev/null
    )
    if [[ "$process_state" == *PROCESS_MATCH* ]]; then
      run_remote_capture cleanup_kill "$RAW/cleanup-kill.log" \
        "kill -KILL $SERVER_PID" >/dev/null
    fi
  fi

  if [[ -x "$ARTIFACT" ]]; then
    run_remote_capture post_sa_lookup "$RAW/post-sa-lookup.log" \
      "'$REMOTE_ARTIFACT' client 0 0" >/dev/null
  fi
  run_remote_capture post_state "$RAW/post-state.log" \
    "echo PROCESS; if [ -z '$SERVER_PID' ] || [ ! -d /proc/$SERVER_PID ]; then echo PROCESS_ABSENT pid=$SERVER_PID; elif [ \"\$(readlink /proc/$SERVER_PID/exe 2>/dev/null)\" = '$REMOTE_ARTIFACT' ]; then echo PROCESS_MATCH_STILL_PRESENT pid=$SERVER_PID; false; else echo PID_REUSED_BY_OTHER_PROCESS pid=$SERVER_PID; fi; echo SA_$PRIVATE_SA_ID; hidumper -s $PRIVATE_SA_ID 2>&1; echo LIST_MATCH; hidumper -ls 2>&1 | grep -E '(^|[^0-9])$PRIVATE_SA_ID([^0-9]|\$)' || true" \
    >/dev/null
  run_remote_capture cleanup_files "$RAW/cleanup-files.log" \
    "rm -f '$REMOTE_ARTIFACT' '$REMOTE_SERVER_LOG' '$REMOTE_STORE/recovery.complete' '$REMOTE_STORE/lease.lock'; rmdir '$REMOTE_STORE' 2>/dev/null || true; if [ -e '$REMOTE_ARTIFACT' ] || [ -e '$REMOTE_SERVER_LOG' ]; then echo CLEANUP_FILE_PRESENT; false; else echo CLEANUP_FILES_ABSENT; fi" \
    >/dev/null
  run_remote_capture final_state "$RAW/final-state.log" \
    "echo ARTIFACT; [ ! -e '$REMOTE_ARTIFACT' ] && echo ARTIFACT_ABSENT; echo PROCESS; if [ -z '$SERVER_PID' ] || [ ! -d /proc/$SERVER_PID ]; then echo PROCESS_ABSENT pid=$SERVER_PID; elif [ \"\$(readlink /proc/$SERVER_PID/exe 2>/dev/null)\" = '$REMOTE_ARTIFACT' ]; then echo PROCESS_MATCH_STILL_PRESENT pid=$SERVER_PID; false; else echo PID_REUSED_BY_OTHER_PROCESS pid=$SERVER_PID; fi; echo SA_$PRIVATE_SA_ID; hidumper -s $PRIVATE_SA_ID 2>&1; echo LIST_MATCH; hidumper -ls 2>&1 | grep -E '(^|[^0-9])$PRIVATE_SA_ID([^0-9]|\$)' || true" \
    >/dev/null

  set -e
  return "$original_rc"
}
trap cleanup EXIT INT TERM

run_local_capture hdc_version "$RAW/hdc-version.log" "$HDC" -v
run_local_capture target_list "$RAW/target-list.log" "$HDC" list targets -v
if ! grep -F "$TARGET" "$RAW/target-list.log" | grep -F 'Connected' >/dev/null; then
  echo "TARGET_NOT_CONNECTED target=$TARGET" >&2
  exit 71
fi

{
  printf 'target=%s\n' "$TARGET"
  printf 'private_sa_id=%s\n' "$PRIVATE_SA_ID"
  printf 'artifact_local=%s\n' "$ARTIFACT"
  printf 'artifact_sha256=%s\n' "$artifact_sha"
  printf 'artifact_size=%s\n' "$(stat -f %z "$ARTIFACT")"
  printf 'remote_artifact=%s\n' "$REMOTE_ARTIFACT"
  printf 'runner_sha256=%s\n' "$(shasum -a 256 "$0" | awk '{print $1}')"
  printf 'run_started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$RAW/generation-binding.env"

run_remote_capture device_binding "$RAW/device-binding.log" \
  "echo TARGET='$TARGET'; echo BOOT_ID; cat /proc/sys/kernel/random/boot_id; printf '\\n'; echo SOFTWARE; param get const.product.software.version; echo SERIAL; param get ohos.boot.sn; echo PRODUCT; param get const.product.name; echo KERNEL; uname -a; echo SELINUX_ENFORCE; cat /sys/fs/selinux/enforce; printf '\\n'; echo SHELL_IDENTITY; id; cat /proc/self/attr/current; printf '\\n'; echo RUNTIME_LIBS; sha256sum /system/lib64/platformsdk/libsamgr_proxy.z.so /system/lib64/platformsdk/libsamgr_common.z.so /system/lib64/platformsdk/libipc_single.z.so /system/lib64/platformsdk/libutils.z.so /system/lib64/chipset-sdk-sp/libc++.so /system/lib/ld-musl-aarch64.so.1" \
  >/dev/null
grep -F "$TARGET" "$RAW/device-binding.log" >/dev/null
grep -F 'OpenHarmony 6.1.0.31' "$RAW/device-binding.log" >/dev/null
boot_id=$(
  tr -d '\r' <"$RAW/device-binding.log" |
    awk '/^BOOT_ID$/{getline; print; exit}'
)
if [[ ! "$boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
  echo "BOOT_ID_INVALID value=$boot_id" >&2
  exit 83
fi
printf '%s\n' "$boot_id" >"$RAW/boot-id.txt"
enforce_value=$(
  tr -d '\r' <"$RAW/device-binding.log" |
    awk '/^SELINUX_ENFORCE$/{getline; gsub(/[[:space:]]/, ""); print; exit}'
)
if [[ "$enforce_value" != 1 ]]; then
  echo "SELINUX_NOT_ENFORCING value=$enforce_value" >&2
  exit 86
fi
grep -F 'a97fe3dc89365d6e37b44cd130aaf89f3ea30f788f1039301a9bd169d205a107  /system/lib64/platformsdk/libsamgr_proxy.z.so' "$RAW/device-binding.log" >/dev/null
grep -F 'bb919eb31e6f1b1e58f6578619724fdb1d0d6cf79c1f42a32435b335e3cad51f  /system/lib64/platformsdk/libsamgr_common.z.so' "$RAW/device-binding.log" >/dev/null
grep -F 'f6742ea92c89d4400d69201ec5ac47261dcfeb0945951ecc5ae44041ff6bd4f8  /system/lib64/platformsdk/libipc_single.z.so' "$RAW/device-binding.log" >/dev/null
grep -F '66bdf65d494437eae03b4cb4a6f277e65f1832de5d79634d350d01b69e079d1a  /system/lib64/platformsdk/libutils.z.so' "$RAW/device-binding.log" >/dev/null
grep -F '9466fb0d933689533bdf4b4962907f3e0c0970be278bd6ccf703ffa2aea838a6  /system/lib64/chipset-sdk-sp/libc++.so' "$RAW/device-binding.log" >/dev/null
grep -F 'fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2  /system/lib/ld-musl-aarch64.so.1' "$RAW/device-binding.log" >/dev/null

client_identity_rc=$(run_remote_capture client_identity \
  "$RAW/client-identity.log" "id -u")
client_uid=$(
  tr -d '\r' <"$RAW/client-identity.log" |
    sed -n '/^[0-9][0-9]*$/p' |
    head -1
)
if [[ "$client_identity_rc" != 0 || ! "$client_uid" =~ ^[0-9]+$ ]]; then
  echo "CLIENT_UID_INVALID value=$client_uid remote_rc=$client_identity_rc" >&2
  exit 85
fi
printf '%s\n' "$client_uid" >"$RAW/client-uid.txt"

run_remote_capture baseline_sa "$RAW/baseline-sa.log" \
  "echo HIDUMPER_$PRIVATE_SA_ID; hidumper -s $PRIVATE_SA_ID 2>&1; echo HIDUMPER_LIST_MATCH; hidumper -ls 2>&1 | grep -E '(^|[^0-9])$PRIVATE_SA_ID([^0-9]|\$)' || true; echo ARTIFACT_BASELINE; if [ -e '$REMOTE_ARTIFACT' ] || [ -e '$REMOTE_SERVER_LOG' ]; then echo STALE_ARTIFACT_PRESENT; false; else echo ARTIFACT_ABSENT; fi" \
  >/dev/null
if grep -E "$PRIVATE_SA_ID|STALE_ARTIFACT_PRESENT" "$RAW/baseline-sa.log" |
  grep -v -E "HIDUMPER_$PRIVATE_SA_ID|__FN01_REMOTE_RC" >/dev/null; then
  echo "SA_OR_ARTIFACT_BASELINE_NOT_EMPTY" >&2
  exit 72
fi

run_local_capture artifact_send "$RAW/artifact-send.log" \
  "$HDC" -t "$TARGET" file send "$ARTIFACT" "$REMOTE_ARTIFACT"
run_remote_capture artifact_verify "$RAW/artifact-verify.log" \
  "chmod 0755 '$REMOTE_ARTIFACT'; sha256sum '$REMOTE_ARTIFACT'; ls -l '$REMOTE_ARTIFACT'" \
  >/dev/null
grep -F "$artifact_sha  $REMOTE_ARTIFACT" "$RAW/artifact-verify.log" >/dev/null

prelookup_rc=$(run_remote_capture pre_sa_lookup "$RAW/pre-sa-lookup.log" \
  "'$REMOTE_ARTIFACT' client 0 0")
if [[ "$prelookup_rc" != 41 ]] ||
  ! grep -F "CLIENT_SA_LOOKUP_FAIL sa_id=$PRIVATE_SA_ID" "$RAW/pre-sa-lookup.log" >/dev/null; then
  echo "PRIVATE_SA_PRELOOKUP_NOT_ABSENT sa_id=$PRIVATE_SA_ID remote_rc=$prelookup_rc" >&2
  exit 73
fi

start_command="setsid '$REMOTE_ARTIFACT' server >'$REMOTE_SERVER_LOG' 2>&1 </dev/null & server_pid=\$!; echo SERVER_PID=\$server_pid"
start_rc=$(run_remote_capture server_start "$RAW/server-start.log" "$start_command")
if [[ "$start_rc" != 0 ]]; then
  echo "SERVER_START_SHELL_FAIL remote_rc=$start_rc" >&2
  exit 74
fi
SERVER_PID=$(
  tr -d '\r' <"$RAW/server-start.log" |
    sed -n 's/^SERVER_PID=\([0-9][0-9]*\)$/\1/p' |
    tail -1
)
if [[ ! "$SERVER_PID" =~ ^[0-9]+$ ]]; then
  echo "SERVER_PID_INVALID value=$SERVER_PID" >&2
  exit 75
fi

for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  refresh_server_log
  if grep -q '^SA_ADD_RESULT ' "$RAW/server.log"; then
    break
  fi
  sleep 0.2
done
if ! grep -q '^SA_ADD_RESULT ' "$RAW/server.log"; then
  echo "SA_ADD_RESULT_NOT_OBSERVED pid=$SERVER_PID" >&2
  exit 76
fi

recovery_line=$(grep -n '^RECOVERY_COMPLETE ' "$RAW/server.log" | cut -d: -f1 | head -1)
add_line=$(grep -n '^SA_ADD_RESULT ' "$RAW/server.log" | cut -d: -f1 | head -1)
add_status=$(sed -n 's/^SA_ADD_RESULT .* status=\(-\{0,1\}[0-9][0-9]*\) .*/\1/p' "$RAW/server.log" | head -1)
{
  printf 'recovery_line=%s\n' "$recovery_line"
  printf 'sa_add_line=%s\n' "$add_line"
  printf 'sa_add_status=%s\n' "$add_status"
} >"$RAW/order-check.env"
if [[ -z "$recovery_line" || -z "$add_line" || "$recovery_line" -ge "$add_line" ]]; then
  echo "RECOVERY_REGISTRATION_ORDER_FAIL recovery=$recovery_line add=$add_line" >&2
  exit 77
fi
if [[ "$add_status" != 0 ]]; then
  run_remote_capture selinux_first_wall "$RAW/selinux-first-wall.log" \
    "hilog -x 2>&1 | grep -E 'avc: denied|SA_SELINUX|AddSystemAbility|$PRIVATE_SA_ID' | tail -200" \
    >/dev/null
  echo "OBSERVED_WALL_ADD_SYSTEM_ABILITY status=$add_status" >&2
  exit 31
fi

for attempt in 1 2 3 4 5 6 7 8 9 10; do
  refresh_server_log
  if grep -q '^SERVER_READY ' "$RAW/server.log"; then
    break
  fi
  sleep 0.2
done
ready_line=$(grep -n '^SERVER_READY ' "$RAW/server.log" | cut -d: -f1 | head -1)
bms_line=$(grep -n '^BMS_READ_ONLY ' "$RAW/server.log" | cut -d: -f1 | head -1)
if [[ -z "$ready_line" || "$add_line" -ge "$ready_line" ]]; then
  echo "SA_READY_ORDER_FAIL add=$add_line ready=$ready_line" >&2
  exit 78
fi
if [[ -z "$bms_line" ]]; then
  echo "BMS_LAYERED_RESULT_MISSING" >&2
  exit 79
fi

second_rc=$(run_remote_capture second_server "$RAW/second-server.log" \
  "'$REMOTE_ARTIFACT' server")
if [[ "$second_rc" != 23 ]] ||
  ! grep -F 'STORE_LEASE_BUSY' "$RAW/second-server.log" >/dev/null; then
  echo "SECOND_SERVER_LEASE_EXPECTATION_FAIL remote_rc=$second_rc" >&2
  exit 80
fi

honest_rc=$(run_remote_capture honest_client "$RAW/honest-client.log" \
  "'$REMOTE_ARTIFACT' client '$client_uid' 0")
if [[ "$honest_rc" != 0 ]] ||
  ! grep -F 'claim_matches_peer=1' "$RAW/honest-client.log" >/dev/null; then
  echo "HONEST_CLIENT_FAIL remote_rc=$honest_rc" >&2
  exit 81
fi

forged_rc=$(run_remote_capture forged_client "$RAW/forged-client.log" \
  "'$REMOTE_ARTIFACT' client '$((client_uid + 1))' 0")
if [[ "$forged_rc" != 44 ]] ||
  ! grep -F 'CLIENT_CLAIM_REJECTED' "$RAW/forged-client.log" >/dev/null; then
  echo "FORGED_CLIENT_EXPECTATION_FAIL remote_rc=$forged_rc" >&2
  exit 82
fi

forged_user_rc=$(run_remote_capture forged_user_client \
  "$RAW/forged-user-client.log" \
  "'$REMOTE_ARTIFACT' client '$client_uid' 1")
if [[ "$forged_user_rc" != 44 ]] ||
  ! grep -F 'CLIENT_CLAIM_REJECTED' \
    "$RAW/forged-user-client.log" >/dev/null; then
  echo "FORGED_USER_EXPECTATION_FAIL remote_rc=$forged_user_rc" >&2
  exit 84
fi

refresh_server_log
printf 'RUNTIME_SEQUENCE_COMPLETE pid=%s\n' "$SERVER_PID"
