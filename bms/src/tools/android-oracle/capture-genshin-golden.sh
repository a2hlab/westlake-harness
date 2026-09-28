#!/usr/bin/env bash
# task #70 — Android golden-reference capture skeleton
# Goal: cold-launch Genshin on a real Android device through the in-game
# data-package download page, while recording:
#   - strace: openat / epoll_wait / eventfd / futex  (feeds #68 lib order + fix83)
#   - logcat: framework / ART / ActivityThread / Looper / JNI
#   - screenrecord: per-screen acceptance baseline for #66
#
# Event schema (order-only timestamps): seq,pid,tid,name,effect
#
# Usage:
#   export ANDROID_SERIAL=<serial>          # optional if one device
#   export ADB=${ADB:-adb}
#   export OUTDIR=${OUTDIR:-/tmp/task70-android/run-$(date +%Y%m%d-%H%M%S)}
#   export PKG=${PKG:-com.miHoYo.Yuanshen}
#   export ACTIVITY=${ACTIVITY:-com.miHoYo.GetMobileInfo.MainActivity}
#   bash src/tools/android-oracle/capture-genshin-golden.sh
#
# Root: strace attach needs root (or run-as / debuggable probe). Without root,
# this script still collects logcat + screenrecord + dumpsys; strace is skipped
# with a clear note.
set -euo pipefail

ADB="${ADB:-adb}"
PKG="${PKG:-com.miHoYo.Yuanshen}"
ACTIVITY="${ACTIVITY:-com.miHoYo.GetMobileInfo.MainActivity}"
OUTDIR="${OUTDIR:-/tmp/task70-android/run-$(date +%Y%m%d-%H%M%S)}"
DURATION_SEC="${DURATION_SEC:-180}"
SCREENRECORD_SEC="${SCREENRECORD_SEC:-120}"

if ! command -v "$ADB" >/dev/null 2>&1; then
  echo "FATAL: adb not found (set ADB=...)" >&2
  exit 2
fi

ADB_CMD=("$ADB")
if [[ -n "${ANDROID_SERIAL:-}" ]]; then
  ADB_CMD+=(-s "$ANDROID_SERIAL")
fi

mkdir -p "$OUTDIR"/{logcat,strace,screen,meta,events}
echo "OUTDIR=$OUTDIR"

{
  echo "time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "pkg=$PKG"
  echo "activity=$ACTIVITY"
  "${ADB_CMD[@]}" get-state || true
  "${ADB_CMD[@]}" shell getprop ro.build.version.release
  "${ADB_CMD[@]}" shell getprop ro.build.version.sdk
  "${ADB_CMD[@]}" shell getprop ro.product.model
  "${ADB_CMD[@]}" shell getprop ro.build.fingerprint
  "${ADB_CMD[@]}" shell 'id; which su; getenforce 2>/dev/null || true'
} | tee "$OUTDIR/meta/device.txt"

# Ensure package present
if ! "${ADB_CMD[@]}" shell pm path "$PKG" >/dev/null 2>&1; then
  echo "FATAL: package $PKG not installed. Install official APK first." >&2
  exit 3
fi

# Clear prior state for cold-ish launch
"${ADB_CMD[@]}" shell am force-stop "$PKG" || true
"${ADB_CMD[@]}" logcat -c || true

# Start logcat collectors
"${ADB_CMD[@]}" logcat -v threadtime '*:S' \
  ActivityManager:I ActivityTaskManager:I \
  AndroidRuntime:I art:I dalvikvm:I \
  System.err:W \
  -f /data/local/tmp/t70-logcat-framework.txt &
LOGCAT_FW_PID=$!
"${ADB_CMD[@]}" logcat -v threadtime >"$OUTDIR/logcat/all.txt" &
LOGCAT_ALL_PID=$!

# Screenrecord (device-side then pull)
"${ADB_CMD[@]}" shell "rm -f /data/local/tmp/t70-screen.mp4; screenrecord --time-limit $SCREENRECORD_SEC /data/local/tmp/t70-screen.mp4" &
SCREEN_PID=$!

# Launch
START_TS=$(date +%s)
"${ADB_CMD[@]}" shell am start -S -W -n "$PKG/$ACTIVITY" | tee "$OUTDIR/meta/am-start.txt" || true

# Resolve pid
sleep 2
PID=$("${ADB_CMD[@]}" shell pidof "$PKG" | tr -d '\r' | awk '{print $1}')
echo "pid=$PID" | tee "$OUTDIR/meta/pid.txt"

# strace if root available
ROOT_OK=0
if "${ADB_CMD[@]}" shell su -c id 2>/dev/null | grep -q 'uid=0'; then
  ROOT_OK=1
