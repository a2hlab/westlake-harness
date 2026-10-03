#!/bin/bash
# M2 A0 in-process ArkWeb probe: one board window (<= 30 min, typically ~8 min). Mac side, hdc.
#
#   run_a0.sh <serial> <new out dir> [modes]      modes default "0 1" (0 = default, 1 = single render process,
#                                                  2 = InitAndRun(false) via the bundle path, 4 = no ApplicationContext
#                                                  attach, 8 = no producer surface; bits combine)
#
# Board changes, all reverted before UNLOCK (trap): /data/local/tmp/a0probe.apk (pushed, removed), the test bundle
# org.westlake.a0probe (installed with bm, uninstalled), param debug.westlake.a0probe.mode (set per mode, reset to 0;
# debug.* is not persistent), the probe's own processes (stopped). Nothing under /system, no runtime/JAR/bridge/BCP
# change, no other bundle touched. Not via board_run.py: that tool requires a smoke spec and bms shards (a runtime
# deploy); this window installs one test APK and deploys nothing.
set -uo pipefail
SERIAL=${1:?serial}; OUT=${2:?new out dir}; MODES=${3:-0 1}
HERE=$(cd "$(dirname "$0")/.." && pwd)
WS=${WORKSPACES:-$HOME/orca/workspaces}
BOARD=$WS/westlake-harness/.octos/boards/app-lighting.md
NOTE=$WS/westlake-inputs/tools/board_note.sh
APK=$HERE/build/a0probe.apk
APK_SHA=d4d9556ff71f6bb8524fd12a1bcac6bb9a526980969026ff7620748c49343551
PKG=org.westlake.a0probe
LANE=${A0_LANE:-cc-t3}
H() { timeout "${T:-60}" hdc -t "$SERIAL" shell "$@"; }

[ -e "$OUT" ] && { echo "refusing: $OUT exists"; exit 2; }
[ "$(shasum -a 256 "$APK" | cut -d' ' -f1)" = "$APK_SHA" ] || { echo "APK hash mismatch"; exit 2; }
hdc list targets | grep -q "^$SERIAL$" || { echo "board $SERIAL not connected"; exit 3; }
held=$("$NOTE" held "$SERIAL" 2>/dev/null || true); [ -z "$held" ] || { echo "board held: $held"; exit 75; }
mkdir -p "$OUT"; exec > >(tee "$OUT/session.log") 2>&1
echo "[a0] start $(date -Iseconds) serial=$SERIAL modes=$MODES apk=$APK_SHA"

"$NOTE" lock "$BOARD" "$SERIAL" "$LANE" "M2 A0 ArkWeb probe: install test APK $PKG, run modes [$MODES], uninstall; <=30 min" || exit 75
START=$(date +%s)

rollback() {
  echo "[a0] rollback $(date -Iseconds)"
  H "param set debug.westlake.a0probe.mode 0" ; H "aa force-stop $PKG"
  uid=$(H "bm dump -n $PKG" 2>/dev/null | grep -m1 -E '"uid"' | grep -oE '[0-9]+' | head -1)
  if [ -n "${uid:-}" ]; then
    for pid in $(H "ps -A -o PID,USER" | grep -E " $uid *$" | sed 's/^ *//; s/ .*//'); do H "kill -15 $pid"; done
  fi
  T=180 H "bm uninstall -n $PKG"; H "rm -f /data/local/tmp/a0probe.apk /data/local/tmp/a0-*.jpeg"
  sleep 2
  left=$(H "bm dump -n $PKG" 2>&1 | grep -c '"bundleName"'); procs=$( [ -n "${uid:-}" ] && H "ps -A -o PID,USER" | grep -cE " $uid *$" || echo 0)
  echo "[a0] after rollback: bundle_entries=$left uid=${uid:-none} live_processes=$procs param=$(H 'param get debug.westlake.a0probe.mode')"
  [ "$left" = 0 ] && [ "${procs:-0}" = 0 ]
}
finish() {
  rc=$?; trap - EXIT INT TERM HUP
  if rollback; then "$NOTE" unlock "$BOARD" "$SERIAL" "$LANE"; echo "[a0] UNLOCKED after $(( $(date +%s) - START )) s"
  else echo "[a0] ROLLBACK INCOMPLETE: lock kept"; "$NOTE" progress "$BOARD" 90 "$LANE" "A0 probe rollback incomplete on $SERIAL; lock kept, see $OUT/session.log"; fi
  exit $rc
}
trap finish EXIT INT TERM HUP

