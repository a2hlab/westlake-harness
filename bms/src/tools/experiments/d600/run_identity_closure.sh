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

"$BRIDGE_ROOT/tools/fn08_fn12_d600_readonly_baseline.sh" "$RUN_ID" "$SERIAL"

boot_before="$("$HDC_BIN" -t "$SERIAL" shell 'cat /proc/sys/kernel/random/boot_id' | tr -d '\r')"
pid_list="$("$HDC_BIN" -t "$SERIAL" shell 'pidof appspawn-x || true' | tr -d '\r')"
pid_count="$(echo "$pid_list" | awk '{print NF}')"

{
  echo "boot_id_before: $boot_before"
  echo "appspawn_pid_list: $pid_list"
  echo "appspawn_pid_count: $pid_count"
} > "$OUT/identity-precheck.txt"

if [ "$pid_count" -ne 1 ]; then
  {
    echo "experiment: E00"
    echo "verdict: BLOCK"
    echo "reason: expected exactly one appspawn-x PID"
  } > "$OUT/E00-VERDICT.yaml"
  echo "BLOCK: expected one appspawn-x PID, got '$pid_list'" >&2
  exit 1
fi

pid="$pid_list"
"$HDC_BIN" -t "$SERIAL" shell "
echo '## exe'
readlink /proc/$pid/exe
echo '## maps'
cat /proc/$pid/maps
" > "$OUT/appspawn-maps.txt" 2>&1

awk '$6 ~ /^\// {print $6}' "$OUT/appspawn-maps.txt" |
  sort -u |
  grep -E 'appspawn|android|art|bridge|hwui|skia|binder|datashare|hilog|hitrace' \
  > "$OUT/mapped-artifact-paths.txt" || true

map_hash_fail=0
: > "$OUT/mapped-artifact-sha256.txt"
while IFS= read -r path; do
  [ -n "$path" ] || continue
  case "$path" in
    *"'"*)
      echo "UNSAFE_PATH $path" >> "$OUT/mapped-artifact-sha256.txt"
      map_hash_fail=1
      continue
      ;;
  esac
  if ! "$HDC_BIN" -t "$SERIAL" shell \
      "test -f '$path' && sha256sum '$path'" \
      >> "$OUT/mapped-artifact-sha256.txt" 2>&1; then
    echo "UNHASHED $path" >> "$OUT/mapped-artifact-sha256.txt"
    map_hash_fail=1
  fi
done < "$OUT/mapped-artifact-paths.txt"

for required_path in \
  /system/bin/appspawn-x \
  /system/android/lib64/liboh_adapter_bridge.so \
  /system/android/lib64/liboh_android_runtime.so; do
  if ! grep -Fxq "$required_path" "$OUT/mapped-artifact-paths.txt" ||
     ! grep -Fq "  $required_path" "$OUT/mapped-artifact-sha256.txt"; then
    echo "MISSING_REQUIRED_MAP $required_path" \
      >> "$OUT/mapped-artifact-sha256.txt"
    map_hash_fail=1
  fi
done

boot_after="$("$HDC_BIN" -t "$SERIAL" shell 'cat /proc/sys/kernel/random/boot_id' | tr -d '\r')"
pid_after="$("$HDC_BIN" -t "$SERIAL" shell 'pidof appspawn-x || true' | tr -d '\r')"

verdict="PASS"
reason="single appspawn identity remained stable during read-only collection"
if [ "$boot_before" != "$boot_after" ] || [ "$pid_list" != "$pid_after" ]; then
  verdict="BLOCK"
  reason="boot ID or appspawn PID changed during collection"
elif [ "$map_hash_fail" -ne 0 ]; then
  verdict="BLOCK"
  reason="required mapped artifact path or SHA-256 receipt is incomplete"
fi

{
  echo "experiment: E00"
  echo "verdict: $verdict"
  echo "risk: R0_READ_ONLY"
  echo "device_serial: $SERIAL"
  echo "boot_id_before: $boot_before"
  echo "boot_id_after: $boot_after"
  echo "appspawn_pid_before: '$pid_list'"
  echo "appspawn_pid_after: '$pid_after'"
  echo "reason: $reason"
  echo "claim_boundary: DEVICE_GENERATION_IDENTITY_ONLY"
} > "$OUT/E00-VERDICT.yaml"

echo "$verdict: $reason"
test "$verdict" = "PASS"
