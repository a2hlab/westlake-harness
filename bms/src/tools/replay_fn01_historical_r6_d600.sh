#!/usr/bin/env bash

set -euo pipefail

usage() {
  printf '%s\n' \
    "Usage:" \
    "  $0 --hdc <path> --serial <d600-serial> \\" \
    "     --run-id <YYYYMMDDTHHMMSSZ-label> [--execute]"
}

hdc_bin=""
serial=""
run_id=""
execute=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hdc)
      hdc_bin="$2"
      shift 2
      ;;
    --serial)
      serial="$2"
      shift 2
      ;;
    --run-id)
      run_id="$2"
      shift 2
      ;;
    --execute)
      execute=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'ERROR: unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$hdc_bin" || -z "$serial" || -z "$run_id" ]]; then
  usage >&2
  exit 2
fi
if [[ ! -x "$hdc_bin" ]]; then
  printf 'ERROR: hdc is not executable: %s\n' "$hdc_bin" >&2
  exit 2
fi
if [[ ! "$run_id" =~ ^[0-9]{8}T[0-9]{6}Z-[a-z0-9][a-z0-9._-]*$ ]]; then
  printf 'ERROR: invalid run id: %s\n' "$run_id" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
historical_root="$repo_root/evidence/runs/helloworld-hanbing-v2-cfi-resource-r6-20260724"
artifact_root="$historical_root/artifacts"
apk="$artifact_root/HelloWorld.apk"
candidate_installer="$artifact_root/libapk_installer.so"
candidate_bms="$artifact_root/libbms.z.so"
candidate_installs="$artifact_root/libinstalls.z.so"

expected_apk="2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
expected_installer="a015fb78185b6490041e5ac8187ed87363e79517ccba7040c51f06a926d3e30c"
expected_bms="f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105"
expected_installs="2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0"
package_name="com.example.helloworld"
activity_name="com.example.helloworld.MainActivity"

out_dir="$repo_root/evidence/atoms/Fn01/A01/runs/$run_id-historical-r6-$serial"
host_dir="$out_dir/host"
device_dir="$out_dir/device"
backup_dir="$out_dir/backup"
if [[ -e "$out_dir" ]]; then
  printf 'ERROR: evidence output already exists; choose a fresh run id: %s\n' \
    "$out_dir" >&2
  exit 2
fi
mkdir -p "$host_dir" "$device_dir" "$backup_dir"

remote_root="/data/local/tmp/$run_id"
remote_backup="$remote_root/backup"
remote_stage="$remote_root/stage"
remote_apk="$remote_stage/HelloWorld.apk"

device() {
  "$hdc_bin" -t "$serial" shell "$1"
}

capture() {
  local output_path="$1"
  local rc_path="$2"
  shift 2
  set +e
  "$@" >"$output_path" 2>&1
  local command_rc=$?
  set -e
  printf '%s\n' "$command_rc" >"$rc_path"
  return 0
}

capture_device() {
  local name="$1"
  local command="$2"
  capture "$device_dir/$name.txt" "$device_dir/$name.rc" \
    "$hdc_bin" -t "$serial" shell "$command"
}

sha256_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

require_sha() {
  local path="$1"
  local expected="$2"
  local actual
  actual="$(sha256_file "$path")"
  if [[ "$actual" != "$expected" ]]; then
    printf 'ERROR: hash mismatch path=%s expected=%s actual=%s\n' \
      "$path" "$expected" "$actual" >&2
    exit 1
  fi
}

wait_device() {
  local attempt
  local probe
  for attempt in $(seq 1 100); do
    probe="$(device "cat /proc/sys/kernel/random/boot_id" 2>&1 || true)"
    if [[ -n "$probe" && "$probe" != *"[Fail]"* ]]; then
      return 0
    fi
    sleep 3
  done
  return 1
}

wait_platform_ready() {
  local attempt
  local probe
  for attempt in $(seq 1 100); do
    probe="$(device "param get bootevent.boot.completed; pidof accountmgr; pidof accesstoken_service; pidof foundation" 2>&1 || true)"
    if [[ "$probe" == *"true"* ]] &&
       [[ "$(printf '%s\n' "$probe" | grep -Ec '^[0-9]+([[:space:]][0-9]+)*$')" -ge 3 ]]; then
      # Preserve the original author's post-reboot settling interval after
      # boot-complete and the three required services are observable.
      sleep 12
      return 0
    fi
    sleep 3
  done
  return 1
}

mutated=0
completed=0

