#!/usr/bin/env zsh
# auto_deploy_5583_654b.sh - Watcher that deploys the Bridge r18 runtime
# to D600 boards 5583 and 654B as soon as they come online after a reflash.
set -eu

ROOT=/opt/Bridge
STATE_DIR="$ROOT/.work/auto-deploy-state"
LOCK_DIR="$STATE_DIR/lock"
LOG="$STATE_DIR/watcher.log"
HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
DEPLOY_SCRIPT="$ROOT/tools/experiments/d600/deploy_fn01_fn03_r18_runtime_d600.sh"
TARGETS=(
  5583f5be00000000000000000323012c
  654b3a6b00000000000000000824012c
)

mkdir -p "$STATE_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

# Simple directory-based lock. Skip this cycle if another instance is running.
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$TS] another watcher instance is running; skip" >> "$LOG"
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

is_connected() {
  local serial="$1"
  "$HDC" list targets -v 2>/dev/null | awk -v s="$serial" '$1==s && $3=="Connected"{found=1} END{exit found?0:1}'
}

run_deploy() {
  local serial="$1"
  echo "[$TS] $serial transitioned to Connected; starting deploy" >> "$LOG"
  if zsh "$DEPLOY_SCRIPT" "$serial" >> "$LOG" 2>&1; then
    echo "[$TS] $serial deploy script finished" >> "$LOG"
  else
    echo "[$TS] $serial deploy script failed (see log above)" >> "$LOG"
  fi

  # Give appspawn-x/HelloWorld time to settle, then do a cheap health check.
  sleep 8
  local pid=""
  pid="$("$HDC" -t "$serial" shell pidof com.example.helloworld 2>/dev/null | tr -d '\r')" || true
  if [[ -n "$pid" ]]; then
    echo "[$TS] $serial HelloWorld pid=$pid OK" >> "$LOG"
  else
    echo "[$TS] $serial HelloWorld NOT RUNNING after deploy" >> "$LOG"
  fi
}

for serial in "${TARGETS[@]}"; do
  state_file="$STATE_DIR/$serial.state"
  prev="$(cat "$state_file" 2>/dev/null || echo offline)"
  if is_connected "$serial"; then
    if [[ "$prev" != "connected" ]]; then
      run_deploy "$serial"
      echo "connected" > "$state_file"
    else
      echo "[$TS] $serial already connected and deployed" >> "$LOG"
    fi
  else
    echo "[$TS] $serial offline" >> "$LOG"
    echo "offline" > "$state_file"
  fi
done
