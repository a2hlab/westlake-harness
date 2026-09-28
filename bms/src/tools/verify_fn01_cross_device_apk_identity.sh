#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  verify_fn01_cross_device_apk_identity.sh \
    --apk <frozen.apk> \
    --package <android.package> \
    --activity <fully.qualified.Activity> \
    --d600-serial <hdc-serial> \
    --android-serial <adb-serial> \
    --run-id <YYYYMMDDTHHMMSSZ-label>

The APK must already be installed on both devices. This command is read-only.
EOF
}

apk=""
package_name=""
activity_name=""
d600_serial=""
android_serial=""
run_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apk)
      apk="$2"
      shift 2
      ;;
    --package)
      package_name="$2"
      shift 2
      ;;
    --activity)
      activity_name="$2"
      shift 2
      ;;
    --d600-serial)
      d600_serial="$2"
      shift 2
      ;;
    --android-serial)
      android_serial="$2"
      shift 2
      ;;
    --run-id)
      run_id="$2"
      shift 2
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

if [[ -z "$apk" || -z "$package_name" || -z "$activity_name" ||
      -z "$d600_serial" || -z "$android_serial" || -z "$run_id" ]]; then
  usage >&2
  exit 2
fi
if [[ ! "$run_id" =~ ^[0-9]{8}T[0-9]{6}Z-[a-z0-9][a-z0-9._-]*$ ]]; then
  printf 'ERROR: invalid run id: %s\n' "$run_id" >&2
  exit 2
fi
if [[ ! -f "$apk" ]]; then
  printf 'ERROR: APK not found: %s\n' "$apk" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
apk="$(cd "$(dirname "$apk")" && pwd)/$(basename "$apk")"
hdc_bin="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
adb_bin="${ADB_BIN:-$(command -v adb)}"
android_sdk="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Library/Android/sdk}}"
aapt_bin="$(find "$android_sdk/build-tools" -type f -name aapt 2>/dev/null | sort -V | tail -1)"
aapt2_bin="$(find "$android_sdk/build-tools" -type f -name aapt2 2>/dev/null | sort -V | tail -1)"
apksigner_bin="$(find "$android_sdk/build-tools" -type f -name apksigner 2>/dev/null | sort -V | tail -1)"
run_dir="$repo_root/evidence/atoms/Fn01/A01/runs/$run_id-cross-device-apk-identity"
host_dir="$run_dir/host"
android_dir="$run_dir/android"
d600_dir="$run_dir/d600"

if [[ -e "$run_dir" ]]; then
  printf 'ERROR: evidence output already exists; choose a fresh run id: %s\n' \
    "$run_dir" >&2
  exit 2
fi
for tool in "$hdc_bin" "$adb_bin" "$aapt_bin" "$aapt2_bin" "$apksigner_bin"; do
  if [[ ! -x "$tool" ]]; then
    printf 'ERROR: required executable is missing: %s\n' "$tool" >&2
    exit 2
  fi
done

mkdir -p "$host_dir" "$android_dir" "$d600_dir"

host_sha="$(shasum -a 256 "$apk" | awk '{print $1}')"
printf '%s  %s\n' "$host_sha" "$apk" >"$host_dir/apk.sha256"
set +e
"$aapt_bin" dump badging "$apk" >"$host_dir/aapt-badging.txt" 2>&1
aapt_rc=$?
set -e
printf '%s\n' "$aapt_rc" >"$host_dir/aapt-badging.rc"
"$aapt2_bin" dump xmltree "$apk" --file AndroidManifest.xml \
  >"$host_dir/manifest-xmltree.txt" 2>&1
"$apksigner_bin" verify --verbose --print-certs "$apk" \
  >"$host_dir/apksigner.txt" 2>&1
unzip -Z1 "$apk" >"$host_dir/apk-entries.txt"

