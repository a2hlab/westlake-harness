#!/usr/bin/env bash
# Runs ON hw248. oatdump the U14 bake's run1/run2 boot.art (and, as the binary-identity control, the T7d reference
# image the T7d oatdump log came from). Every command is printed verbatim before it runs; stdout+stderr go to one log.
set -uo pipefail
LAB=$LAB_HOME
R=$LAB/u14-bt-bake-0349-87cf-v1
O=$R/oatdump
OD=$LAB/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump
export LD_LIBRARY_PATH=$LAB/aosp-14.0.0_r1-art/out/host/linux-x86/lib64
ORDER="core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework"
[ -d "$R/run1" ] && [ -d "$R/run2" ] || exit 4
[ ! -e "$O/oatdump-run1.log" ] || exit 4
mkdir -p "$O"
echo "oatdump: $(sha256sum $OD)"; ls -l --time-style=full-iso $OD
bcp() { local d=$1 p="" l=""; for j in $ORDER; do p="$p${p:+:}$d/$j.jar"; l="$l${l:+:}/system/android/framework/$j.jar"; done; echo "$p|$l"; }
dump() { # dump <name> <image-location> <jars-dir>
  local name=$1 img=$2 jars=$3 x; x=$(bcp "$jars")
  local cmd=("$OD" "--image=$img" "--instruction-set=arm64" "--runtime-arg" "-Xbootclasspath:${x%%|*}" "--runtime-arg" "-Xbootclasspath-locations:${x##*|}")
  printf '[cmd %s]' "$name"; printf ' %q' "${cmd[@]}"; printf '\n'
  "${cmd[@]}" > "$O/oatdump-$name.log" 2>&1; local rc=$?
  echo "[rc $name] $rc"; echo "{\"oatdump_exit_code\":$rc}" > "$O/oatdump-$name.status.json"
  sha256sum "$O/oatdump-$name.log"; wc -l < "$O/oatdump-$name.log"
}
for r in 1 2; do
  mkdir -p "$O/img-run$r/arm64"
  cp -a "$R/run$r/." "$O/img-run$r/arm64/"
  (cd "$O/img-run$r/arm64" && sha256sum -c --quiet "$R/logs/image-sha256-run$r.txt") || exit 5
  dump run$r "$O/img-run$r/boot.art" "$R/jars9"
done
dump t7d-control "$LAB/cc-wiki-t7d-out/boot.art" "$LAB/cc-wiki-t7d-jars"
