#!/usr/bin/env bash
set -euo pipefail
if [ "${U14_PLAN_EXECUTE:-}" != "outer-approved-hw248-only" ]; then
  echo 'DISABLED: plan only; require explicit outer authorization and U14_PLAN_EXECUTE=outer-approved-hw248-only'
  exit 78
fi
RUN=${1:?run number 1 or 2}
case "$RUN" in 1|2) ;; *) echo 'Invalid run number'; exit 2;; esac
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || exit 3
[ "$(hostname -s)" = ecs-9f6c ] || { echo 'Wrong machine; never use a2hlab during window'; exit 3; }
export HOME=$LAB_HOME
export U14_ROOT="$HOME/u14-bt-bake-0349-87cf-v1" U14_RUN="$RUN"
ROOT="$U14_ROOT"
WORK="$ROOT/work"
DEX="$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64"
DRIVER="$HOME/cc-wiki-t5/tool/t5_gen_image.sh"
[ -d "$ROOT/jars9" ] && [ -d "$ROOT/plan" ] && [ ! -e "$ROOT/run$RUN" ] || exit 4
[ ! -L "$ROOT" ] && [ ! -L "$WORK" ] || exit 4
printf '%s  %s\n' ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b "$DEX" \
  14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46 "$DRIVER" | sha256sum -c -
(cd "$ROOT/jars9" && sha256sum -c "$ROOT/plan/inputs/jars9.sha256")
[ "$(find "$ROOT/jars9" -maxdepth 1 -type f -name '*.jar' | wc -l)" -eq 9 ] || exit 4
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
printf '[u14-bake] start=%s run=%s host=%s work=%s\n' "$(date -Is)" "$RUN" "$(hostname)" "$WORK"
uname -a
cat /etc/os-release
sha256sum "$DEX" "$DRIVER" "$ROOT/plan/dex2oat-tee.sh" "$ROOT/plan/planned-bake.sh" "$ROOT/plan/inputs/t5-ref-u14.sha256"
export LD_LIBRARY_PATH="$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/lib64"
ldd "$DEX" | tee "$ROOT/logs/ldd-run$RUN.txt"
if grep -q 'not found' "$ROOT/logs/ldd-run$RUN.txt"; then exit 5; fi
find "$LD_LIBRARY_PATH" -type f \( -name '*.so' -o -name '*.so.*' \) -print0 | sort -z | xargs -0 sha256sum > "$ROOT/logs/hostlibs-run$RUN.sha256"
if [ "$RUN" = 2 ]; then
  [ -d "$ROOT/run1" ] || exit 4
  cmp "$ROOT/logs/hostlibs-run1.sha256" "$ROOT/logs/hostlibs-run2.sha256"
fi
rm -rf -- "$WORK"
mkdir -p "$WORK"
set +e
bash "$DRIVER" --dex2oat "$ROOT/plan/dex2oat-tee.sh" --jars-dir "$ROOT/jars9" --work "$WORK" --ref "$ROOT/plan/inputs/t5-ref-u14.sha256"
DRIVER_RC=$?
set -e
printf '{"t5_exit_code":%s}\n' "$DRIVER_RC" > "$ROOT/logs/t5-run$RUN.status.json"
python3 - "$ROOT/logs/dex2oat-run$RUN.status.json" <<'PY'
import json
import sys
status = json.load(open(sys.argv[1]))
if status != {"dex2oat_exit_code": 0, "tee_exit_code": 0}:
    raise SystemExit("Compiler/live-tee failed; do not select partial outputs")
PY
case "$DRIVER_RC" in 0|6) ;; *) echo "Unexpected frozen-driver rc=$DRIVER_RC; stop"; exit 6;; esac
[ "$(find "$WORK/products/arm64" -maxdepth 1 -type f | wc -l)" -eq 27 ] || exit 7
[ "$(find "$WORK/products/arm64" -maxdepth 1 -type f -size 0 | wc -l)" -eq 0 ] || exit 7
cp -a "$WORK/products/arm64" "$ROOT/run$RUN"
(cd "$ROOT/run$RUN" && sha256sum *) | tee "$ROOT/logs/image-sha256-run$RUN.txt"
printf '[u14-bake] recorded, NOT approved; t5_rc=%s; G1/G2/RB/T4B/repro/paired-receipt pending\n' "$DRIVER_RC"
printf '[u14-bake] end=%s\n' "$(date -Is)"
