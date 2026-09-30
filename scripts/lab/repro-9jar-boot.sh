#!/bin/bash
# repro-9jar-boot.sh — reproduce the board's 27-file boot image with the
# official AOSP android-14.0.0_r16 dex2oat (outer-loop official line).
#
# Order and flags are transcribed byte-for-byte from the OatHeader
# key-value store of the board's boot.oat (see dex2oat-a14.md "OatHeader
# key-value"); inputs are the 9 jars listed in boot-image-inputs.sha256.
#
# Usage: repro-9jar-boot.sh <dex2oat64> <jars-dir> <out-dir>
#   jars-dir must contain the 9 jars (sha256-verified against
#   knowledge/toolchains/boot-image-inputs.sha256 before running).
set -euo pipefail

D2O=${1:?dex2oat64 path}
JARS=${2:?jars dir}
OUT=${3:?out dir}
LIST=${LIST:-knowledge/toolchains/boot-image-inputs.sha256}

# 1) verify the 9 input jars against the manifest (any mismatch aborts)
HERE=$(cd "$(dirname "$0")" && pwd)
MANIFEST=$(cd "$HERE/../../.." && pwd)/knowledge/toolchains/boot-image-inputs.sha256
[ -f "$MANIFEST" ] || MANIFEST="$LIST"
JAR_ORDER="core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework"
for j in $JAR_ORDER; do
  want=$(awk -v n="$j.jar" '$2 == n {print $1}' "$MANIFEST")
  got=$(sha256sum "$JARS/$j.jar" | awk '{print $1}')
  [ "$want" = "$got" ] || { echo "INPUT MISMATCH: $j.jar"; echo " want $want"; echo " got  $got"; exit 2; }
done
echo "inputs: 9/9 jars verified"

# 2) assemble the command exactly as recorded in the OatHeader
DEX_ARGS=()
for j in $JAR_ORDER; do
  DEX_ARGS+=(--dex-file="$JARS/$j.jar" --dex-location="/system/android/framework/$j.jar")
done

mkdir -p "$OUT/arm64"
"$D2O" --android-root=/system \
  --instruction-set=arm64 \
  --base=0x70000000 \
  --compiler-filter=speed \
  --runtime-arg -Xms64m --runtime-arg -Xmx512m --runtime-arg -Xverify:none \
  --image="$OUT/arm64/boot.art" \
  --oat-file="$OUT/arm64/boot.oat" \
  "${DEX_ARGS[@]}"

# 3) L1 check: compare every produced file against the manifest
fail=0
while read -r sha rel; do
  [ -f "$OUT/$rel" ] || { echo "MISSING $rel"; fail=1; continue; }
  got=$(sha256sum "$OUT/$rel" | awk '{print $1}')
  if [ "$got" = "$sha" ]; then echo "L1 OK   $rel"; else echo "L1 DIFF $rel"; fail=1; fi
done < <(grep 'arm64/' "$MANIFEST")
exit $fail
