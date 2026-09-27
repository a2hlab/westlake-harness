#!/usr/bin/env bash
# run_crux.sh [symlink|stub]  — GLESv1_CM crux test for fd-stk (SuperTuxKart) on board 5ea34a45.
#
# Sequence: (1) build the stub, (2) run the probe once so STK's libs stage into the app's native
# lib dir and it FAILS "Error loading shared library libGLESv1_CM.so" (baseline), (3) inject a
# libGLESv1_CM.so (symlink->libGLESv2.so, OR the built stub) into that same dir, (4) re-exec the
# probe's run.sh to relaunch STK, (5) snapshot + capture child stderr. Compare the two modes.
#
# HARD-PINNED to 5ea34a45; refuses if not attached (never 61b06572 / 5cd1e3dd).
set -uo pipefail
MODE="${1:-stub}"                      # symlink | stub
S5=5ea34a4500000000000000001123012c
H=/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh
W=/home/dspfac/a2hlab/source-closure/verify
FR=$HOME/a2hlab/board/$S5/framework-2/device-report.json
APPROOT=$HOME/a2hlab/app-inputs
OUT=$HOME/a2hlab/ws/out-glesv1cm-crux/$MODE
SRC=$(cd "$(dirname "$0")" && pwd)      # this dir (has glesv1_cm_stub.c)
ASXLIB=/data/local/tmp/asx/lib/arm64-v8a
HOSTPKG=org.westlake.imehost
SCREENS_MAC=/Users/zhaoyue/orca/workspaces/westlake-harness-merged48/benchmark/2026-09-27-app-breadth-sweep/glesv1cm-crux/screens

"$H" list targets 2>/dev/null | grep -qx "$S5" || { echo "REFUSE: 5ea34a45 not attached"; exit 2; }
b(){ "$H" -t "$S5" "$@"; }              # every board op pinned to 5ea34a45
mkdir -p "$OUT" "$SCREENS_MAC"

# ---- 1. build the stub (OH SDK clang; links OH libc for fprintf) ----
CLANG=$(ls "$HOME"/a2hlab/**/llvm/bin/clang 2>/dev/null | head -1)
[ -z "$CLANG" ] && CLANG=$(command -v /opt/ohos-sdk/*/native/llvm/bin/clang 2>/dev/null | head -1)
[ -z "$CLANG" ] && CLANG=$(command -v ohos-clang clang 2>/dev/null | head -1)
echo "clang=$CLANG"
"$CLANG" --target=aarch64-linux-ohos -fPIC -O2 -shared -Wl,-soname,libGLESv1_CM.so \
    -o "$OUT/libGLESv1_CM.so" "$SRC/glesv1_cm_stub.c" || { echo "BUILD FAILED"; exit 3; }
echo "built stub: $(ls -l "$OUT/libGLESv1_CM.so" | awk '{print $5}') bytes; exports:"
readelf --dyn-syms "$OUT/libGLESv1_CM.so" 2>/dev/null | awk '$7!="UND"&&/gl/{print $8}' | sort -u | tr '\n' ' '; echo

# ---- 2. baseline: probe stages STK libs into $ASXLIB and launches (should fail: file-not-found) ----
b shell "aa force-stop $HOSTPKG >/dev/null 2>&1; true" >/dev/null 2>&1; sleep 2
( cd "$HOME/a2hlab/manifest" && timeout 240 python3 tools/probe_source_app.py \
    --workspace "$W" --westlake-source "$W/westlake" --framework-report "$FR" \
    --app-input "$APPROOT/fd-stk" --app fd-stk --hdc "$H" --serial "$S5" --out "$OUT/probe" \
    --host-build "$W/out/signed-host" --webview-input "$W/out/webview-input-source" ) \
    > "$OUT/probe.stdout" 2> "$OUT/probe.stderr"
RUNSH=$(ls "$OUT"/probe/run.sh 2>/dev/null | head -1)
echo "probe rc=$?; run.sh=$RUNSH; staged libs in $ASXLIB:"; b shell "ls $ASXLIB/ | grep -iE 'SDL|GLES|main'"

# ---- 3. inject libGLESv1_CM.so into the staged lib dir ----
if [ "$MODE" = symlink ]; then
  echo "== SYMLINK mode: libGLESv1_CM.so -> libGLESv2.so =="
  b shell "cd $ASXLIB && rm -f libGLESv1_CM.so && ln -s /system/lib64/libGLESv2.so libGLESv1_CM.so && ls -l libGLESv1_CM.so"
else
  echo "== STUB mode: push built stub =="
  b file send "$OUT/libGLESv1_CM.so" "$ASXLIB/libGLESv1_CM.so"
  b shell "chmod 755 $ASXLIB/libGLESv1_CM.so; ls -l $ASXLIB/libGLESv1_CM.so"
fi

# ---- 4. relaunch STK via the probe's run.sh (child stderr → file) ----
b shell "aa force-stop $HOSTPKG >/dev/null 2>&1; true" >/dev/null 2>&1; sleep 1
# push run.sh to device and exec it, tee-ing child stderr
b file send "$RUNSH" /data/local/tmp/stk_run.sh
b shell "chmod 755 /data/local/tmp/stk_run.sh; setsid sh -c '/data/local/tmp/stk_run.sh >/data/local/tmp/stk_child.out 2>/data/local/tmp/stk_child.err' </dev/null >/dev/null 2>&1 & echo relaunched"
sleep 30

# ---- 5. capture ----
b shell "snapshot_display -f /data/local/tmp/stk_$MODE.jpeg" >/dev/null 2>&1
b file recv "/data/local/tmp/stk_$MODE.jpeg" "$SCREENS_MAC/stk_$MODE.jpeg" >/dev/null 2>&1
b file recv "/data/local/tmp/stk_child.err" "$OUT/stk_child.err" >/dev/null 2>&1
echo "=== child stderr (last 20) ==="; tail -20 "$OUT/stk_child.err" 2>/dev/null
echo "=== screenshot -> $SCREENS_MAC/stk_$MODE.jpeg ==="
b shell "aa force-stop $HOSTPKG >/dev/null 2>&1; true" >/dev/null 2>&1
