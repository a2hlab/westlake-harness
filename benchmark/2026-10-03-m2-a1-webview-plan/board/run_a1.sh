#!/bin/bash
# M2 A1 real-WebView window (<= 30 min). Mac side, hdc. Installs the A1 WebView test APK (org.westlake.a1webview, a real
# android.webkit.WebView), overlays cc-wiki's route-a WebView provider for the window, launches (data: page or a URL),
# captures t28, then rolls EVERYTHING back before UNLOCK.
#
#   run_a1.sh <serial> <new out dir> [url]   url empty -> the #12ab34 data: page; else loadUrl(url) (Wikipedia window)
#
# Overlays (bind-mount for the window; cc-wiki artifacts, SHA-pinned):
#   - oh-adapter-runtime.jar : bind-mount OVER the EXISTING deployed jar (non-BCP, PathClassLoader). Its ORIGINAL SHA is
#     recorded after lock; umount restores it; the real jar is NEVER rm'd (only our overlay source under /data/local/tmp).
#   - shim .so  : /system/android/lib64/<shim>.so (B7BindFixes System.load). Absent on a clean board -> create/mount/rm.
#   - worker .so: /data/local/tmp/<worker>.so (shim dlopen_ns).
# runtime-fingerprint after lock == before unlock (else keep the lock). Nothing under /system persists; no BCP/boot change.
#
# cc-wiki fills OVERLAY filenames + *_SHA below when the artifacts land; until then the placeholder guard refuses to run.
set -uo pipefail
SERIAL=${1:?serial}; OUT=${2:?new out dir}; URL=${3:-}
HERE=$(cd "$(dirname "$0")/.." && pwd)
WS=${WORKSPACES:-$HOME/orca/workspaces}
BOARD=$WS/westlake-harness/.octos/boards/app-lighting.md
NOTE=$WS/westlake-inputs/tools/board_note.sh
APK=$HERE/build/a1webview.apk
APK_SHA=a45631ab4f4407cf093bcd16527004247878a158c67315e58c6c9f60481b8552   # a1webview.apk (real WebView, no app native)
PKG=org.westlake.a1webview
LANE=${A1_LANE:-cc-t3}
RT_REF=/system/android/lib64/libwestlake_jni_gapfill.so            # an existing deployed lib, for the SELinux context

# ---- cc-wiki route-a WebView provider overlays (FILL names + SHAs when artifacts land) ----
JAR_SRC=$HERE/build/overlay/oh-adapter-runtime.jar
JAR_TARGET=/system/android/framework/oh-adapter-runtime.jar
JAR_PUSH=/data/local/tmp/oh-adapter-runtime.jar                    # writable bind-mount source (labelled like deployed)
JAR_SHA=${A1_JAR_SHA:-TBD_CCWIKI}                                  # SHA of the candidate oh-adapter-runtime.jar
SHIM_SRC=$HERE/build/overlay/libwl_a1_webview.so                   # cc-wiki shim filename (adjust to the delivered name)
SHIM_TARGET=/system/android/lib64/libwl_a1_webview.so
SHIM_PUSH=/data/local/tmp/libwl_a1_webview.so
SHIM_SHA=${A1_SHIM_SHA:-TBD_CCWIKI}
WORKER_SRC=$HERE/build/overlay/libwl_a1_worker.so                  # cc-wiki worker filename (adjust to the delivered name)
WORKER_DST=/data/local/tmp/libwl_a1_worker.so
WORKER_SHA=${A1_WORKER_SHA:-TBD_CCWIKI}

RECIPE=$HERE/../2026-09-28-bms-route-deploy/batch/prepare_sandbox.sh
PKG_DIRS="/data/app/el1/100/base/$PKG /data/app/el1/100/database/$PKG /data/app/el2/100/base/$PKG /data/app/el2/100/database/$PKG /data/app/el2/100/sharefiles/$PKG /data/app/el3/100/base/$PKG /data/app/el3/100/database/$PKG /data/app/el4/100/base/$PKG /data/app/el4/100/database/$PKG /data/app/el2/100/log/$PKG /data/app/el1/bundle/public/$PKG"
H() { timeout "${T:-60}" hdc -t "$SERIAL" shell "$@"; }

[ -e "$OUT" ] && { echo "refusing: $OUT exists"; exit 2; }
for v in JAR_SHA SHIM_SHA WORKER_SHA; do
  [ "${!v}" = TBD_CCWIKI ] && { echo "refusing: $v is a placeholder — fill cc-wiki's artifact SHA (env A1_${v} or edit) first"; exit 2; }
