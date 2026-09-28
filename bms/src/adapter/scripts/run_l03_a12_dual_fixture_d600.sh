#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURE="$ROOT/out/app_native_loader_fixture"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
SERIAL="${D600_SERIAL:-5bb5b1ae00000000000000000823012c}"
RUN_ID="${ANL_RUN_ID:-$(date -u '+%Y%m%dT%H%M%SZ')}"
RESULT_DIR="${ANL_RESULT_DIR:-$ROOT/out/d600_a_anl_dual_$RUN_ID}"
TARGET_ROOT="/data/service/el1/public/westlake-anl-dual/$RUN_ID"
DEVICE_LOG="$RESULT_DIR/device.log"
COMMAND_LOG="$RESULT_DIR/commands.log"
READELF="${OH_READELF:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf}"

FILES=(
  anl_target_fixture
  dual_app/libanl_shadow.so
  dual_app/libanl_dual_root.so
  dual_app/libanl_denied_root.so
  dual_bridge/libanl_shadow.so
  dual_bridge/libanl_bridge_only.so
  dual_bridge/libanl_bridge_denied.so
)

mkdir -p "$RESULT_DIR"
: > "$DEVICE_LOG"
: > "$COMMAND_LOG"

record() {
  printf '%s\n' "$*" >> "$COMMAND_LOG"
}

remote() {
  record "hdc -t $SERIAL shell $1"
  "$HDC" -t "$SERIAL" shell "$1"
}

run_fixture() {
  local label="$1"
  local output rc
  local command="env -i PATH=/system/bin:/bin $TARGET_ROOT/bin/anl_target_fixture $TARGET_ROOT/app $TARGET_ROOT/bridge"
  record "$label: hdc -t $SERIAL shell $command"
  set +e
  output="$("$HDC" -t "$SERIAL" shell "$command; rc=\$?; echo __REMOTE_RC=\$rc; exit \$rc" 2>&1)"
  rc=$?
  set -e
  printf '%s_HOST_HDC_RC=%s\n%s\n' "$label" "$rc" "$output" >> "$DEVICE_LOG"
  printf '%s\n' "$output"
}

test -x "$HDC"
test -x "$READELF"
test -s "$FIXTURE/dual_target_manifest.sha256"
(
  cd "$FIXTURE"
  sha256sum -c dual_target_manifest.sha256
) > "$RESULT_DIR/host_manifest_check.log"
cp "$FIXTURE/dual_target_manifest.sha256" "$RESULT_DIR/host_manifest.sha256"
{
  "$READELF" -l "$FIXTURE/anl_target_fixture"
  sha256sum "$ROOT/out/d600_a_e_n0_20260711/ld-musl-aarch64.so.1"
} > "$RESULT_DIR/host_runner_elf.log"
grep -F '/lib/ld-musl-aarch64.so.1' "$RESULT_DIR/host_runner_elf.log" >/dev/null

record "hdc list targets"
"$HDC" list targets > "$RESULT_DIR/targets.txt"
grep -Fx "$SERIAL" "$RESULT_DIR/targets.txt" >/dev/null

BOOT_START="$(remote 'cat /proc/sys/kernel/random/boot_id' | tr -d '\r\n')"
ARCH="$(remote 'uname -m' | tr -d '\r\n')"
SELINUX="$(remote 'cat /sys/fs/selinux/enforce 2>/dev/null || getenforce' | tr -d '\r\n')"
test "$ARCH" = "aarch64"
printf 'BOOT_ID=%s\nARCH=%s\nSELINUX=%s\nTARGET_ROOT=%s\n' \
  "$BOOT_START" "$ARCH" "$SELINUX" "$TARGET_ROOT" >> "$DEVICE_LOG"

remote "readlink -f /lib/ld-musl-aarch64.so.1; sha256sum /lib/ld-musl-aarch64.so.1 /system/lib/ld-musl-aarch64.so.1; ls -l /lib/ld-musl-aarch64.so.1 /system/lib/ld-musl-aarch64.so.1" \
  | tr -d '\r' > "$RESULT_DIR/provider_identity.log"
grep -F '316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98' \
  "$RESULT_DIR/provider_identity.log" >/dev/null

GLOBAL_FIXTURES="$(remote "find /system/lib64 /system/android/lib64 -maxdepth 1 -name 'libanl_*' -print 2>/dev/null" | tr -d '\r')"
if [ -n "$GLOBAL_FIXTURES" ]; then
  printf 'unexpected global fixture providers:\n%s\n' "$GLOBAL_FIXTURES" >&2
  exit 1
fi

remote "test ! -e '$TARGET_ROOT'"
remote "mkdir -p '$TARGET_ROOT/bin' '$TARGET_ROOT/app' '$TARGET_ROOT/bridge'"
remote "chmod 0755 '$TARGET_ROOT' '$TARGET_ROOT/bin' '$TARGET_ROOT/app' '$TARGET_ROOT/bridge'"