echo "== read-only preflight"
H "param get const.ohos.fullname; uptime; cat /proc/sys/kernel/random/boot_id"
H "bm dump -n $PKG" | grep -q '"bundleName"' && { echo "[a0] $PKG already installed: leftover, stop"; exit 4; }
# the board libraries liba0probe.so was linked against (expected = link inputs, logs/hw248-r1-inputs-and-includes.txt)
H "for f in libarkweb_core_loader.z.so libapp_context.z.so libappexecfwk_base.z.so libeventhandler.z.so libsurface.z.so libsync_fence.z.so libbegetutil.z.so libutils.z.so libhilog.so libc++.so; do p=\$(find /system/lib64 -name \$f 2>/dev/null | head -1); echo \"\$(sha256sum \$p 2>/dev/null | cut -c1-16) \$p\"; done; sha256sum /data/app/el1/bundle/public/com.ohos.arkwebcore/libs/arm64/libarkweb_engine.so | cut -c1-16; pidof nwebspawn" | tee "$OUT/board-libs.txt"

echo "== install"
T=120 hdc -t "$SERIAL" file send "$APK" /data/local/tmp/a0probe.apk
T=180 H "bm install -p /data/local/tmp/a0probe.apk" | tee "$OUT/install.txt"
H "bm dump -n $PKG" > "$OUT/bm-dump.txt"; grep -q '"bundleName"' "$OUT/bm-dump.txt" || { echo "[a0] install failed"; exit 5; }

for mode in $MODES; do
  M=$OUT/mode-$mode; mkdir -p "$M"
  echo "== mode $mode ($(( $(date +%s) - START )) s into the window)"
  [ $(( $(date +%s) - START )) -gt 1500 ] && { echo "[a0] window budget reached, stop"; break; }
  H "aa force-stop $PKG" >/dev/null; sleep 1
  H "param set debug.westlake.a0probe.mode $mode"
  t0=$(H "date +%m-%d\ %H:%M:%S" | tr -d '\r')
  H "aa start -b $PKG -a $PKG.MainActivity" | tee "$M/aa-start.txt"
  sleep 28
  H "snapshot_display -f /data/local/tmp/a0-$mode.jpeg" >/dev/null; T=60 hdc -t "$SERIAL" file recv /data/local/tmp/a0-$mode.jpeg "$M/t28.jpeg" >/dev/null
  H "ps -A -o PID,PPID,USER,NAME" > "$M/ps.txt"
  T=120 H "hilog -x" > "$M/hilog-all.txt"
  grep -E "WL-A0|A0-JAVA|A0-SHIM|$PKG|ArkWeb|arkweb|NWEB|nweb|webview|nwebspawn|RenderProcess|StartRenderProcess" "$M/hilog-all.txt" | awk -v t="$t0" '$1" "$2 >= t' > "$M/hilog-a0.txt"
  grep -E "\[A0\] RESULT|\[A0-SHIM\]|\[A0-JAVA\]" "$M/hilog-a0.txt" | tail -3
  pid=$(grep -m1 -oE "\[A0\] S0 pid=[0-9]+" "$M/hilog-a0.txt" | grep -oE "[0-9]+$")
  [ -n "$pid" ] && grep -E "^ *[0-9]+ +($pid|[0-9]+) " "$M/ps.txt" | grep -iE "$PKG|render|arkweb|nweb" > "$M/processes.txt"
  echo "process rows:"; cat "$M/processes.txt" 2>/dev/null
  gzip -9 "$M/hilog-all.txt"
  grep -q "\[A0\] RESULT PASS" "$M/hilog-a0.txt" && { echo "[a0] PASS in mode $mode: stop"; break; }
done
echo "[a0] done $(date -Iseconds)"
