#!/bin/bash
# Native platform N2 (generated headers), N3 (objects needing them), N4 (renderer object combine).
set -u
A=/home/dspfac/a2hlab/source-closure/verify; O=$A/out; WT=$A/westlake/tools; INV=$A/westlake/native
mountpoint -q $A || { sudo mkdir -p $A && sudo mount --bind "$HOME/a2hlab/ws" $A; } || exit 1
M=$HOME/a2hlab/manifest; LOGS=$HOME/a2hlab/logs/build; cd "$M" || exit 1
ok() { for s; do [ -e "$LOGS/$s.ok" ] || return 1; done; }
step() {
  local name=$1; shift
  ok "$name" && { echo "SKIP $name"; return 0; }
  echo "START $name $(date +%T)"
  if "$@" > "$LOGS/$name.log" 2>&1; then touch "$LOGS/$name.ok"; echo "OK    $name $(date +%T)"; else echo "FAIL  $name $(date +%T)"; return 1; fi
}
CI="python3 $WT/compile_native_inventory.py --workspace $A --westlake-source $A/westlake --jobs 5"
HO="python3 $WT/build_hwui_objects.py --workspace $A --westlake-source $A/westlake --jobs 5"
# N2
step framework-native-flags python3 tools/build_framework_native_flags.py --flag-build $O/framework-flags --out $O/framework-native-flags &
step binder-stats-aidl python3 $WT/generate_binder_stats_aidl.py --workspace $A --stats-build $O/framework-generators --host-library-build $O/host-bootstrap --host-library-build $O/host-base --out $O/binder-stats-aidl &
step hwui-support python3 $WT/generate_hwui_support.py --workspace $A --sysprop-build $O/framework-generators --hidl-build $O/hidl-generator --stats-build $O/framework-generators --host-library-build $O/host-bootstrap --host-library-build $O/host-base --out $O/hwui-support &
wait; echo "N2_DONE $(date +%T)"
# N3
ok framework-native-flags && step minikin15 $CI --inventory $INV/minikin15-sources.json --header-build $O/framework-native-flags --out $O/minikin15 &
ok gui-aidl && step android-runtime15 $CI --inventory $INV/android-runtime15-sources.json --header-build $O/gui-aidl --out $O/android-runtime15 &
ok oh61-headers && step bridge15 $CI --inventory $INV/bridge15-sources.json --header-build $O/oh61-headers --out $O/bridge15 &
wait
ok binder-stats-aidl && step stats-pull $CI --inventory $INV/stats-pull-sources.json --header-build $O/binder-stats-aidl --out $O/stats-pull &
ok binder-stats-aidl && step stats-socket $CI --inventory $INV/stats-socket-sources.json --header-build $O/binder-stats-aidl --out $O/stats-socket &
wait
if ok framework-native-flags hwui-support; then
  step hwui15 $HO --inventory $INV/hwui15-complete-sources.json --header-build $O/framework-native-flags --header-build $O/hwui-support --out $O/hwui15 &
  step hwui15-registration $HO --inventory $INV/hwui15-registration-sources.json --header-build $O/framework-native-flags --header-build $O/hwui-support --out $O/hwui15-registration &
  step jnigraphics15 $HO --inventory $INV/jnigraphics15-sources.json --header-build $O/framework-native-flags --header-build $O/hwui-support --out $O/jnigraphics15 &
  wait
fi
echo "N3_DONE $(date +%T)"
# N4: skia15-rtti must be the last --build; eight Skia units replaced explicitly
R=""; for u in core_SkStream core_SkBitmap core_SkCanvas core_SkDrawable core_SkExecutor core_SkPixelRef utils_SkNWayCanvas utils_SkPaintFilterCanvas; do R="$R --replace objects/android-source_oh-skia_m133_src_$u.cpp.o"; done
ok hwui15 hwui15-registration && step renderer-objects python3 $WT/combine_native_objects.py --build $O/hwui15 --build $O/hwui15-platform --build $O/hwui15-registration --build $O/skia15-closure --build $O/skia15-gpu --build $O/skia15-codecs --build $O/skia15-support --build $O/skia15-platform --build $O/skia15-rtti $R --out $O/renderer-objects
echo "PHASE3B_DONE $(date +%T)"
