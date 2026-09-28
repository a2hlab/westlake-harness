#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FRAMEWORK_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
OUT_DIR=${FN05_FN11_HARNESS_OUT:-"$FRAMEWORK_DIR/../../../.work/fn05-fn11-contract"}
HOST_CXX=${CXX:-c++}
OH_NATIVE_ROOT=${OHOS_NATIVE_ROOT:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}
TARGET_CXX=${OHOS_TARGET_CXX:-"$OH_NATIVE_ROOT/llvm/bin/aarch64-unknown-linux-ohos-clang++"}

mkdir -p "$OUT_DIR"

COMMON_SOURCES=(
  "$FRAMEWORK_DIR/window/jni/finished_token_ledger.cpp"
  "$FRAMEWORK_DIR/window/input_contract/input_contract_harness.cpp"
  "$FRAMEWORK_DIR/system-service/capability/typed_service_capability.cpp"
  "$SCRIPT_DIR/local_six_contract_harness.cpp"
)
COMMON_INCLUDES=(
  -I"$FRAMEWORK_DIR/window/jni"
  -I"$FRAMEWORK_DIR/window/input_contract"
  -I"$FRAMEWORK_DIR/system-service/capability"
)

"$HOST_CXX" -std=c++17 -O2 -Wall -Wextra -Werror -pthread \
  "${COMMON_INCLUDES[@]}" "${COMMON_SOURCES[@]}" \
  -o "$OUT_DIR/fn05_fn11_contract_harness_host"
"$OUT_DIR/fn05_fn11_contract_harness_host"

"$TARGET_CXX" -std=c++17 -O2 -Wall -Wextra -Werror -pthread \
  "${COMMON_INCLUDES[@]}" "${COMMON_SOURCES[@]}" \
  -o "$OUT_DIR/fn05_fn11_contract_harness_ohos_arm64"

file "$OUT_DIR/fn05_fn11_contract_harness_ohos_arm64"
sha256sum "$OUT_DIR/fn05_fn11_contract_harness_host" \
  "$OUT_DIR/fn05_fn11_contract_harness_ohos_arm64"
