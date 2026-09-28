#!/usr/bin/env bash
set -euo pipefail

MODULE=$(cd "$(dirname "$0")/.." && pwd)
ADAPTER=$(cd "$MODULE/../../.." && pwd)
REGISTRY="$ADAPTER/framework/native-compat/thread-guard-registry"
BUILD_DIR="${TMPDIR:-/tmp}/westlake-jni-attach-admission-$$"
CXX=${CXX:-c++}
trap 'rm -rf "$BUILD_DIR"' EXIT
mkdir -p "$BUILD_DIR"

"$CXX" \
    -std=c++17 -Wall -Wextra -Werror -pedantic \
    -I"$MODULE/include" \
    -I"$REGISTRY/include" \
    -I"$ADAPTER/prebuilts/android/jni/include" \
    "$MODULE/src/jni_attach_admission.cpp" \
    "$MODULE/tests/jni_attach_admission_test.cpp" \
    -o "$BUILD_DIR/jni_attach_admission_test"

"$BUILD_DIR/jni_attach_admission_test"
