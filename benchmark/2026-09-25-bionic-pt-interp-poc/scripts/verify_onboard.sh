#!/usr/bin/env bash
# #39 on-board verification. Pushes the Bionic linker64 + libs + PoC binaries to
# /data/local/tmp/bionic39 ONLY, runs them, and checks for SELinux denials.
# Never touches /system, never remounts. Reads dmesg/hilog by diff (no dmesg -c).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
SERIAL="${SERIAL:-5cd1e3dd00000000000000000923012c}"
APEX="${APEX:-$HOME/OrbStack/a2hlab/home/zhaoyue/a2hlab/bionic39/runtime-apex}"
OUT="$HERE/out"
RD=/data/local/tmp/bionic39
sh() { "$HDC" -t "$SERIAL" shell "$@"; }
snd() { "$HDC" -t "$SERIAL" file send "$1" "$2" >/dev/null; }

echo "== target =="; sh "getprop const.product.model 2>/dev/null; id; uname -a"

echo "== stage files under $RD (no /system writes) =="
sh "rm -rf $RD; mkdir -p $RD/lib64/bionic"
snd "$APEX/bin/linker64"            "$RD/linker64"
snd "$APEX/lib64/bionic/libc.so"    "$RD/lib64/bionic/libc.so"
snd "$APEX/lib64/bionic/libdl.so"   "$RD/lib64/bionic/libdl.so"
snd "$APEX/lib64/bionic/libm.so"    "$RD/lib64/bionic/libm.so"
for b in tp_probe_static hello_static tp_probe_dyn hello_dyn; do snd "$OUT/$b" "$RD/$b"; done
sh "chmod 755 $RD/linker64 $RD/tp_probe_* $RD/hello_* ; ls -l $RD $RD/lib64/bionic"

echo "== dmesg/hilog baseline (line counts) =="
D0=$(sh "dmesg 2>/dev/null | wc -l" | tr -d '\r')
echo "dmesg lines before: $D0"

echo "== A. static control (no interpreter) =="
sh "cd $RD && ./tp_probe_static; echo EXIT=\$?"

echo "== B. dynamic via Bionic linker64 =="
LP="$RD/lib64/bionic"
sh "cd $RD && LD_LIBRARY_PATH=$LP ./hello_dyn; echo EXIT=\$?"
sh "cd $RD && LD_LIBRARY_PATH=$LP ./tp_probe_dyn; echo EXIT=\$?"

echo "== B2. explicit-linker form (linker64 executable-mode) =="
sh "cd $RD && LD_LIBRARY_PATH=$LP ./linker64 ./tp_probe_dyn; echo EXIT=\$?"

echo "== dmesg delta since baseline, avc grep =="
sh "dmesg 2>/dev/null | tail -n +$((D0+1)) | grep -iE 'avc|denied|linker64|tp_probe' || echo '(no matching new dmesg lines)'"
echo "== hilog avc grep (recent) =="
sh "hilog -x 2>/dev/null | grep -iE 'avc|denied' | tail -20 || echo '(hilog empty/none)'"
echo "== done =="
