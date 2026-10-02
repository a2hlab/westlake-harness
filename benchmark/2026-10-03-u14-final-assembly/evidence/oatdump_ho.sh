#!/usr/bin/env bash
# Runs ON hw248: the T7d oatdump command shape (--header-only, pinned by the control) on U14 run1/run2 boot.art.
set -uo pipefail
LAB=$LAB_HOME R=$LAB/u14-bt-bake-0349-87cf-v1; O=$R/oatdump
OD=$LAB/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump
export LD_LIBRARY_PATH=$LAB/aosp-14.0.0_r1-art/out/host/linux-x86/lib64
p=""; l=""; for j in core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework; do p="$p${p:+:}$R/jars9/$j.jar"; l="$l${l:+:}/system/android/framework/$j.jar"; done
echo "oatdump: $(sha256sum $OD)"
for r in 1 2; do (
  cmd=("$OD" "--image=$O/img-run$r/boot.art" --instruction-set=arm64 --header-only --runtime-arg "-Xbootclasspath:$p" --runtime-arg "-Xbootclasspath-locations:$l")
  printf '[cmd headeronly-run%s]' $r; printf ' %q' "${cmd[@]}"; printf '\n'
  "${cmd[@]}" > $O/oatdump-headeronly-run$r.log 2>&1; rc=$?
  echo "{\"oatdump_exit_code\":$rc}" > $O/oatdump-headeronly-run$r.status.json
  echo "[rc headeronly-run$r] $rc $(wc -lc < $O/oatdump-headeronly-run$r.log) $(sha256sum < $O/oatdump-headeronly-run$r.log)"
) & done; wait
