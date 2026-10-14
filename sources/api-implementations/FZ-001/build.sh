#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == --help ]]; then
  echo 'OH_ROOT=<restored OH6.1 kit> AOSP_ROOT=<AOSP14 headers> BUILD_OUT=<new absolute directory> ./build.sh'
  echo 'Builds the archived installer translation units. BMS kit/ninja build is separately documented in BUILD.md.'
  exit 0
fi
: "${OH_ROOT:?restored OH6.1 kit required}" "${AOSP_ROOT:?AOSP source headers required}" "${BUILD_OUT:?new output directory required}"
[[ "$BUILD_OUT" == /* && ! -e "$BUILD_OUT" ]] || { echo 'BUILD_OUT must be a new absolute directory' >&2; exit 2; }
mkdir -p "$BUILD_OUT"
cp -R "$HERE/archive-source/adapter" "$BUILD_OUT/adapter"
export ADAPTER_ROOT="$BUILD_OUT/adapter" A="$AOSP_ROOT" BUILD_INNER_INVOKED=1
export APK_INSTALLER_BUILD_TMP="$BUILD_OUT/objects"
bash "$HERE/build-evidence/adapter/build/inner/compile_apk_installer.sh.original.txt" 2>&1 | tee "$BUILD_OUT/build.log"

# The historical producer can continue after one failed translation unit.
# Reject partial compilation even if its final link/list command returns zero.
python3 - "$BUILD_OUT/build.log" <<'PYCHECK'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text()
counts = re.findall(r'^  Compiled: (\d+)/(\d+)\s*$', text, re.M)
if len(counts) != 1 or int(counts[0][0]) == 0 or counts[0][0] != counts[0][1]:
    raise SystemExit('Incomplete original compilation: ' + repr(counts))
if not re.search(r'Linking libapk_installer\.so\.\.\. OK', text):
    raise SystemExit('Original installer link did not report success')
PYCHECK
