#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == --help ]]; then
  echo 'BUILD_OUT=<new absolute directory> [ANDROID_JAR=<pinned compile jar>] [JAVAC=javac] ./build.sh'
  echo 'Compiles the exact frozen API unit; it does not claim a reconstructed multi-fix runtime JAR or boot image.'
  exit 0
fi
: "${BUILD_OUT:?new output directory required}"
[[ "$BUILD_OUT" == /* && ! -e "$BUILD_OUT" ]] || { echo 'BUILD_OUT must be new and absolute' >&2; exit 2; }
: "${ANDROID_JAR:?the SHA-pinned compile android.jar from build-evidence/build-result-j7b.json is required}"
python3 - "$ANDROID_JAR" <<'CHECK'
import hashlib,sys
from pathlib import Path
expected='d9eb9da824d9e247a352f570f01e1169e725b2954bca9e283a71786c59b59f9a'
assert hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()==expected, 'compile android.jar SHA mismatch'
CHECK
ARGS=(-classpath "$ANDROID_JAR")
mkdir -p "$BUILD_OUT/classes"
"${JAVAC:-javac}" -source 8 -target 8 "${ARGS[@]}" -d "$BUILD_OUT/classes" "$HERE/src/VibratorFetcher.java" 2>&1 | tee "$BUILD_OUT/build.log"
