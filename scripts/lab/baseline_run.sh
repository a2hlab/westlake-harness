#!/bin/bash
# Launch each app key on one OH board, one at a time, and record what a person watching the screen would see:
# a screenshot after WAIT seconds, whether the child is still alive, new faultlog entries and lifecycle markers.
# Usage: baseline_run.sh <serial> <framework-report (VM path)> <tag> <app-key>...
# Runs the manifest launcher inside VM a2hlab through tools/hdc_mac.sh; screenshots land in ~/.octos/outer/board/<tag>/.
set -u
S=$1; FW=$2; TAG=$3; shift 3
H=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
WAIT=${WAIT:-35}
SHOTS=~/.octos/outer/board/$TAG; mkdir -p "$SHOTS"
dev() { "$H" -t "$S" shell "$1" | LC_ALL=C tr -d '\r'; }

for key in "$@"; do
  # Leftovers from the previous app (parent and child are both named appspawn-x), then keep the screen awake:
  # the default 30 s screen-off brings the lock screen back over the app and every screenshot turns black.
  dev 'kill -9 $(pidof appspawn-x) 2>/dev/null; power-shell wakeup >/dev/null; power-shell timeout -o 86400000 >/dev/null' >/dev/null
  if dev "hidumper -s WindowManagerService -a '-a'" | grep -E '^SCBScreenLock' | grep -vqE ' -1 +0 +\['; then
    dev 'uinput -T -m 600 1500 600 300 400' >/dev/null
  fi
  before=$(dev 'ls /data/log/faultlog/temp/')
  extra=""
  [ "$key" = toutiao ] && extra="--android-native-target libvision_core.so --android-native-target libc++_shared.so"
  out=$(orb -m a2hlab bash -lc "W=/home/dspfac/a2hlab/source-closure/verify; cd ~/a2hlab/manifest && python3 tools/probe_source_app.py \
    --workspace \$W --westlake-source \$W/westlake --framework-report $FW --app-input ~/a2hlab/app-inputs/$key --app $key \
    --hdc /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh --serial $S --out ~/a2hlab/board/$S/$TAG/$key \
    --host-build \$W/out/signed-host --webview-input \$W/out/webview-input-source $extra 2>&1 | tail -3")
  spawned=$(printf '%s\n' "$out" | grep -o 'SOURCE_APP_SPAWNED.*')
  if [ -z "$spawned" ]; then
    printf '%-14s LAUNCH-FAILED %s\n' "$key" "$(printf '%s' "$out" | tail -1 | cut -c1-160)"; continue
  fi
  child=$(printf '%s' "$spawned" | sed -E 's/.*"child": ([0-9]+).*/\1/')
  runtime=$(printf '%s' "$spawned" | sed -E 's/.*"runtime": "([^"]+)".*/\1/')
  sleep "$WAIT"
  # OH can move the host ability to the background after launch; the app's sub-windows then drop to 0x0 and
  # every capture shows the desktop or black. Re-starting the running ability only brings it to the front.
  dev 'power-shell wakeup >/dev/null; aa start -b org.westlake.imehost -a EntryAbility >/dev/null; sleep 2'
  dev "snapshot_display -f /data/local/tmp/bl.jpeg >/dev/null"
  "$H" -t "$S" file recv /data/local/tmp/bl.jpeg "$SHOTS/$key.jpeg" >/dev/null
  log="$runtime/private-tmp/adapter_child_$child.stderr"
  alive=$(dev "[ -d /proc/$child ] && echo alive || echo dead")
  crash=$(comm -13 <(printf '%s\n' "$before" | sort) <(dev 'ls /data/log/faultlog/temp/' | sort) | tr '\n' ' ')
  bind=$(dev "grep -c 'sBindAppDone=true' $log 2>/dev/null")
  roots=$(dev "grep -c 'mAppVisible<-true' $log 2>/dev/null")
  fatal=$(dev "grep -m1 -E 'FATAL EXCEPTION|Fatal signal|UnsatisfiedLinkError' $log 2>/dev/null" | cut -c1-120)
  printf '%-14s child=%-6s %-5s bind=%s visible_roots=%s crash=[%s] %s\n' "$key" "$child" "$alive" "${bind:-0}" \
    "${roots:-0}" "$crash" "$fatal"
done
