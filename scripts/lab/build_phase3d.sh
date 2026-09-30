#!/bin/bash
# Native platform N5-N8: object map (reconstructed, validated read-only), link-only imports, platform link,
# media JNI, appspawn-x link, composed native runtime.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
T=$WORKSPACES/westlake-inputs/tools
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
MAP=$A/native-object-map.json
[ -e $MAP ] || cp $T/scratch/native-object-map.json $MAP
echo "object map sha256 $(sha256sum $MAP | cut -c1-16)"
step object-map-check python3 $T/scratch/check_object_map.py $MAP \
 && step native-imports python3 $WT/build_native_imports.py --workspace $A --firmware-abi $INV/oh61-firmware-abi.json --object-map $MAP --out $O/native-imports \
 && step native-platform python3 $WT/link_native_platform.py --workspace $A --object-map $MAP --imports $O/native-imports --core-runtime $O/art/runtime --out $O/native-platform \
 && { step media-jni python3 tools/build_media_jni_compat.py --workspace $A --westlake-source $A/westlake --bridge-build $O/native-platform --out $O/media-jni &
      step appspawn python3 $WT/link_appspawn.py --workspace $A --objects $O/appspawn-objects --runtime $O/native-platform --core-runtime $O/art/runtime --imports $O/native-imports --out $O/appspawn &
      wait; } \
 && ok media-jni && step runtime-extras bash $T/build_extras.sh \
 && step runtime-helpers bash $T/build_runtime_helpers.sh \
 && step native-runtime python3 tools/compose_native_runtime.py --build $O/art/runtime --build $O/native-platform --build $O/connectivity-native --build $O/media-jni --build $O/runtime-extras --build $O/runtime-helpers --replace libminikin.so --out $O/native-runtime
echo "PHASE3D_DONE $(date +%T)"
