#!/bin/bash
set -euo pipefail

# Collects a read-only Fn08-Fn12 D600 baseline. It does not install/uninstall,
# clear hilog, stop/start processes, push files, or modify device configuration.

if [ "$#" -lt 2 ]; then
  echo "usage: $0 RUN_ID SERIAL [SERIAL ...]" >&2
  exit 2
fi

RUN_ID="$1"
shift
BRIDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
OUT_ROOT="$BRIDGE_ROOT/evidence/concepts/fn08-fn12-d600-early/$RUN_ID"

if [ ! -x "$HDC_BIN" ]; then
  echo "hdc is not executable: $HDC_BIN" >&2
  exit 2
fi

mkdir -p "$OUT_ROOT"

for serial in "$@"; do
  device_dir="$OUT_ROOT/$serial"
  mkdir -p "$device_dir"

  {
    echo "schema_version: '1.0'"
    echo "run_id: '$RUN_ID'"
    echo "device_serial: '$serial'"
    echo "collection_mode: READ_ONLY"
    echo "product_mutation: false"
    echo "device_mutation: false"
    echo "claim_boundary: EARLY_FACTS_NOT_ROUTE_VERDICT"
    echo "collected_at_utc: '$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
    echo "hdc_version: '$("$HDC_BIN" -v 2>&1 | head -1 | tr -d "\r" | sed "s/'/''/g")'"
  } > "$device_dir/MANIFEST.yaml"

  "$HDC_BIN" -t "$serial" shell '
echo "## software_version"
param get const.product.software.version
echo "## build_number"
param get const.product.build.number
echo "## boot_id"
cat /proc/sys/kernel/random/boot_id
echo "## uptime"
uptime
echo "## cpu"
grep -E "Hardware|Processor|model name" /proc/cpuinfo | head -8
echo "## memory"
grep -E "MemTotal|MemAvailable" /proc/meminfo
echo "## data"
df -h /data
echo "## appspawnx_pid"
pidof appspawn-x || true
echo "## helloworld_pid"
pidof com.example.helloworld || true
' > "$device_dir/device-state.txt" 2>&1

  "$HDC_BIN" -t "$serial" shell \
    'bm dump -n com.example.helloworld' \
    > "$device_dir/helloworld-bm-dump.txt" 2>&1 || true

  "$HDC_BIN" -t "$serial" shell '
for path in \
  /system/bin/appspawn-x \
  /system/lib64/liboh_adapter_bridge.so \
  /system/lib64/libandroid_runtime.so \
  /system/framework/framework.jar \
  /data/app/el1/bundle/public/com.example.helloworld/android/base.apk
do
  if [ -e "$path" ]; then
    ls -lZ "$path" 2>/dev/null || ls -l "$path"
    sha256sum "$path" 2>/dev/null || true
  else
    echo "MISSING $path"
  fi
done
' > "$device_dir/artifact-identity.txt" 2>&1

  "$HDC_BIN" -t "$serial" shell \
    'hilog -x 2>/dev/null | grep -Ei "AppSpawnX|AONB|AndroidRuntime|RenderService|AccessToken|DataShare|Trace" | tail -800' \
    > "$device_dir/relevant-hilog-tail.txt" 2>&1 || true
done

echo "PASS: collected read-only baseline at $OUT_ROOT"
