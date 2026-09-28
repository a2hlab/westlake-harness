#!/usr/bin/env bash
set -euo pipefail

SERIAL=5cd1e3dd00000000000000000923012c
HDC=${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FRAMEWORK_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
OUT_DIR=${FN05_FN11_HARNESS_OUT:-"$FRAMEWORK_DIR/../../../.work/fn05-fn11-contract"}
LOCAL_BINARY="$OUT_DIR/fn05_fn11_contract_harness_ohos_arm64"
REMOTE_BINARY=/data/local/tmp/fn05_fn11_contract_harness

if [[ ! -x "$LOCAL_BINARY" ]]; then
  "$SCRIPT_DIR/run_fn05_fn11_contract_harness.sh"
fi

preflight=$("$HDC" -t "$SERIAL" shell \
  'printf "SERIAL_READY "; cat /proc/sys/kernel/random/boot_id' 2>&1)
if [[ "$preflight" != SERIAL_READY\ * ]]; then
  printf '%s\n' "$preflight" >&2
  exit 69
fi
printf '%s\n' "$preflight"

cleanup() {
  "$HDC" -t "$SERIAL" shell "rm -f '$REMOTE_BINARY'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

"$HDC" -t "$SERIAL" file send "$LOCAL_BINARY" "$REMOTE_BINARY"
"$HDC" -t "$SERIAL" shell "chmod 700 '$REMOTE_BINARY'"
"$HDC" -t "$SERIAL" shell "'$REMOTE_BINARY'"
