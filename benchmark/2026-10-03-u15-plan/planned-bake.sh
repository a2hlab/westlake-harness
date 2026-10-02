#!/usr/bin/env bash
set -euo pipefail
if [ "${U15_PLAN_EXECUTE:-}" != "outer-approved-hw248-only" ]; then
  echo 'DISABLED: U15 preparation only; a separate outer execution authorization is required'
  exit 78
fi
RUN=${1:?run number 1 or 2}
case "$RUN" in 1|2) ;; *) echo 'Invalid run number'; exit 2;; esac
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || exit 3
[ "$(hostname -s)" = ecs-9f6c ] || { echo 'Wrong machine; never use a2hlab during window'; exit 3; }
export HOME="${HW248_HOME:?approved FZ-005 lab home must be supplied explicitly}"
[ "$(printf '%s' "$HOME" | sha256sum | cut -d ' ' -f 1)" = 4e5277d9907dc562d2135c48e53fa1ed5764ab628dae1e8e397499e708a1c102 ] || exit 3
export U15_ROOT="$HOME/u15-bitmap-9e55-v1" U15_RUN="$RUN"
ROOT="$U15_ROOT"
WORK="$ROOT/work"
DEX="$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64"
DRIVER="$HOME/cc-wiki-t5/tool/t5_gen_image.sh"
[ -d "$ROOT/jars9" ] && [ -d "$ROOT/plan" ] && [ ! -e "$ROOT/run$RUN" ] || exit 4
[ ! -L "$ROOT" ] && [ ! -L "$WORK" ] || exit 4
if [ "$RUN" = 2 ]; then [ -d "$ROOT/run1" ] || exit 4; fi
mkdir -p "$ROOT/logs"
[ ! -e "$ROOT/logs/bake-run$RUN.session.log" ] || exit 4
exec 3>&1 4>&2
exec > >(tee "$ROOT/logs/bake-run$RUN.session.log") 2>&1
SESSION_TEE_PID=$!
finish_session() {
  ORIGINAL_RC=$?
  trap - EXIT
  exec 1>&3 2>&4
  set +e
  wait "$SESSION_TEE_PID"
  SESSION_TEE_RC=$?
  printf '{"session_tee_exit_code":%s,"script_exit_code":%s}\n' "$SESSION_TEE_RC" "$ORIGINAL_RC" > "$ROOT/logs/session-run$RUN.status.json"
  if [ "$SESSION_TEE_RC" -ne 0 ]; then exit 8; fi
  exit "$ORIGINAL_RC"
}
trap finish_session EXIT
printf '[u15-bake] start=%s run=%s host=%s home=%s work=%s\n' "$(date -Is)" "$RUN" "$(hostname)" "$HOME" "$WORK"
uname -a
cat /etc/os-release
printf '%s  %s\n' ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b "$DEX" \
  14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46 "$DRIVER" | sha256sum -c -
sha256sum "$DEX" "$DRIVER" "$ROOT/plan/dex2oat-tee.sh" "$ROOT/plan/planned-bake.sh" "$ROOT/plan/inputs/t5-ref-u15.sha256"
(cd "$ROOT/jars9" && sha256sum -c "$ROOT/plan/inputs/jars9.sha256")
[ "$(find "$ROOT/jars9" -maxdepth 1 -type f -name '*.jar' | wc -l)" -eq 9 ] || exit 4
export LD_LIBRARY_PATH="$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/lib64"
ldd "$DEX" | tee "$ROOT/logs/ldd-run$RUN.txt"
if grep -q 'not found' "$ROOT/logs/ldd-run$RUN.txt"; then exit 5; fi
(cd "$LD_LIBRARY_PATH" && find . -type f \( -name '*.so' -o -name '*.so.*' \) -printf '%P\n' | LC_ALL=C sort | xargs sha256sum) > "$ROOT/logs/hostlibs-run$RUN.sha256"
cmp "$ROOT/plan/inputs/hostlibs.expected.sha256" "$ROOT/logs/hostlibs-run$RUN.sha256"
if [ "$RUN" = 2 ]; then cmp "$ROOT/logs/hostlibs-run1.sha256" "$ROOT/logs/hostlibs-run2.sha256"; fi
rm -rf -- "$WORK"
mkdir -p "$WORK"
set +e
bash "$DRIVER" --dex2oat "$ROOT/plan/dex2oat-tee.sh" --jars-dir "$ROOT/jars9" --work "$WORK" --ref "$ROOT/plan/inputs/t5-ref-u15.sha256"
DRIVER_RC=$?
set -e
printf '{"t5_exit_code":%s}\n' "$DRIVER_RC" > "$ROOT/logs/t5-run$RUN.status.json"
python3 - "$ROOT/logs/dex2oat-run$RUN.status.json" "$WORK/products/arm64" <<'PY'
import json
from pathlib import Path
import sys

status = json.load(open(sys.argv[1]))
if status != {"dex2oat_exit_code": 0, "tee_exit_code": 0}:
    raise SystemExit("Compiler/live-tee failed; do not select partial outputs")
segments = ["boot", "boot-core-libart", "boot-core-icu4j", "boot-okhttp", "boot-bouncycastle",
            "boot-apache-xml", "boot-adapter-mainline-stubs", "boot-framework", "boot-oh-adapter-framework"]
expected = {segment + "." + suffix for segment in segments for suffix in ["art", "oat", "vdex"]}
members = list(Path(sys.argv[2]).iterdir())
if {path.name for path in members} != expected or any(not path.is_file() or path.is_symlink() or path.stat().st_size == 0 for path in members):
    raise SystemExit("Incomplete or unexpected image group")
PY
case "$DRIVER_RC" in 0|6) ;; *) echo "Unexpected frozen-driver rc=$DRIVER_RC; stop"; exit 6;; esac
cp -a "$WORK/products/arm64" "$ROOT/run$RUN"
(cd "$ROOT/run$RUN" && sha256sum *) | tee "$ROOT/logs/image-sha256-run$RUN.txt"
printf '[u15-bake] recorded, NOT approved; t5_rc=%s; G1/G2/RB/T4B/repro/paired-receipt pending\n' "$DRIVER_RC"
printf '[u15-bake] end=%s\n' "$(date -Is)"
