#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/framework/native-loader-oh"
JNI="$ROOT/prebuilts/android/jni/include"
ANL="$ROOT/framework/app-native-loader/include"
OUT="${NATIVE_LOADER_REGISTRY_TEST_OUT:-$ROOT/out/native_loader_oh_registry_tests}"
CXX="${HOST_CXX:-c++}"
REPEATS="${NATIVE_LOADER_REGISTRY_REPEATS:-20}"
TIMEOUT_SECONDS="${NATIVE_LOADER_REGISTRY_TIMEOUT_SECONDS:-15}"

mkdir -p "$OUT"

run_with_watchdog() {
  local log="$1"
  shift
  "$@" >"$log" 2>&1 &
  local pid=$!
  (
    sleep "$TIMEOUT_SECONDS"
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
      sleep 1
      kill -KILL "$pid" 2>/dev/null || true
    fi
  ) &
  local watchdog=$!
  set +e
  wait "$pid"
  local rc=$?
  set -e
  kill "$watchdog" 2>/dev/null || true
  wait "$watchdog" 2>/dev/null || true
  if [ "$rc" -ne 0 ]; then
    cat "$log" >&2
    return "$rc"
  fi
}

build_and_repeat() {
  local mode="$1"
  shift
  local binary="$OUT/registry_${mode}"
  "$CXX" -std=c++17 -Wall -Wextra -Werror -pthread -g "$@" \
    -I"$SRC/include" -I"$SRC/src" -I"$JNI" -I"$ANL" \
    "$SRC/src/native_loader_registry.cpp" \
    "$SRC/src/system_loader.cpp" \
    "$SRC/src/native_loader.cpp" \
    "$SRC/tests/native_loader_registry_host_test.cpp" \
    -o "$binary"
  local iteration
  for iteration in $(seq 1 "$REPEATS"); do
    run_with_watchdog "$OUT/${mode}.${iteration}.log" "$binary"
    grep -q 'NativeLoader Profile B registry: .* 0 failures' \
      "$OUT/${mode}.${iteration}.log"
  done
  echo "NativeLoader registry ${mode}: ${REPEATS} bounded runs PASS"
}

mode="${1:-normal}"
case "$mode" in
  normal)
    build_and_repeat normal -O2
    ;;
  asan)
    build_and_repeat asan -O1 -fsanitize=address,undefined \
      -fno-omit-frame-pointer
    ;;
  tsan)
    build_and_repeat tsan -O1 -fsanitize=thread
    ;;
  all)
    build_and_repeat normal -O2
    build_and_repeat asan -O1 -fsanitize=address,undefined \
      -fno-omit-frame-pointer
    build_and_repeat tsan -O1 -fsanitize=thread
    ;;
  *)
    echo "usage: $0 [normal|asan|tsan|all]" >&2
    exit 2
    ;;
esac
