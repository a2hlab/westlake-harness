#!/bin/bash
# T5 (specs/dex2oat-once/t5-boot-image.spec.md) — generate the 9-segment boot image (27 files)
# with T3's dex2oat64, using the board boot.oat's recorded dex2oat-cmdline + key-value set,
# then byte-compare all 27 against knowledge/toolchains/boot-image-inputs.sha256.
# Runs on hw248 once T3 produces dex2oat64 + arm64 libart.
#
# Acceptance (d5_image_headers_match): the 9 .vdex byte-identical to reference; boot.oat
# oat version 230, boot.art image version 108; key-value set matches the board. .oat/.art
# are NOT expected byte-identical (their OatHeader embeds the dex2oat-cmdline path strings +
# source-tree fingerprint) — those diffs are recorded with cause (oc-t4 official-r16 repro:
# 9/27 = all vdex; 18 differ = 9 .oat + 9 .art, from embedded path strings).
#
# Usage:
#   t5_gen_image.sh --dex2oat <dex2oat64> --jars-dir <dir-with-9-jars> [--work <path>] [--out <dir>] [--ref <sha256>]
#   t5_gen_image.sh --check --jars-dir <dir>        # offline: verify 9 jars vs ref + print cmdline, no run
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REF_DEFAULT="$HERE/../boot-image-inputs.sha256"   # knowledge/toolchains/boot-image-inputs.sha256
FW=/system/android/framework
# board original work path (match it so the embedded cmdline strings match -> minimize .oat/.art diff)
WORK_DEFAULT="/opt/build-trees/.work/fn03-r29-boot-20260728T0635Z"
# boot classpath order (from dex2oat-a14.md OatHeader key-value, verbatim):
JARS_ORDER=(core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework)

DEX2OAT=""; JARS=""; WORK="$WORK_DEFAULT"; OUT=""; REF="$REF_DEFAULT"; CHECK=0
while [ $# -gt 0 ]; do case "$1" in
  --dex2oat) DEX2OAT="$2"; shift 2;;
  --jars-dir) JARS="$2"; shift 2;;
  --work) WORK="$2"; shift 2;;
  --out) OUT="$2"; shift 2;;
  --ref) REF="$2"; shift 2;;
  --check) CHECK=1; shift;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done
[ -n "$JARS" ] || { echo "usage: t5_gen_image.sh --dex2oat <d> --jars-dir <dir> [--work <p>] [--out <dir>] | --check --jars-dir <dir>"; exit 2; }
[ -f "$REF" ] || { echo "MISSING ref $REF"; exit 3; }
OUT="${OUT:-$WORK/products/arm64}"
SHA(){ if command -v sha256sum >/dev/null; then sha256sum "$1"|cut -d' ' -f1; else shasum -a 256 "$1"|cut -d' ' -f1; fi; }
refsha(){ grep -E "  $1\$" "$REF" | awk '{print $1}'; }

# ---- verify the 9 input jars vs reference ----
echo "[t5] verify 9 input jars vs $REF"; jbad=0
for j in "${JARS_ORDER[@]}"; do
  f="$JARS/$j.jar"; [ -f "$f" ] || { echo "  MISSING jar $f"; jbad=$((jbad+1)); continue; }
  a=$(SHA "$f"); e=$(refsha "$j.jar")
  [ "$a" = "$e" ] && echo "  OK   $j.jar" || { echo "  DIFF $j.jar (got $a want $e)"; jbad=$((jbad+1)); }
done
[ "$jbad" = 0 ] || { echo "[t5] FAIL: $jbad input jars missing/mismatch"; exit 3; }

# ---- assemble dex2oat cmdline (board-recorded) ----
# board cmdline uses --dex-file=<work>/incoming/<jar> (staged) + --dex-location=/system/android/framework/<jar>.
# Matching the <work>/incoming path minimizes .oat/.art path-string diffs (oc-t4: reduces to boot.art/boot.oat).
INCOMING="$WORK/incoming"
DEXARGS=()
for j in "${JARS_ORDER[@]}"; do DEXARGS+=(--dex-file="$INCOMING/$j.jar" --dex-location="$FW/$j.jar"); done
CMD=( "$DEX2OAT"
  --android-root=/system --instruction-set=arm64 --base=0x70000000 --compiler-filter=speed
  --runtime-arg -Xms64m --runtime-arg -Xmx512m --runtime-arg -Xverify:none
  --image="$OUT/boot.art" --oat-file="$OUT/boot.oat" "${DEXARGS[@]}" )

if [ "$CHECK" = 1 ]; then
  echo "[t5] CHECK ok: 9 jars match reference."
  echo "[t5] cmdline would be:"; printf '  %q' "${CMD[@]}"; echo
  echo "[t5] key-values (board boot.oat): compiler-filter=speed concurrent-copying=false debuggable=false native-debuggable=false requires-image=true apex-versions=(empty); isa-features bitmap=0x3 (no explicit --instruction-set-features)."
  echo "[t5] work=$WORK out=$OUT (matches board original path to minimize .oat/.art string diff)"
  exit 0
