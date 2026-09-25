#!/usr/bin/env bash
# #41 ① — can the REAL app domain (u:r:normal_hap:s0) exec a PT_INTERP=Bionic program
# and mmap-execute Bionic files? Controlled 2-label experiment, same binary/paths.
# Enters normal_hap by writing /proc/self/attr/exec in a shell builtin (su is permissive,
# so the setexeccon + su->normal_hap transition is allowed; file exec is then judged as
# normal_hap, which is ENFORCING). dmesg is bounded by unique /dev/kmsg markers, never
# by line count. Writes only /data/local/tmp/bionic41.
set -uo pipefail
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
SERIAL="${SERIAL:-5cd1e3dd00000000000000000923012c}"
APEX="${APEX:-$HOME/OrbStack/a2hlab/home/zhaoyue/a2hlab/bionic39/runtime-apex}"
OUT="$(cd "$(dirname "$0")" && pwd)/out"
RD=/data/local/tmp/bionic41; LP=$RD/lib64/bionic; DOM=u:r:normal_hap:s0
sh(){ "$HDC" -t "$SERIAL" shell "$@"; }
snd(){ "$HDC" -t "$SERIAL" file send "$1" "$2" >/dev/null; }

echo "== stage =="
sh "rm -rf $RD; mkdir -p $LP"
snd "$APEX/bin/linker64" "$RD/linker64"
snd "$APEX/lib64/bionic/libc.so" "$LP/libc.so"
snd "$APEX/lib64/bionic/libdl.so" "$LP/libdl.so"
snd "$APEX/lib64/bionic/libm.so" "$LP/libm.so"
snd "$OUT/tp_probe41" "$RD/tp_probe41"
sh "chmod -R 755 $RD"

echo "== control: run in su domain (baseline, expect exit 0) =="
sh "cd $RD && LD_LIBRARY_PATH=$LP ./tp_probe41; echo EXIT=\$?"

run_case(){
  local tag="$1" label="$2"
  echo "== case $tag: files labelled $label, exec under $DOM =="
  sh "chcon -R $label $RD 2>&1; ls -Zd $RD; ls -Z $RD/linker64 $RD/tp_probe41 $LP/libc.so"
  sh "echo '=== A2H41 MARK $tag BEGIN ===' > /dev/kmsg 2>/dev/null; true"
  sh "cd $RD && LD_LIBRARY_PATH=$LP sh -c 'echo -n $DOM > /proc/self/attr/exec && exec $RD/tp_probe41'; echo EXIT=\$?"
  sh "echo '=== A2H41 MARK $tag END ===' > /dev/kmsg 2>/dev/null; true"
  echo "-- normal_hap avc between markers (direct grep, show permissive=) --"
  sh "dmesg | sed -n '/A2H41 MARK $tag BEGIN/,/A2H41 MARK $tag END/p' | grep -E 'avc:|denied' || echo '(no avc lines in window)'"
}

run_case datalocal "u:object_r:data_local_tmp:s0"
run_case appdat     "u:object_r:appdat:s0"

echo "== all normal_hap denials currently in ring buffer (context) =="
sh "dmesg | grep 'scontext=u:r:normal_hap:s0' | tail -20 || echo '(none)'"
echo "== done =="