for relative in "${FILES[@]}"; do
  source_file="$FIXTURE/$relative"
  case "$relative" in
    anl_target_fixture) target_file="$TARGET_ROOT/bin/$relative" ;;
    dual_app/*) target_file="$TARGET_ROOT/app/${relative#dual_app/}" ;;
    dual_bridge/*) target_file="$TARGET_ROOT/bridge/${relative#dual_bridge/}" ;;
  esac
  test -s "$source_file"
  record "hdc -t $SERIAL file send $source_file $target_file"
  "$HDC" -t "$SERIAL" file send "$source_file" "$target_file" >> "$COMMAND_LOG"
  remote "chmod 0755 '$target_file'"
  expected="$(sha256sum "$source_file" | awk '{print $1}')"
  actual="$(remote "sha256sum '$target_file'" | awk '{print $1}' | tr -d '\r\n')"
  if [ "$actual" != "$expected" ]; then
    printf 'device hash mismatch for %s: expected=%s actual=%s\n' \
      "$relative" "$expected" "$actual" >&2
    exit 1
  fi
  printf '%s  %s\n' "$actual" "$target_file" >> "$RESULT_DIR/device_manifest.sha256"
done

remote "find '$TARGET_ROOT' -mindepth 1 -maxdepth 2 -type f -print | sort" \
  | tr -d '\r' > "$RESULT_DIR/device_file_list.txt"
test "$(wc -l < "$RESULT_DIR/device_file_list.txt" | tr -d ' ')" = "7"
remote "ls -laZ '$TARGET_ROOT/bin' '$TARGET_ROOT/app' '$TARGET_ROOT/bridge' 2>/dev/null || ls -la '$TARGET_ROOT/bin' '$TARGET_ROOT/app' '$TARGET_ROOT/bridge'" \
  | tr -d '\r' > "$RESULT_DIR/device_file_metadata.log"

SHELL_ENV="$(remote 'env' | tr -d '\r')"
printf '%s\n' "$SHELL_ENV" > "$RESULT_DIR/shell_env.txt"
if printf '%s\n' "$SHELL_ENV" | grep -Eq '^LD_PRELOAD=|^LD_LIBRARY_PATH=.*westlake-anl'; then
  echo "fixture environment is globally contaminated" >&2
  exit 1
fi

FIRST="$(run_fixture RUN1)"
SECOND="$(run_fixture RUN2)"
printf '%s\n' "$FIRST" | grep -E \
  'ANL_DUAL_PASS value=0x4002 namespace=westlake\.anl\.app\.[0-9]+\.1 denied=1 denied_error=.*libanl_bridge_denied\.so' >/dev/null
printf '%s\n' "$SECOND" | grep -E \
  'ANL_DUAL_PASS value=0x4002 namespace=westlake\.anl\.app\.[0-9]+\.1 denied=1 denied_error=.*libanl_bridge_denied\.so' >/dev/null
printf '%s\n' "$FIRST" | grep -F '__REMOTE_RC=0' >/dev/null
printf '%s\n' "$SECOND" | grep -F '__REMOTE_RC=0' >/dev/null

remote "mv '$TARGET_ROOT/app/libanl_shadow.so' '$TARGET_ROOT/app/libanl_shadow.so.held'"
NEGATIVE="$(run_fixture NEGATIVE_NO_APP_SHADOW)"
printf '%s\n' "$NEGATIVE" | grep -F \
  'ANL_DUAL_FAIL stage=local-preferred value=0x5002 expected=0x4002' >/dev/null
printf '%s\n' "$NEGATIVE" | grep -F '__REMOTE_RC=13' >/dev/null
remote "mv '$TARGET_ROOT/app/libanl_shadow.so.held' '$TARGET_ROOT/app/libanl_shadow.so'"

APP_SHADOW_HOST="$(sha256sum "$FIXTURE/dual_app/libanl_shadow.so" | awk '{print $1}')"
APP_SHADOW_DEVICE="$(remote "sha256sum '$TARGET_ROOT/app/libanl_shadow.so'" | awk '{print $1}' | tr -d '\r\n')"
test "$APP_SHADOW_DEVICE" = "$APP_SHADOW_HOST"

BOOT_END="$(remote 'cat /proc/sys/kernel/random/boot_id' | tr -d '\r\n')"
test "$BOOT_END" = "$BOOT_START"
printf 'BOOT_ID_END=%s\nRESULT=PASS\n' "$BOOT_END" >> "$DEVICE_LOG"

remote "rm -rf '$TARGET_ROOT'"
remote "test ! -e '$TARGET_ROOT'"

(
  cd "$RESULT_DIR"
  sha256sum commands.log device.log device_manifest.sha256 device_file_list.txt \
    device_file_metadata.log host_manifest.sha256 host_manifest_check.log \
    host_runner_elf.log provider_identity.log shell_env.txt targets.txt \
    > EVIDENCE.sha256
)

printf 'ANL_D600_DUAL_PASS result_dir=%s boot_id=%s\n' "$RESULT_DIR" "$BOOT_START"