fi

[ -n "$DEX2OAT" ] && [ -x "$DEX2OAT" ] || { echo "[t5] MISSING/again --dex2oat (T3 output)"; exit 4; }
mkdir -p "$OUT" "$INCOMING"
# stage the 9 jars into <work>/incoming to match the board cmdline path form
for j in "${JARS_ORDER[@]}"; do cp -f "$JARS/$j.jar" "$INCOMING/$j.jar"; done
echo "[t5] staged 9 jars -> $INCOMING"
# host dex2oat needs its build's host libs on LD_LIBRARY_PATH (../lib64 next to the binary)
HOSTLIB="$(cd "$(dirname "$DEX2OAT")/../lib64" 2>/dev/null && pwd)"
[ -n "$HOSTLIB" ] && export LD_LIBRARY_PATH="$HOSTLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "[t5] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[t5] running dex2oat -> $OUT"
"${CMD[@]}" 2>&1 | tail -5
[ $? = 0 ] || { echo "[t5] dex2oat FAILED"; exit 5; }

# ---- L1 compare the 27 outputs vs reference ----
echo "[t5] L1 compare 27 image files vs reference"
IMG=$(awk '{print $2}' "$REF" | grep -E '^arm64/.*\.(art|oat|vdex)$')
same=0; diff=0; missing=0; vdex_same=0; vdex_total=0
for rel in $IMG; do
  bn=$(basename "$rel"); f="$OUT/$bn"
  [ -f "$f" ] || { echo "  MISSING $bn"; missing=$((missing+1)); continue; }
  a=$(SHA "$f"); e=$(refsha "$rel")
  case "$bn" in *.vdex) vdex_total=$((vdex_total+1));; esac
  if [ "$a" = "$e" ]; then same=$((same+1)); case "$bn" in *.vdex) vdex_same=$((vdex_same+1));; esac
  else diff=$((diff+1)); echo "  DIFF $bn"; fi
done
echo "[t5] L1: same=$same diff=$diff missing=$missing (vdex $vdex_same/$vdex_total)"

# ---- L2 header assertions ----
BO="$OUT/boot.oat"; BA="$OUT/boot.art"
grep -aqE 'oat'$'\n''230' "$BO" && echo "[t5] boot.oat oat version 230 OK" || echo "[t5] FAIL boot.oat oat version"
grep -aqE 'art'$'\n''108' "$BA" && echo "[t5] boot.art image version 108 OK" || echo "[t5] FAIL boot.art image version"

echo "[t5] verdict: vdex L1 = $vdex_same/$vdex_total (accept iff 9/9); .oat/.art diffs expected"
echo "[t5]   cause of .oat/.art diff = OatHeader embeds dex2oat-cmdline path strings + source-tree fingerprint"
echo "[t5]   (oc-t4 official-r16: 9/27 byte-identical = all vdex; same-work-path reduces to boot.art/boot.oat only)."

# ---- pre-deploy gate (ACK95): G1 image<->BCP consistency + G2 compiled-code suspend-check ----
# Beyond L1 byte-identity, gate the freshly-generated image against a known-good REFERENCE image the way
# the board will load it: G1 = per-.oat recorded dex checksum vs the deploy-time BCP jars; G2 = probe-method
# suspend-check shape vs the reference (rejects the T5b implicit-suspend build). Configure via env: GATE_REF
# (reference image dir) is the minimum for G1; add GATE_OATDUMP + GATE_BCP [+ GATE_CAND_BCP] for G2;
# GATE_SWAP for jars shipped with the image; GATE_PLAN for a deploy-plan.json. Unset -> gate not run.
GATE="$HERE/image_predeploy_gate.py"
if [ -n "${GATE_PLAN:-}${GATE_REF:-}" ]; then
  gargs=(--image "$OUT")
  [ -n "${GATE_PLAN:-}" ]     && gargs+=(--plan "$GATE_PLAN")
  [ -n "${GATE_REF:-}" ]      && gargs+=(--reference "$GATE_REF")
  [ -n "${GATE_SWAP:-}" ]     && gargs+=(--swap "$GATE_SWAP")
  [ -n "${GATE_OATDUMP:-}" ]  && gargs+=(--oatdump "$GATE_OATDUMP")
  [ -n "${GATE_BCP:-}" ]      && gargs+=(--bcp-dir "$GATE_BCP")
  [ -n "${GATE_CAND_BCP:-}" ] && gargs+=(--cand-bcp-dir "$GATE_CAND_BCP")
  [ -n "${GATE_ARTLIB:-}" ]   && gargs+=(--art-lib "$GATE_ARTLIB")
  echo "[t5] pre-deploy gate: image_predeploy_gate.py ${gargs[*]}"
  python3 "$GATE" "${gargs[@]}" || { echo "[t5] PRE-DEPLOY GATE FAILED (see G1/G2 above)"; exit 7; }
  echo "[t5] pre-deploy gate PASS"
fi

[ "$vdex_same" = 9 ] && exit 0 || exit 6