{
  while IFS= read -r entry; do
    case "$entry" in
      lib/arm64-v8a/*.so)
        entry_sha="$(unzip -p "$apk" "$entry" | shasum -a 256 | awk '{print $1}')"
        printf '%s  %s\n' "$entry_sha" "$entry"
        ;;
    esac
  done <"$host_dir/apk-entries.txt"
} >"$host_dir/arm64-native-entry-sha256.txt"

activity_manifest_name="${activity_name#"$package_name"}"
if [[ "$activity_manifest_name" == "$activity_name" ]]; then
  activity_manifest_name="$activity_name"
fi
grep -Fq "package=\"$package_name\"" "$host_dir/manifest-xmltree.txt"
grep -Fq "Raw: \"$activity_manifest_name\"" "$host_dir/manifest-xmltree.txt"

android_apk_path="$("$adb_bin" -s "$android_serial" shell pm path "$package_name" |
  tr -d '\r' | sed -n 's/^package://p' | head -1)"
if [[ -z "$android_apk_path" ]]; then
  printf 'ERROR: Android package is not installed: %s\n' "$package_name" >&2
  exit 1
fi
printf '%s\n' "$android_apk_path" >"$android_dir/installed-path.txt"
"$adb_bin" -s "$android_serial" shell "sha256sum '$android_apk_path'" \
  >"$android_dir/installed-base.sha256"
"$adb_bin" -s "$android_serial" shell "dumpsys package '$package_name'" \
  >"$android_dir/package-dump.txt"

d600_apk_path="/data/app/el1/bundle/public/$package_name/android/base.apk"
printf '%s\n' "$d600_apk_path" >"$d600_dir/installed-path.txt"
"$hdc_bin" -t "$d600_serial" shell "sha256sum '$d600_apk_path'" \
  >"$d600_dir/installed-base.sha256"
"$hdc_bin" -t "$d600_serial" shell "bm dump -n '$package_name'" \
  >"$d600_dir/package-dump.txt"

android_sha="$(awk '{print $1}' "$android_dir/installed-base.sha256")"
d600_sha="$(awk '{print $1}' "$d600_dir/installed-base.sha256")"

grep -Fq "$package_name" "$android_dir/package-dump.txt"
if ! grep -Fq "$activity_name" "$android_dir/package-dump.txt" &&
   ! grep -Fq "$package_name/$activity_manifest_name" "$android_dir/package-dump.txt"; then
  printf 'ERROR: Android package dump does not contain activity: %s\n' \
    "$activity_name" >&2
  exit 1
fi
grep -Fq "$package_name" "$d600_dir/package-dump.txt"
if ! grep -Fq "$activity_name" "$d600_dir/package-dump.txt" &&
   ! grep -Fq "$package_name/$activity_manifest_name" "$d600_dir/package-dump.txt"; then
  printf 'ERROR: D600 package dump does not contain activity: %s\n' \
    "$activity_name" >&2
  exit 1
fi

if [[ "$android_sha" != "$host_sha" || "$d600_sha" != "$host_sha" ]]; then
  {
    printf 'verdict=FAIL_APK_IDENTITY\n'
    printf 'host_sha256=%s\n' "$host_sha"
    printf 'android_sha256=%s\n' "$android_sha"
    printf 'd600_sha256=%s\n' "$d600_sha"
  } >"$run_dir/VERDICT.txt"
  printf 'FAIL: installed APK bytes differ; evidence=%s\n' "$run_dir" >&2
  exit 1
fi

{
  printf 'verdict=PASS_EXACT_APK_IDENTITY\n'
  printf 'claim_boundary=APK_BYTES_PACKAGE_ACTIVITY_AND_HOST_SIGNING_IDENTITY\n'
  printf 'package=%s\n' "$package_name"
  printf 'activity=%s\n' "$activity_name"
  printf 'host_sha256=%s\n' "$host_sha"
  printf 'android_sha256=%s\n' "$android_sha"
  printf 'd600_sha256=%s\n' "$d600_sha"
  printf 'android_serial=%s\n' "$android_serial"
  printf 'd600_serial=%s\n' "$d600_serial"
  printf 'note=Behavioral equivalence and visible-frame equivalence require separate runtime evidence.\n'
} >"$run_dir/VERDICT.txt"

(
  cd "$run_dir"
  find . -type f ! -name SHA256SUMS -print0 |
    sort -z |
    xargs -0 shasum -a 256 >SHA256SUMS
)

printf 'PASS_EXACT_APK_IDENTITY evidence=%s\n' "$run_dir"
