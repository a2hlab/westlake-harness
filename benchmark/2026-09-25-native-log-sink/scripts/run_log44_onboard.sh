#!/usr/bin/env bash
# #44 on-board verification (run when the outer loop assigns board 61b06572).
# Overlays the #44-patched liblog.so onto a WORKING COPY of the runtime build,
# launches Toutiao with WESTLAKE_SOURCE_LOG_STDERR=1, and checks that app-native
# log lines now reach child.stderr. Does not mutate any shared build tree.
#
# Runs in the VM (needs the manifest probe tools + hdc_mac.sh for the board).
#   env overrides:
#     SERIAL   board connect key         (default 61b06572...)
#     BUILD    runtime build dir to base on (has appspawn/native-runtime/framework-runtime/
#              framework-boot/probe-local); default the #27 integration out-all0925
#     LIBLOG   the #44-patched liblog.so   (default out-log44/lib/liblog.so)
set -euo pipefail
A=/home/dspfac/a2hlab/source-closure/verify
B=${BUILD:-$A/out-all0925}
LIBLOG=${LIBLOG:-$A/out-log44/lib/liblog.so}
SERIAL=${SERIAL:-61b0657200000000000000000324012c}
HDC=${HDC:-/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh}
BASEJAVA=$A/out
R=$HOME/a2hlab/board/$SERIAL/log44
work=$R/build-overlay
mkdir -p "$R"

echo "== sanity: patched liblog has the sink =="
"$A/../../ws/toolchains/clang-15/bin/llvm-nm" -D "$LIBLOG" 2>/dev/null | grep -q __android_log_set_logger || { echo "liblog missing exports"; exit 3; }
strings -a "$LIBLOG" | grep -q WESTLAKE_SOURCE_LOG_STDERR || { echo "liblog missing #44 sink"; exit 3; }

echo "== working copy of the runtime build with liblog.so overlaid (shared build untouched) =="
rm -rf "$work"; mkdir -p "$work"
for d in appspawn native-runtime framework-runtime framework-boot probe-local; do
  [ -e "$B/$d" ] && cp -a "$B/$d" "$work/$d"
done
# overlay the patched liblog into every runtime dir that carries one
for t in "$work/native-runtime/liblog.so"; do
  [ -e "$t" ] && cp -f "$LIBLOG" "$t" && echo "overlaid $t"
done
# core-runtime is the same dir as native-runtime in the touch21/#38 recipe
echo "overlaid liblog sha: $(sha256sum "$work/native-runtime/liblog.so" | cut -c1-16)"

echo "== stage framework onto the board =="
cd "$HOME/a2hlab/manifest"
python3 tools/probe_framework_vm.py \
  --appspawn-build "$work/appspawn" --core-runtime "$work/native-runtime" \
  --native-runtime "$work/native-runtime" --core-build "$BASEJAVA/core-java/java" \
  --extension-build "$BASEJAVA/java-extensions" --framework-build "$work/framework-runtime" \
  --boot-build "$work/framework-boot" --resources-build "$BASEJAVA/framework-resources" \
  --data-build "$BASEJAVA/runtime-data" \
  --firmware-abi "$A/westlake/native/oh61-firmware-abi.json" \
  --hdc "$HDC" --serial "$SERIAL" --out "$R/framework" > "$R/framework.log" 2>&1
echo "framework staged (see $R/framework.log)"

echo "== launch Toutiao with the native-log stderr sink enabled =="
"$HDC" -t "$SERIAL" shell "pidof com.ss.android.article.news >/dev/null && echo BUSY || echo free"
python3 "$work/probe-local/tools/probe_source_app.py" \
  --app toutiao --hdc "$HDC" --serial "$SERIAL" --out "$R/toutiao-1" \
  --runtime-env WESTLAKE_SOURCE_LOG_STDERR=1 > "$R/toutiao-1.log" 2>&1 || true
echo "launch done (see $R/toutiao-1.log)"

echo "== does child.stderr now carry app-native log lines? =="
CS=$(find "$R/toutiao-1" -name 'child.stderr' | head -1)
echo "child.stderr = $CS"
echo "-- app-native tag hits --"
grep -icE "Cronet|ttnet|TTNet|Lynx|metasec|METASEC|MSTaskManager|DoLazyInit|Gorgon|Argus|bytedance|npth|BDTracker" "$CS" 2>/dev/null || true
echo "-- METASEC / DoLazyInit specifically --"
grep -nE "METASEC|MSTaskManager|DoLazyInit" "$CS" 2>/dev/null | head || echo "(none)"
echo "-- distinct native-ish tags (logcat form '<p> <tag> :') --"
grep -oE "^[VDIWEF] [^:]+ :" "$CS" 2>/dev/null | sort | uniq -c | sort -rn | head -40
echo "== done. Compare tag set + volume against the Android reference logcat; check #38 queueMs separately. =="
