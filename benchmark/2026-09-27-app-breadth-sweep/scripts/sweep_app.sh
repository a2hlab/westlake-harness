#!/usr/bin/env bash
# sweep_app.sh <app-key> — stage+launch ONE app on board 5ea34a45, wait, snapshot, classify.
# Idempotent: kills + clears the host between runs. Classifies LIT vs BLOCKED(category) from the
# child stderr lifecycle + process-alive + a screenshot saved for manual confirmation.
#
# SAFETY: hard-pinned to board 5ea34a45. ABORTS if $SERIAL is not exactly that board, so a stray
# run can never touch 61b06572 (Toutiao delivery) or 5cd1e3dd (device farm).
#
# Runtime-candidate env (the board runner's assembled 5ea34a45 base runtime — supply via env or a
# sourced config file; these are the same paths launch-webview10.sh / the probe wrapper already use):
#   HDC, SERIAL, WORKSPACE, WESTLAKE_SOURCE, FRAMEWORK_REPORT, HOST_BUILD, WEBVIEW_INPUT,
#   SOURCE_WEBVIEW_BUILD, APP_INPUT_ROOT (=/home/.../app-inputs), PROBE (=probe_source_app.py), OUT_ROOT
set -uo pipefail
APP="${1:?usage: sweep_app.sh <app-key>}"
SERIAL="${SERIAL:?SERIAL must be set}"

# ---- HARD BOARD GUARD (FIRST, before anything else) ----
# A wrong serial aborts immediately, even if other env is unset, so a stray run can never touch
# 61b06572 (Toutiao delivery) or 5cd1e3dd (device farm).
EXPECT_SERIAL="5ea34a4500000000000000001123012c"
if [ "$SERIAL" != "$EXPECT_SERIAL" ]; then
  echo "REFUSE: SERIAL=$SERIAL != $EXPECT_SERIAL (5ea34a45 only; never 61b06572/5cd1e3dd)" >&2; exit 2
fi

: "${HDC:?}" "${WORKSPACE:?}" "${WESTLAKE_SOURCE:?}" "${FRAMEWORK_REPORT:?}" "${HOST_BUILD:?}" \
  "${WEBVIEW_INPUT:?}" "${SOURCE_WEBVIEW_BUILD:?}" "${APP_INPUT_ROOT:?}" "${PROBE:?}" "${OUT_ROOT:?}"
HOST="${HOST:-org.westlake.imehost}"
WAIT="${WAIT:-30}"

if ! "$HDC" list targets 2>/dev/null | grep -qx "$EXPECT_SERIAL"; then
  echo "REFUSE: board $EXPECT_SERIAL not attached" >&2; exit 2
fi
h(){ "$HDC" -t "$EXPECT_SERIAL" "$@"; }   # every board op pinned to 5ea34a45

OUT="$OUT_ROOT/$APP"; rm -rf "$OUT"; mkdir -p "$OUT"
echo "=== sweep $APP on 5ea34a45 ==="

# ---- clean slate: stop + clear the host so the previous app can't bleed into this one ----
h shell "aa force-stop $HOST 2>/dev/null; pkill -f appspawn-x 2>/dev/null; true" >/dev/null 2>&1
h shell "rm -f /data/local/tmp/adapter_child_*.stderr" >/dev/null 2>&1
sleep 2

# ---- stage + launch via the board runner's probe (serial-pinned inside probe too) ----
timeout 180 python3 "$PROBE" \
    --workspace "$WORKSPACE" --westlake-source "$WESTLAKE_SOURCE" \
    --framework-report "$FRAMEWORK_REPORT" \
    --app-input "$APP_INPUT_ROOT/$APP" --app "$APP" \
    --hdc "$HDC" --serial "$EXPECT_SERIAL" --out "$OUT/probe" \
    --host-build "$HOST_BUILD" --webview-input "$WEBVIEW_INPUT" \
    --source-webview-build "$SOURCE_WEBVIEW_BUILD" \
    > "$OUT/probe.stdout" 2> "$OUT/probe.stderr"
PROBE_RC=$?
echo "probe rc=$PROBE_RC"

sleep "$WAIT"

# ---- collect: screenshot + child stderr + process-alive ----
h shell "snapshot_display -f /data/local/tmp/sweep_$APP.jpeg" >/dev/null 2>&1 \
  || h shell "screencap -p /data/local/tmp/sweep_$APP.png" >/dev/null 2>&1
h file recv "/data/local/tmp/sweep_$APP.jpeg" "$OUT/screen.jpeg" >/dev/null 2>&1 \
  || h file recv "/data/local/tmp/sweep_$APP.png" "$OUT/screen.png" >/dev/null 2>&1
CHILD=$(h shell "ls -t /data/local/tmp/adapter_child_*.stderr 2>/dev/null | head -1" | tr -d '\r')
[ -n "$CHILD" ] && h file recv "$CHILD" "$OUT/child.stderr" >/dev/null 2>&1
ALIVE=$(h shell "pidof appspawn-x 2>/dev/null | head -c 40" | tr -d '\r')

# ---- classify ----
S="$OUT/child.stderr"; [ -f "$S" ] || S="$OUT/probe.stderr"
verdict="BLOCKED"; category="unknown"
if grep -qE "Fatal signal|SIGSEGV|SIGABRT|\bpc 0+\b|pc=0x0*\b|libc.*abort" "$S" 2>/dev/null; then
  category="crash"
  grep -qE "0xd6e20|0xd5e1c|mallocng" "$S" && category="crash:mallocng-smash"
  grep -qiE "telephony|ITelephonyRegistry" "$S" && category="crash:telephony-NPE"
  grep -qiE "impeller|libflutter|eglGetProc|1.raster" "$S" && category="crash:flutter-impeller"
  grep -qiE "cannot locate symbol|undefined symbol|dlopen failed|UnsatisfiedLink" "$S" && category="crash:native-symbol"
elif [ -n "$ALIVE" ] && grep -qiE "ANativeWindow|first frame|onResume|render|SurfaceView|prewrapped|drawFrame" "$S" 2>/dev/null; then
  verdict="LIT"; category="rendered"
elif [ -n "$ALIVE" ]; then
  verdict="BLOCKED"; category="alive-no-render(stuck/black)"
else
  verdict="BLOCKED"; category="exited-no-crash-marker"
fi

echo "$APP	$verdict	$category	probe_rc=$PROBE_RC	alive=${ALIVE:-no}" | tee "$OUT/verdict.tsv"
# cleanup for the next app
h shell "aa force-stop $HOST 2>/dev/null; true" >/dev/null 2>&1
