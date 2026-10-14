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
mkdir -p "$BUILD_OUT/classes"
"${JAVAC:-javac}" -source 8 -target 8 -d "$BUILD_OUT/classes" "$HERE/src/android/net/ssl/SSLSockets.java" 2>&1 | tee "$BUILD_OUT/build.log"
