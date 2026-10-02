#!/bin/bash
# U12 boot-image bake, run N (hw248). FZ-005 tools: t5_gen_image.sh (14b1f709) driving dex2oat64 (ae865ddd) through
# Repo copy: the run copy (u12r2-v1/bake/, SHA in u12r2-v1/bake/receipt.json) with the hw248 home prefix written as $HOME/ (hw248 user).
# dex2oat64-tee.sh (full dex2oat output -> logs/dex2oat-runN.log). Same --work path for every run, so the
# dex2oat-cmdline strings embedded in the image are identical between runs; products copied to runN/.
set -uo pipefail
N=${1:?run number}
B=$HOME/u12r2-bake; W=$B/work
echo "[bake_u12] run $N start $(date -Is) host=$(hostname)"
sha256sum $HOME/cc-wiki-t5/tool/t5_gen_image.sh $HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64 $B/dex2oat64-tee.sh $B/t5-ref-u12.sha256
rm -rf "$W"; mkdir -p "$B/logs"
export U12_BAKE_LOG=$B/logs/dex2oat-run$N.log; : > "$U12_BAKE_LOG"
export LD_LIBRARY_PATH=$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/lib64
bash $HOME/cc-wiki-t5/tool/t5_gen_image.sh --dex2oat "$B/dex2oat64-tee.sh" --jars-dir "$B/jars9" --work "$W" --ref "$B/t5-ref-u12.sha256"
echo "[bake_u12] t5 rc=$?; dex2oat: $(tail -1 "$U12_BAKE_LOG")"
rm -rf "$B/run$N"; cp -a "$W/products/arm64" "$B/run$N"
echo "[bake_u12] run $N products: $(ls "$B/run$N" | wc -l) files, zero-size $(find "$B/run$N" -size 0 | wc -l)"
(cd "$B/run$N" && sha256sum *) | tee "$B/logs/image-sha256-run$N.txt"
echo "[bake_u12] run $N end $(date -Is)"