done
[ "$(shasum -a 256 "$APK" | cut -d' ' -f1)" = "$APK_SHA" ] || { echo "APK hash mismatch"; exit 2; }
for f in "$JAR_SRC:$JAR_SHA" "$SHIM_SRC:$SHIM_SHA" "$WORKER_SRC:$WORKER_SHA"; do
  p=${f%:*}; want=${f##*:}
  [ -f "$p" ] || { echo "overlay source missing: $p"; exit 2; }
  [ "$(shasum -a 256 "$p" | cut -d' ' -f1)" = "$want" ] || { echo "overlay SHA mismatch: $p"; exit 2; }
done
hdc list targets | grep -q "^$SERIAL$" || { echo "board $SERIAL not connected"; exit 3; }
held=$("$NOTE" held "$SERIAL" 2>/dev/null || true); [ -z "$held" ] || { echo "board held: $held"; exit 75; }
mkdir -p "$OUT"; exec > >(tee "$OUT/session.log") 2>&1
echo "[a1] start $(date -Iseconds) serial=$SERIAL url='${URL:-<data:page>}' apk=$APK_SHA"

"$NOTE" lock "$BOARD" "$SERIAL" "$LANE" "M2 A1 WebView: overlay route-a provider, install $PKG, load ${URL:-data:page}, rollback; <=30 min" || exit 75
START=$(date +%s)
FP=$HERE/../2026-10-03-m2-a0-probe/board/fingerprint.py
python3 "$FP" "$SERIAL" "$OUT" runtime-fingerprint-after-lock.txt | tee "$OUT/fingerprint-after-lock.txt"

exists() { [ "$(H "[ -e $1 ] && echo PRESENT || echo ABSENT" | tr -d '\r\n')" = PRESENT ]; }
ctx_of() { H "ls -Z $1" | grep -oE 'u:object_r:[A-Za-z0-9_]+:s0' | head -1; }

ORIG_JAR_SHA=""; MOUNTED_JAR=0; MOUNTED_SHIM=0
mount_overlays() {
  local ctx; ctx=$(ctx_of "$RT_REF"); [ -n "$ctx" ] || { echo "[a1] no ref SELinux ctx"; return 1; }
  # --- jar: overlay OVER the existing deployed jar; record its original SHA; NEVER rm the real jar ---
  exists "$JAR_TARGET" || { echo "[a1] $JAR_TARGET absent (expected a deployed non-BCP jar) -> stop"; return 1; }
  ORIG_JAR_SHA=$(H "sha256sum $JAR_TARGET 2>/dev/null | cut -d' ' -f1" | tr -d '\r')
  echo "[a1] original $JAR_TARGET sha=$ORIG_JAR_SHA (recorded for restore)"
  T=120 hdc -t "$SERIAL" file send "$JAR_SRC" "$JAR_PUSH" >/dev/null || { echo "[a1] jar send failed"; return 1; }
  H "chcon $(ctx_of "$JAR_TARGET") $JAR_PUSH" 2>/dev/null || H "chcon $ctx $JAR_PUSH"
  local r; r=$(H "mount -o bind $JAR_PUSH $JAR_TARGET && echo OK || echo FAIL" | tr -d '\r')
  [ "$r" = OK ] || { echo "[a1] jar bind-mount failed"; return 1; }
  MOUNTED_JAR=1
  local on; on=$(H "sha256sum $JAR_TARGET | cut -d' ' -f1" | tr -d '\r')
  echo "[a1] jar overlaid: on-board=$(echo $on|cut -c1-16) expect=$(echo $JAR_SHA|cut -c1-16)"
  [ "$on" = "$JAR_SHA" ] || { echo "[a1] jar overlay content mismatch"; return 1; }
  # --- worker .so -> /data/local/tmp ---
  T=120 hdc -t "$SERIAL" file send "$WORKER_SRC" "$WORKER_DST" >/dev/null || { echo "[a1] worker send failed"; return 1; }
  H "chcon $ctx $WORKER_DST"
  # --- shim .so -> /system/android/lib64 (absent on a clean board: create + bind-mount, rm on rollback) ---
  if exists "$SHIM_TARGET"; then echo "[a1] $SHIM_TARGET already present (deployed?): stop, will not shadow it"; return 1; fi
  T=120 hdc -t "$SERIAL" file send "$SHIM_SRC" "$SHIM_PUSH" >/dev/null || { echo "[a1] shim send failed"; return 1; }
  H "chcon $ctx $SHIM_PUSH"
  H "touch $SHIM_TARGET" ; exists "$SHIM_TARGET" || { echo "[a1] cannot create $SHIM_TARGET (ro fs?)"; return 1; }
  r=$(H "mount -o bind $SHIM_PUSH $SHIM_TARGET && echo OK || echo FAIL" | tr -d '\r')
  [ "$r" = OK ] || { echo "[a1] shim bind-mount failed"; return 1; }
  MOUNTED_SHIM=1
  local son; son=$(H "sha256sum $SHIM_TARGET | cut -d' ' -f1" | tr -d '\r')
  echo "[a1] shim mounted: on-board=$(echo $son|cut -c1-16) expect=$(echo $SHIM_SHA|cut -c1-16)"
  [ "$son" = "$SHIM_SHA" ] || { echo "[a1] shim overlay content mismatch"; return 1; }
}
unmount_overlays() {
  [ "$MOUNTED_SHIM" = 1 ] && H "umount $SHIM_TARGET 2>/dev/null; true"
  H "rm -f $SHIM_TARGET $SHIM_PUSH $WORKER_DST 2>/dev/null; true"          # the .so targets were absent pre-window
  [ "$MOUNTED_JAR" = 1 ] && H "umount $JAR_TARGET 2>/dev/null; true"       # restores the ORIGINAL deployed jar
  H "rm -f $JAR_PUSH 2>/dev/null; true"                                    # only the pushed copy; NEVER the real jar
  local shim_st=ABSENT; exists "$SHIM_TARGET" && shim_st=PRESENT
  local jar_now; jar_now=$(H "sha256sum $JAR_TARGET 2>/dev/null | cut -d' ' -f1" | tr -d '\r')
  echo "[a1] unmount: shim $SHIM_TARGET after=$shim_st (expect ABSENT); jar restored sha=$(echo $jar_now|cut -c1-16) orig=$(echo $ORIG_JAR_SHA|cut -c1-16)"
  [ "$shim_st" = ABSENT ] && { [ -z "$ORIG_JAR_SHA" ] || [ "$jar_now" = "$ORIG_JAR_SHA" ]; }
}

APP_UID=""
kill_app() {
  [ -z "$APP_UID" ] && APP_UID=$(H "bm dump -n $PKG" 2>/dev/null | grep -m1 -E '"uid"' | grep -oE '[0-9]+' | head -1)
  H "aa force-stop $PKG" >/dev/null 2>&1 || true
  [ -z "$APP_UID" ] && return 0
  [ "$APP_UID" = 0 ] && { echo "[a1] kill_app: refusing uid 0"; return 0; }
  local i pids
  for i in $(seq 1 12); do
    pids=$(H "ps -A -o PID,USER" | grep -E " $APP_UID *$" | sed 's/^ *//; s/ .*//' | tr -d '\r')
    [ -z "$pids" ] && { echo "[a1] kill_app: uid=$APP_UID clean"; return 0; }
    for p in $pids; do H "kill -9 $p" >/dev/null 2>&1 || true; done
    sleep 1
  done
  echo "[a1] kill_app: WARN uid=$APP_UID still alive"
}
rollback() {
  unmount_overlays || RB_FAIL=1
  echo "[a1] rollback $(date -Iseconds)"
  H "param set debug.westlake.a1.url ''" 2>/dev/null || true
  kill_app; uid=$APP_UID
  T=180 H "bm uninstall -n $PKG"; H "rm -f /data/local/tmp/a1webview.apk /data/local/tmp/a1-*.jpeg /data/local/tmp/a1-sandbox.sh"
  H "rm -rf $PKG_DIRS; rmdir /mnt/sandbox/100/$PKG 2>/dev/null; true"
  sleep 2
  left=$(H "bm dump -n $PKG" 2>&1 | grep -c '"bundleName"' || true)
  procs=0; [ -n "${uid:-}" ] && procs=$(H "ps -A -o PID,USER" | grep -cE " $uid *$" || true)
  echo "[a1] after rollback: bundle_entries=$left live_processes=$procs rb_fail=${RB_FAIL:-0}"
  [ "$left" = 0 ] && [ "$procs" = 0 ] && [ "${RB_FAIL:-0}" = 0 ]
}
finish() {
  rc=$?; trap - EXIT INT TERM HUP
  ok=1; rollback || ok=0
  python3 "$FP" "$SERIAL" "$OUT" runtime-fingerprint-before-unlock.txt | tee "$OUT/fingerprint-before-unlock.txt"
  if [ -n "${A1_EXPECT_FP:-}" ] && ! grep -q "RUNTIME fingerprint=$A1_EXPECT_FP " "$OUT/fingerprint-before-unlock.txt"; then
    echo "[a1] before-unlock fingerprint is not $A1_EXPECT_FP"; ok=0
  fi
  if cmp -s "$OUT/runtime-fingerprint-after-lock.txt" "$OUT/runtime-fingerprint-before-unlock.txt"; then
    echo "[a1] runtime fingerprint unchanged"
  else echo "[a1] runtime fingerprint CHANGED"; /usr/bin/diff "$OUT/runtime-fingerprint-after-lock.txt" "$OUT/runtime-fingerprint-before-unlock.txt"; ok=0; fi
  if [ $ok = 1 ]; then "$NOTE" unlock "$BOARD" "$SERIAL" "$LANE"; echo "[a1] UNLOCKED after $(( $(date +%s) - START )) s"
  else echo "[a1] ROLLBACK/FINGERPRINT FAILED: lock kept"; "$NOTE" progress "$BOARD" 90 "$LANE" "A1 rollback/fingerprint failed on $SERIAL; lock kept, see $OUT/session.log"; fi
  exit $rc
}
trap finish EXIT INT TERM HUP
if [ -n "${A1_EXPECT_FP:-}" ]; then
  grep -q "RUNTIME fingerprint=$A1_EXPECT_FP " "$OUT/fingerprint-after-lock.txt" || { echo "[a1] after-lock fingerprint is not $A1_EXPECT_FP: stop"; exit 7; }
  echo "[a1] after-lock fingerprint = expected $A1_EXPECT_FP"
fi

echo "== read-only preflight"
H "param get const.ohos.fullname; uptime"
H "bm dump -n $PKG" | grep -q '"bundleName"' && { echo "[a1] $PKG already installed: leftover, stop"; exit 4; }

if ! mount_overlays; then echo "[a1] mount_overlays failed: stop before install"; exit 8; fi

echo "== install"
T=120 hdc -t "$SERIAL" file send "$APK" /data/local/tmp/a1webview.apk
T=180 H "bm install -p /data/local/tmp/a1webview.apk" | tee "$OUT/install.txt"
H "bm dump -n $PKG" > "$OUT/bm-dump.txt"; grep -q '"bundleName"' "$OUT/bm-dump.txt" || { echo "[a1] install failed"; exit 5; }
APP_UID=$(grep -m1 -E '"uid"' "$OUT/bm-dump.txt" | grep -oE '[0-9]+' | head -1)
[ -n "$APP_UID" ] && [ "$APP_UID" -ge 20000000 ] || { echo "[a1] no app uid"; exit 5; }
{ printf 'set -e\nD() { sh -c "$1"; }\n'; cat "$RECIPE"; printf '\nprepare_sandbox %s %s\n' "$PKG" "$APP_UID"; } > "$OUT/sandbox-command.sh"
T=60 hdc -t "$SERIAL" file send "$OUT/sandbox-command.sh" /data/local/tmp/a1-sandbox.sh >/dev/null
T=120 H "sh /data/local/tmp/a1-sandbox.sh; echo rc=\$?" | tee "$OUT/sandbox-preparation.txt"
grep -q "^rc=0" "$OUT/sandbox-preparation.txt" || { echo "[a1] sandbox preparation failed"; exit 6; }

echo "== launch"
kill_app
[ -n "$URL" ] && H "param set debug.westlake.a1.url '$URL'"
t0=$(H "date +%m-%d\ %H:%M:%S" | tr -d '\r')
if [ -n "$URL" ]; then H "aa start -b $PKG -a $PKG.MainActivity --ps wl_url '$URL'" | tee "$OUT/aa-start.txt"
else H "aa start -b $PKG -a $PKG.MainActivity" | tee "$OUT/aa-start.txt"; fi
sleep 30
H "snapshot_display -f /data/local/tmp/a1-shot.jpeg" >/dev/null; T=60 hdc -t "$SERIAL" file recv /data/local/tmp/a1-shot.jpeg "$OUT/t30.jpeg" >/dev/null
H "ps -A -o PID,PPID,USER,NAME" > "$OUT/ps.txt"
T=120 H "hilog -x" > "$OUT/hilog-all.txt"
grep -E "A1-JAVA|$PKG|ArkWeb|arkweb|NWEB|nweb|webview|WebView|nwebspawn|org.westlake.webview|OhNWebProvider" "$OUT/hilog-all.txt" | awk -v t="$t0" '$1" "$2 >= t' > "$OUT/hilog-a1.txt"
grep -E "\[A1-JAVA\]|onPageFinished|onReceivedError" "$OUT/hilog-a1.txt" | tail -8
gzip -9 "$OUT/hilog-all.txt"
echo "[a1] done $(date -Iseconds) — judge by $OUT/t30.jpeg (WebView area shows the page)"
