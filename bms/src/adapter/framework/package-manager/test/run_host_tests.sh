#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
JNI_DIR="$PACKAGE_DIR/jni"
OUT_DIR="$(cd "$PACKAGE_DIR/../.." && pwd)/out/package-manager-host-tests"
OPENSSL_ROOT="${OPENSSL_ROOT:-/opt/homebrew/opt/openssl@3}"

mkdir -p "$OUT_DIR"
python3 "$SCRIPT_DIR/test_apk_label_projection_contract.py"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -I"$JNI_DIR" -I"$OPENSSL_ROOT/include" \
    "$JNI_DIR/apk_verify_result.cpp" "$SCRIPT_DIR/test_apk_verify_result.cpp" \
    -L"$OPENSSL_ROOT/lib" -Wl,-rpath,"$OPENSSL_ROOT/lib" -lcrypto \
    -o "$OUT_DIR/test_apk_verify_result"
"$OUT_DIR/test_apk_verify_result"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -I"$JNI_DIR" \
    "$JNI_DIR/game_install_plan_wire.cpp" "$SCRIPT_DIR/test_game_install_plan_wire.cpp" \
    -o "$OUT_DIR/test_game_install_plan_wire"
"$OUT_DIR/test_game_install_plan_wire"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -I"$JNI_DIR" \
    "$JNI_DIR/prepass_context_wire.cpp" "$SCRIPT_DIR/test_prepass_context_wire.cpp" \
    -o "$OUT_DIR/test_prepass_context_wire"
"$OUT_DIR/test_prepass_context_wire"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -I"$JNI_DIR" \
    "$SCRIPT_DIR/test_launcher_activity.cpp" \
    -o "$OUT_DIR/test_launcher_activity"
"$OUT_DIR/test_launcher_activity"

# Fn01 install-route app data dir provisioner (appspawn-x sandbox mount
# sources): three OH-conventional roots, exact mode/owner, typed failures.
PROVISIONER_SCRATCH="$OUT_DIR/app-data-dir-scratch"
rm -rf "$PROVISIONER_SCRATCH"
mkdir -p "$PROVISIONER_SCRATCH"
clang++ -std=c++17 -Wall -Wextra -Werror \
    -I"$JNI_DIR" \
    "$JNI_DIR/app_data_dir_provisioner.cpp" "$SCRIPT_DIR/test_app_data_dir_provisioner.cpp" \
    -o "$OUT_DIR/test_app_data_dir_provisioner"
"$OUT_DIR/test_app_data_dir_provisioner" "$PROVISIONER_SCRATCH"