fi
echo "root_ok=$ROOT_OK" | tee -a "$OUTDIR/meta/device.txt"

if [[ "$ROOT_OK" == 1 && -n "${PID:-}" ]]; then
  # Follow openat/epoll/eventfd/futex only — keep volume manageable
  "${ADB_CMD[@]}" shell su -c \
    "timeout $DURATION_SEC strace -f -tt -s 256 -e trace=openat,open,epoll_wait,epoll_pwait,epoll_ctl,eventfd,eventfd2,futex,read,write -o /data/local/tmp/t70-strace.txt -p $PID" \
    >"$OUTDIR/strace/strace.stdout" 2>"$OUTDIR/strace/strace.stderr" || true
  "${ADB_CMD[@]}" pull /data/local/tmp/t70-strace.txt "$OUTDIR/strace/strace.txt" || true
else
  echo "strace skipped (need root + live pid). Collecting /proc maps instead." | tee "$OUTDIR/strace/SKIPPED.txt"
  if [[ -n "${PID:-}" ]]; then
    "${ADB_CMD[@]}" shell "cat /proc/$PID/maps" >"$OUTDIR/strace/maps.txt" || true
    "${ADB_CMD[@]}" shell "ls -l /proc/$PID/fd" >"$OUTDIR/strace/fds.txt" || true
  fi
  # Still wait so logcat/screen cover the download page window
  sleep "$DURATION_SEC"
fi

# Stop collectors
kill "$LOGCAT_ALL_PID" 2>/dev/null || true
"${ADB_CMD[@]}" shell "kill $LOGCAT_FW_PID 2>/dev/null || true" || true
wait "$SCREEN_PID" 2>/dev/null || true

"${ADB_CMD[@]}" pull /data/local/tmp/t70-logcat-framework.txt "$OUTDIR/logcat/framework.txt" || true
"${ADB_CMD[@]}" pull /data/local/tmp/t70-screen.mp4 "$OUTDIR/screen/session.mp4" || true
"${ADB_CMD[@]}" shell screencap -p /data/local/tmp/t70-final.png || true
"${ADB_CMD[@]}" pull /data/local/tmp/t70-final.png "$OUTDIR/screen/final.png" || true

# Derive coarse event stream from logcat (seq,pid,tid,name,effect)
python3 - <<'PY' "$OUTDIR/logcat/all.txt" "$OUTDIR/events/from-logcat.csv"
import csv, re, sys
src, dst = sys.argv[1], sys.argv[2]
pat = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+(\d+)\s+(\d+)\s+[A-Z]\s+([^\s:]+)\s*:\s*(.*)$')
keys = (
  'ActivityThread', 'Looper', 'MessageQueue', 'Zygote', 'Runtime',
  'dlopen', 'linker', 'ClassLoader', 'System.loadLibrary', 'nativePollOnce',
  'epoll', 'eventfd', 'Genshin', 'Yuanshen', 'miHoYo', 'Unity', 'Download',
)
seq = 0
with open(src, 'r', errors='replace') as f, open(dst, 'w', newline='') as out:
  w = csv.writer(out)
  w.writerow(['seq','ts','pid','tid','name','effect'])
  for line in f:
    m = pat.match(line.rstrip('\n'))
    if not m:
      continue
    ts, pid, tid, tag, msg = m.groups()
    blob = tag + ' ' + msg
    if not any(k.lower() in blob.lower() for k in keys):
      continue
    seq += 1
    effect = msg[:240].replace('\t', ' ')
    w.writerow([seq, ts, pid, tid, tag, effect])
print(f'wrote {seq} events -> {dst}')
PY

# openat order sketch from strace (if present)
if [[ -f "$OUTDIR/strace/strace.txt" ]]; then
  python3 - <<'PY' "$OUTDIR/strace/strace.txt" "$OUTDIR/events/dlopen-openat-order.txt"
import re, sys
src, dst = sys.argv[1], sys.argv[2]
# strace openat lines containing .so
pat = re.compile(r'openat\(.*?\"([^\"]+\.so[^\"]*)\"')
seen = []
with open(src, 'r', errors='replace') as f:
  for line in f:
    m = pat.search(line)
    if not m:
      continue
    path = m.group(1)
    if path not in seen:
      seen.append(path)
with open(dst, 'w') as out:
  for i, p in enumerate(seen, 1):
    out.write(f'{i}\t{p}\n')
print(f'unique .so openat paths: {len(seen)} -> {dst}')
PY
fi

END_TS=$(date +%s)
echo "elapsed_sec=$((END_TS-START_TS))" | tee "$OUTDIR/meta/elapsed.txt"
echo "DONE $OUTDIR"
ls -lhR "$OUTDIR" | head -80
