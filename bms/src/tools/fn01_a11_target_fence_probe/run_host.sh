#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
BUILD_ROOT=${1:-"$REPO_ROOT/src/adapter/.work/fn01-a11-target-fence-host"}
STATE_ROOT="$BUILD_ROOT/state"
ARTIFACT="$BUILD_ROOT/fn01_a11_target_fence_probe"
EVIDENCE="$BUILD_ROOT/host-run.jsonl"

mkdir -p "$BUILD_ROOT"
rm -rf "$STATE_ROOT"

PM="$REPO_ROOT/src/adapter/framework/package-manager"
INCLUDES=(
  -I"$PM/install_plan/include"
  -I"$PM/package_transaction/include"
  -I"$PM/package_query/include"
  -I"$PM/component_resolver/include"
  -I"$PM/package_info/include"
  -I"$PM/application_info/include"
  -I"$PM/runtime_path_descriptor/include"
)
SOURCES=(
  "$PM/package_transaction/src/package_transaction_v1.cpp"
  "$PM/package_query/src/package_query_v1.cpp"
  "$PM/component_resolver/src/component_resolver_v1.cpp"
  "$PM/package_info/src/package_info_v1.cpp"
  "$PM/application_info/src/application_info_v1.cpp"
  "$PM/runtime_path_descriptor/src/runtime_path_descriptor_v1.cpp"
  "$SCRIPT_DIR/fn01_a11_target_fence_probe.cpp"
)

CC_BIN=${CC:-clang}
CXX_BIN=${CXX:-clang++}
"$CC_BIN" -std=c11 -Wall -Wextra -Werror \
  -I"$PM/install_plan/include" \
  -c "$PM/install_plan/src/sha256.c" -o "$BUILD_ROOT/sha256.o"
"$CXX_BIN" -std=c++17 -DFN01_ENABLE_REFERENCE_FIXTURES=1 \
  -Wall -Wextra -Werror -fsanitize=address,undefined \
  "${INCLUDES[@]}" "${SOURCES[@]}" "$BUILD_ROOT/sha256.o" \
  -o "$ARTIFACT"

OPERATIONS=(fixture_prepare query resolver launcher token process)
{
  for operation in "${OPERATIONS[@]}"; do
    "$ARTIFACT" "$STATE_ROOT" "$operation"
  done
} | tee "$EVIDENCE"
echo "HOST_ARTIFACT=$ARTIFACT"
echo "HOST_EVIDENCE=$EVIDENCE"
