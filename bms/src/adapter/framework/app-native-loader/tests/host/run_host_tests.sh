#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
SRC="$ROOT/framework/app-native-loader"
OUT="${ANL_HOST_TEST_OUT:-$ROOT/out/app_native_loader_host_tests}"
CC="${HOST_CC:-cc}"
BIN="$OUT/app_native_loader_host_test"
LOG="$OUT/test.log"

mkdir -p "$OUT"

if ! sed -n '1,20p' "$SRC/src/app_native_loader.c" | \
    rg -q '^#define _XOPEN_SOURCE 700$'; then
  echo "FAIL static gate: app-native-loader must own its X/Open-700 API contract" \
    | tee -a "$LOG"
  exit 1
fi

"$CC" \
  -D_GNU_SOURCE \
  -std=c11 \
  -Wall \
  -Wextra \
  -Werror \
  -I"$SRC/tests/host/include" \
  -I"$SRC/include" \
  -I"$SRC/tests/host" \
  -I"$ROOT/framework/native-compat/bionic-pthread-bridge/include" \
  "$SRC/src/app_native_loader.c" \
  "$SRC/tests/host/mock_dlns.c" \
  "$SRC/tests/host/app_native_loader_host_test.c" \
  -pthread \
  -o "$BIN"

set +e
"$BIN" 2>&1 | tee "$LOG"
test_rc="${PIPESTATUS[0]}"
set -e

if rg -n '(^|[^_[:alnum:]])dlopen[[:space:]]*\(' "$SRC/src/app_native_loader.c"; then
  echo "FAIL static gate: plain dlopen fallback found" | tee -a "$LOG"
  exit 1
fi
rg -n 'mode[[:space:]]*&[[:space:]]*RTLD_GLOBAL' "$SRC/src/app_native_loader.c" >>"$LOG"
rg -n '/data/local/tmp' "$SRC/src/app_native_loader.c" >>"$LOG"
if rg -n '(^|[^_[:alnum:]])(dlns_create2|dlns_set_namespace_.*|dlns_inherit|dlopen_ns)[[:space:]]*\(' \
    "$SRC/src/app_native_loader.c"; then
  echo "FAIL static gate: sealed app-native-loader directly owns namespace operations" \
    | tee -a "$LOG"
  exit 1
fi
rg -n 'namespace_host_ops\.create_configured_namespaces[[:space:]]*\(' \
  "$SRC/src/app_native_loader.c" >>"$LOG"
rg -n 'namespace_host_ops\.open_namespace[[:space:]]*\(' \
  "$SRC/src/app_native_loader.c" >>"$LOG"
rg -n 'validate_archive_search_path' "$SRC/src/app_native_loader.c" >>"$LOG"
echo "PASS static gates" | tee -a "$LOG"

exit "$test_rc"
