#!/bin/bash
# Native platform, object builds that need no generated headers (N1 of the reconstructed plan).
# Up to 3 builds at a time with 5 jobs each; every step logs to $LOGS/<step>.log and is skipped once ok.
set -u
A=/home/dspfac/a2hlab/source-closure/verify; O=$A/out; WT=$A/westlake/tools; INV=$A/westlake/native
mountpoint -q $A || { sudo mkdir -p $A && sudo mount --bind "$HOME/a2hlab/ws" $A; } || exit 1
M=$HOME/a2hlab/manifest; LOGS=$HOME/a2hlab/logs/build; mkdir -p "$LOGS"; cd "$M" || exit 1
run() {  # run <name> <command...>
  local name=$1; shift
  [ -e "$LOGS/$name.ok" ] && { echo "SKIP $name"; return 0; }
  echo "START $name $(date +%T)"
  if "$@" > "$LOGS/$name.log" 2>&1; then touch "$LOGS/$name.ok"; echo "OK    $name $(date +%T)"; else echo "FAIL  $name $(date +%T)"; fi
}
export -f run; export A O WT INV LOGS
{
  echo "oh61-headers|python3 tools/build_oh61_headers.py --workspace $A --out $O/oh61-headers"
  echo "gui-aidl|python3 $WT/generate_gui_aidl.py --workspace $A --out $O/gui-aidl"
  echo "hwui-shims|python3 $WT/build_hwui_shims.py --workspace $A --westlake-source $A/westlake --jobs 5 --out $O/hwui-shims"
  echo "connectivity-native|python3 tools/build_connectivity_native.py --workspace $A --westlake-source $A/westlake --out $O/connectivity-native"
  for x in binder15 binder15-ndk android-ndk15 gif15 ultrahdr15 jpeg15 webp15 wuffs15 securec15 stats-jni15 libcore-linux15 libstdcxx15 bionic-abi os-account15 permission15 connectivity-jni15 connectivity-core-jni15 hwui15-platform; do
    echo "$x|python3 $WT/compile_native_inventory.py --workspace $A --westlake-source $A/westlake --jobs 5 --inventory $INV/$x-sources.json --out $O/$x"
  done
  echo "appspawn-objects|python3 $WT/compile_native_inventory.py --workspace $A --westlake-source $A/westlake --jobs 5 --inventory $INV/appspawn-sources.json --out $O/appspawn-objects"
  for x in skia15-closure skia15-gpu skia15-codecs skia15-support skia15-platform skia15-rtti; do
    echo "$x|python3 $WT/build_hwui_objects.py --workspace $A --westlake-source $A/westlake --jobs 5 --inventory $INV/$x-sources.json --out $O/$x"
  done
} | xargs -P 3 -I{} bash -c 'line="{}"; run "${line%%|*}" ${line#*|}'
echo "PHASE3A_DONE $(date +%T)"
