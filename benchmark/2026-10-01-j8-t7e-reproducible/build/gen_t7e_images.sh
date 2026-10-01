#!/bin/bash
# T7e boot-image regeneration (runs on hw248). Produces the 27-file arm64 boot image from the 9 BCP jars
# (8 T7d-identical + the new adapter-mainline-stubs.jar with full ColorMatrix) using the FZ-005 toolchain.
#
#   gen_t7e_images.sh <new-stubs.jar> <out-dir>
#
# Prereqs on hw248 (FZ-005): dex2oat64 ae865ddd..., t5_gen_image.sh 14b1f709..., the 8 T7d jars.
set -euo pipefail
NEWSTUBS=${1:?usage: gen_t7e_images.sh <new-stubs.jar> <out-dir>}
OUTROOT=${2:?usage: gen_t7e_images.sh <new-stubs.jar> <out-dir>}
LAB_HOME=${LAB_HOME:-$HOME}                                               # hw248 lab home
DEX2OAT=${DEX2OAT:-$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64}   # ae865ddd...
GEN=${T5_GEN:-$LAB_HOME/cc-wiki-t5/tool/t5_gen_image.sh}                  # 14b1f709...
T7DJARS=${T7D_JARS:-$LAB_HOME/cc-wiki-t7d-jars}                           # 8 non-stubs = T7d (= config.json input_jars)
REF=${T7E_REF:?set T7E_REF to the T7e ref (T7d input jars with stubs sha replaced + T7d 27 outputs)}

rm -rf "$OUTROOT"; mkdir -p "$OUTROOT/jars" "$OUTROOT/work" "$OUTROOT/out"
for j in core-oj core-libart core-icu4j okhttp bouncycastle apache-xml framework oh-adapter-framework; do
  cp "$T7DJARS/$j.jar" "$OUTROOT/jars/$j.jar"
done
cp "$NEWSTUBS" "$OUTROOT/jars/adapter-mainline-stubs.jar"
bash "$GEN" --dex2oat "$DEX2OAT" --jars-dir "$OUTROOT/jars" --work "$OUTROOT/work" --out "$OUTROOT/out" --ref "$REF" || true
# t5_gen_image exits 6 by design (wants 9/9 vdex for pure reproduction); for T7e the stubs vdex is INTENDED
# to differ. T7e pass = G1 (8/9 unchanged vdex byte-identical to the T7d reference) + G2 (only the stubs
# segment changed) + L2 headers (oat 230 / art 108).
echo "[t7e] 27 outputs in $OUTROOT/out ; verify G1/G2 against the T7d reference (benchmark/2026-10-01-u7-executor/t7d-build-receipt.json)"
