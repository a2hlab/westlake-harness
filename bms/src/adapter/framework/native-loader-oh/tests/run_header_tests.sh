#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/framework/native-loader-oh"
JNI="$ROOT/prebuilts/android/jni/include"
OUT="${NATIVE_LOADER_HEADER_TEST_OUT:-$ROOT/out/native_loader_oh_header_tests}"
CC="${HOST_CC:-cc}"
CXX="${HOST_CXX:-c++}"

mkdir -p "$OUT"

"$CC" -std=c11 -Wall -Wextra -Werror \
  -I"$SRC/include" -I"$JNI" \
  -c "$SRC/tests/header_c_probe.c" -o "$OUT/header_c_probe.o"

"$CXX" -std=c++17 -Wall -Wextra -Werror \
  -I"$SRC/include" -I"$JNI" \
  -c "$SRC/tests/header_cpp_probe.cpp" -o "$OUT/header_cpp_probe.o"

"$CXX" -std=c++17 -Wall -Wextra -Werror \
  -I"$SRC/include" -I"$ROOT/framework/android-runtime/include" -I"$JNI" \
  "$ROOT/framework/android-runtime/src/com_android_internal_os_ClassLoaderFactory.cpp" \
  "$SRC/tests/classloader_factory_host_test.cpp" \
  -o "$OUT/classloader_factory_host_test"
"$OUT/classloader_factory_host_test"

for symbol in InitializeNativeLoader ResetNativeLoader \
              CreateClassLoaderNamespace OpenNativeLibrary \
              CloseNativeLibrary NativeLoaderFreeErrorMessage; do
  grep -Eq "^[[:space:]]+$symbol;" "$SRC/native_loader.map"
done

if rg -n '_ZN7android|namespace[[:space:]]+android.*OpenNativeLibrary' \
    "$SRC/native_loader.map"; then
  echo "C++-mangled NativeLoader export leaked into Profile B map" >&2
  exit 1
fi

python3 "$SRC/tests/verify_bridge_policy.py"

echo "NativeLoader Profile B header gates: PASS"
