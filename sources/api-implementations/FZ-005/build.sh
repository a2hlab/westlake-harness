#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == --help ]]; then
  echo 'AOSP_R1_ROOT=<restored AOSP14 tree> JARS_DIR=<9 pinned jars> OUT_DIR=<new output> ./build.sh'
  echo 'The existing original reproduction driver rebuilds the host toolchain and runs its original gates. Supply its documented reference inputs.'
  exit 0
fi
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
: "${AOSP_R1_ROOT:?restored AOSP tree required}" "${JARS_DIR:?pinned jars required}" "${OUT_DIR:?new output required}"
[[ ! -e "$OUT_DIR" ]] || { echo 'OUT_DIR must be new' >&2; exit 2; }
export SERIES_DIR="$HERE/frozen" CHECK_SERIES="$REPO_ROOT/knowledge/toolchains/art-r155/check_series.py"
# Preserve recorded evidence mode and bytes; prepare an executable scratch copy.
INPUT_DIR="${OUT_DIR}.source-inputs"
[[ ! -e "$INPUT_DIR" ]] || { echo 'source-inputs directory must be new' >&2; exit 2; }
mkdir -p "$INPUT_DIR"
cp "$HERE/build-evidence/t5_gen_image.frozen.sh.original.txt" "$INPUT_DIR/t5_gen_image.sh"
chmod 700 "$INPUT_DIR/t5_gen_image.sh"
export T5_GEN="$INPUT_DIR/t5_gen_image.sh"
python3 - "$T5_GEN" <<'PYHASH'
import hashlib, pathlib, sys
assert hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() == '14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46'
PYHASH
export EXPECT_DEX2OAT='ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b'
export RB_GATE="$REPO_ROOT/knowledge/toolchains/art-r155/check_boot_oat_rb.py"
export T4B_GATE="$REPO_ROOT/knowledge/toolchains/art-r155/t4b_build_switch_gate.py"
exec bash "$REPO_ROOT/scripts/lab/reproduce_dex2oat_toolchain.sh"