rollback() {
  local reason="$1"
  if [[ "$mutated" -ne 1 || "$completed" -eq 1 ]]; then
    return 0
  fi
  printf 'ROLLBACK: %s\n' "$reason" >&2
  set +e
  wait_device
  "$hdc_bin" -t "$serial" target mount
  device "mkdir -p $remote_stage/rollback"
  "$hdc_bin" -t "$serial" file send \
    "$backup_dir/libapk_installer.so" "$remote_stage/rollback/libapk_installer.so"
  "$hdc_bin" -t "$serial" file send \
    "$backup_dir/libbms.z.so" "$remote_stage/rollback/libbms.z.so"
  "$hdc_bin" -t "$serial" file send \
    "$backup_dir/libinstalls.z.so" "$remote_stage/rollback/libinstalls.z.so"
  device "cp $remote_stage/rollback/libapk_installer.so /system/lib64/libapk_installer.so"
  device "cp $remote_stage/rollback/libbms.z.so /system/lib64/libbms.z.so"
  device "cp $remote_stage/rollback/libinstalls.z.so /system/lib64/libinstalls.z.so"
  device "chown root:root /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
  device "chmod 0644 /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
  device "restorecon -F /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
  device "sync"
  "$hdc_bin" -t "$serial" target boot || true
  set -e
}

on_exit() {
  local rc=$?
  if [[ "$rc" -ne 0 ]]; then
    rollback "script rc=$rc"
  fi
}
trap on_exit EXIT

for path in "$apk" "$candidate_installer" "$candidate_bms" "$candidate_installs"; do
  if [[ ! -f "$path" ]]; then
    printf 'ERROR: missing historical artifact: %s\n' "$path" >&2
    exit 1
  fi
done

require_sha "$apk" "$expected_apk"
require_sha "$candidate_installer" "$expected_installer"
require_sha "$candidate_bms" "$expected_bms"
require_sha "$candidate_installs" "$expected_installs"

{
  printf '%s  %s\n' "$expected_apk" "$apk"
  printf '%s  %s\n' "$expected_installer" "$candidate_installer"
  printf '%s  %s\n' "$expected_bms" "$candidate_bms"
  printf '%s  %s\n' "$expected_installs" "$candidate_installs"
} >"$host_dir/historical-artifacts.sha256"

capture "$host_dir/file.txt" "$host_dir/file.rc" \
  file "$apk" "$candidate_installer" "$candidate_bms" "$candidate_installs"
capture "$host_dir/apk-entries.txt" "$host_dir/apk-entries.rc" unzip -Z1 "$apk"

apksigner_bin="$(find "$HOME/Library/Android/sdk/build-tools" -type f -name apksigner | sort -V | tail -1)"
if [[ -n "$apksigner_bin" ]]; then
  capture "$host_dir/apksigner.txt" "$host_dir/apksigner.rc" \
    "$apksigner_bin" verify --verbose --print-certs "$apk"
fi

capture "$device_dir/target-list.txt" "$device_dir/target-list.rc" \
  "$hdc_bin" list targets -v
capture_device "preflight-identity" \
  "uname -a; cat /proc/sys/kernel/random/boot_id; param get const.product.software.version; param get const.product.cpu.abilist; getenforce"
capture_device "preflight-package" "bm dump -n $package_name"
capture_device "preflight-system-libs" \
  "sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so; ls -lnZ /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"

if ! "$hdc_bin" list targets | grep -Fxq "$serial"; then
  printf 'ERROR: target is not online: %s\n' "$serial" >&2
  exit 1
fi
if ! grep -Fq "OpenHarmony 6.1.0.31" "$device_dir/preflight-identity.txt"; then
  printf 'ERROR: D600 firmware does not match OpenHarmony 6.1.0.31\n' >&2
  exit 1
fi
if grep -Fq "$package_name" "$device_dir/preflight-package.txt"; then
  printf 'ERROR: historical package is not clean-absent: %s\n' "$package_name" >&2
  exit 1
fi

{
  printf 'run_id=%s\n' "$run_id"
  printf 'serial=%s\n' "$serial"
  printf 'execute=%s\n' "$execute"
  printf 'package=%s\n' "$package_name"
  printf 'activity=%s\n' "$activity_name"
  printf 'historical_source_device=5583f5be00000000000000000323012c\n'
  printf 'historical_source_run=helloworld-hanbing-v2-cfi-resource-r6-20260724\n'
} >"$out_dir/inputs.env"

if [[ "$execute" -ne 1 ]]; then
  {
    printf 'result=PASS_HISTORICAL_R6_PRECHECK\n'
    printf 'claim_boundary=READ_ONLY_INPUT_DEVICE_AND_CLEAN_ABSENT_PREFLIGHT\n'
    printf 'formal_action_verdict=NOT_ISSUED\n'
    printf 'apk_sha256=%s\n' "$expected_apk"
    printf 'serial=%s\n' "$serial"
  } >"$out_dir/RESULT.txt"
  (
    cd "$out_dir"
    find . -type f ! -name SHA256SUMS -print0 |
      sort -z |
      xargs -0 shasum -a 256 >SHA256SUMS
  )
  printf 'PRECHECK PASS: add --execute to back up, deploy, reboot and install\n'
  printf 'EVIDENCE=%s\n' "$out_dir"
  completed=1
  exit 0
fi

"$hdc_bin" -t "$serial" target mount
device "mkdir -p $remote_backup $remote_stage"
device "cp /system/lib64/libapk_installer.so $remote_backup/libapk_installer.so"
device "cp /system/lib64/libbms.z.so $remote_backup/libbms.z.so"
device "cp /system/lib64/libinstalls.z.so $remote_backup/libinstalls.z.so"
capture_device "backup-device-libs" \
  "sha256sum $remote_backup/libapk_installer.so $remote_backup/libbms.z.so $remote_backup/libinstalls.z.so; ls -lnZ $remote_backup"

"$hdc_bin" -t "$serial" file recv \
  "$remote_backup/libapk_installer.so" "$backup_dir/libapk_installer.so"
"$hdc_bin" -t "$serial" file recv \
  "$remote_backup/libbms.z.so" "$backup_dir/libbms.z.so"
"$hdc_bin" -t "$serial" file recv \
  "$remote_backup/libinstalls.z.so" "$backup_dir/libinstalls.z.so"
shasum -a 256 "$backup_dir"/*.so >"$backup_dir/SHA256SUMS"

"$hdc_bin" -t "$serial" file send \
  "$candidate_installer" "$remote_stage/libapk_installer.so"
"$hdc_bin" -t "$serial" file send \
  "$candidate_bms" "$remote_stage/libbms.z.so"
"$hdc_bin" -t "$serial" file send \
  "$candidate_installs" "$remote_stage/libinstalls.z.so"
"$hdc_bin" -t "$serial" file send "$apk" "$remote_apk"

capture_device "stage-candidates" \
  "sha256sum $remote_stage/libapk_installer.so $remote_stage/libbms.z.so $remote_stage/libinstalls.z.so $remote_apk; ls -lnZ $remote_stage"
grep -Fq "$expected_installer" "$device_dir/stage-candidates.txt"
grep -Fq "$expected_bms" "$device_dir/stage-candidates.txt"
grep -Fq "$expected_installs" "$device_dir/stage-candidates.txt"
grep -Fq "$expected_apk" "$device_dir/stage-candidates.txt"

mutated=1
device "cp $remote_stage/libapk_installer.so /system/lib64/libapk_installer.so"
device "cp $remote_stage/libbms.z.so /system/lib64/libbms.z.so"
device "cp $remote_stage/libinstalls.z.so /system/lib64/libinstalls.z.so"
device "chown root:root /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
device "chmod 0755 /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
device "restorecon -F /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
capture_device "deployed-before-reboot" \
  "sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so; ls -lnZ /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
grep -Fq "$expected_installer" "$device_dir/deployed-before-reboot.txt"
grep -Fq "$expected_bms" "$device_dir/deployed-before-reboot.txt"
grep -Fq "$expected_installs" "$device_dir/deployed-before-reboot.txt"
device "sync"
capture "$device_dir/target-boot.txt" "$device_dir/target-boot.rc" \
  "$hdc_bin" -t "$serial" target boot

wait_device
wait_platform_ready
capture_device "post-reboot-readiness" \
  "param get bootevent.boot.completed; pidof accountmgr; pidof accesstoken_service; pidof foundation"
capture_device "post-reboot-identity" \
  "cat /proc/sys/kernel/random/boot_id; param get const.product.software.version; getenforce"
capture_device "post-reboot-system-libs" \
  "sha256sum /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so; ls -lnZ /system/lib64/libapk_installer.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so"
grep -Fq "$expected_installer" "$device_dir/post-reboot-system-libs.txt"
grep -Fq "$expected_bms" "$device_dir/post-reboot-system-libs.txt"
grep -Fq "$expected_installs" "$device_dir/post-reboot-system-libs.txt"

device "hilog -r"
capture_device "install" "bm install -p $remote_apk"
capture_device "package-dump" "bm dump -n $package_name"
capture_device "managed-layout" \
  "sha256sum /data/app/el1/bundle/public/$package_name/android/base.apk 2>/dev/null; find /data/app/el1/bundle/public/$package_name -maxdepth 5 -print 2>/dev/null | sort"
capture_device "hilog" \
  "hilog -x -v year -v time | grep -E '$package_name|Apk|APK|Bundle|BMS|Installd|installd|Install' | tail -4000"

if ! grep -Fq "install bundle successfully" "$device_dir/install.txt"; then
  printf 'ERROR: historical bm install did not report success\n' >&2
  exit 1
fi
if ! grep -Fq "$activity_name" "$device_dir/package-dump.txt"; then
  printf 'ERROR: package dump did not resolve historical activity\n' >&2
  exit 1
fi
if ! grep -Fq "$expected_apk" "$device_dir/managed-layout.txt"; then
  printf 'ERROR: managed base.apk hash does not match historical APK\n' >&2
  exit 1
fi

completed=1
trap - EXIT

(
  cd "$out_dir"
  find . -type f ! -name SHA256SUMS -print0 |
    sort -z |
    xargs -0 shasum -a 256 >SHA256SUMS
)

printf 'PASS: historical r6 install reproduced on %s\n' "$serial"
printf 'Evidence: %s\n' "$out_dir"
