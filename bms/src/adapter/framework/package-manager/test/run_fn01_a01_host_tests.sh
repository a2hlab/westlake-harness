#!/usr/bin/env bash
# Developer-owned host build/test for Fn01.A01. This never emits a formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A01_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a01-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A01 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi

mkdir -p "$OUT/bin" "$OUT/obj"
RUN_ROOT=$(mktemp -d "$OUT/run.XXXXXX")
cleanup() {
    rm -rf "$RUN_ROOT"
}
trap cleanup EXIT
RUN_ROOT=$(cd "$RUN_ROOT" && pwd -P)

INCLUDE_TX="$PACKAGE_DIR/package_transaction/include"
INCLUDE_SHA="$PACKAGE_DIR/install_plan/include"
SOURCE_TX="$PACKAGE_DIR/package_transaction/src/package_transaction.cpp"
SOURCE_SHA="$PACKAGE_DIR/install_plan/src/sha256.c"
TEST_SOURCE="$PACKAGE_DIR/package_transaction/tests/package_transaction_host_test.cpp"
BINARY="$OUT/bin/package_transaction_host_test"

clang -std=c11 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_SHA" \
    -c "$SOURCE_SHA" \
    -o "$OUT/obj/sha256.o"

clang++ -std=c++17 -DFN01_ENABLE_REFERENCE_FIXTURES \
    -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_TX" -I"$INCLUDE_SHA" \
    "$SOURCE_TX" "$TEST_SOURCE" "$OUT/obj/sha256.o" \
    -o "$BINARY"

"$BINARY" "$RUN_ROOT"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_TX" -I"$INCLUDE_SHA" \
    "$PACKAGE_DIR/package_transaction/src/prepass_bundle.cpp" \
    "$PACKAGE_DIR/package_transaction/tests/prepass_bundle_host_test.cpp" \
    "$OUT/obj/sha256.o" \
    -o "$OUT/bin/prepass_bundle_host_test"
"$OUT/bin/prepass_bundle_host_test"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_TX" \
    "$PACKAGE_DIR/package_transaction/src/elf_prepass_analyzer.cpp" \
    "$PACKAGE_DIR/package_transaction/tests/elf_prepass_analyzer_host_test.cpp" \
    -o "$OUT/bin/elf_prepass_analyzer_host_test"
"$OUT/bin/elf_prepass_analyzer_host_test"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PACKAGE_DIR/jni" \
    "$PACKAGE_DIR/jni/apk_native_inventory_names.cpp" \
    "$PACKAGE_DIR/package_transaction/tests/native_inventory_host_test.cpp" \
    -o "$OUT/bin/native_inventory_host_test"
"$OUT/bin/native_inventory_host_test"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PACKAGE_DIR/jni" \
    "$PACKAGE_DIR/jni/prepass_context_wire.cpp" \
    "$PACKAGE_DIR/test/test_prepass_context_wire.cpp" \
    -o "$OUT/bin/prepass_context_wire_host_test"
"$OUT/bin/prepass_context_wire_host_test"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PACKAGE_DIR/jni" -I"$INCLUDE_TX" -I"$INCLUDE_SHA" \
    "$PACKAGE_DIR/jni/prepass_context_wire.cpp" \
    "$PACKAGE_DIR/jni/install_prepass_materializer.cpp" \
    "$PACKAGE_DIR/package_transaction/src/elf_prepass_analyzer.cpp" \
    "$PACKAGE_DIR/package_transaction/src/prepass_bundle.cpp" \
    "$PACKAGE_DIR/test/test_install_prepass_materializer.cpp" \
    "$OUT/obj/sha256.o" \
    -o "$OUT/bin/install_prepass_materializer_host_test"
"$OUT/bin/install_prepass_materializer_host_test"
python3 "$PACKAGE_DIR/package_transaction/tests/prepass_source_audit.py"

shasum -a 256 \
    "$PACKAGE_DIR/package_transaction/include/package_transaction.h" \
    "$SOURCE_TX" \
    "$TEST_SOURCE" \
    "$PACKAGE_DIR/package_transaction/include/prepass_bundle.h" \
    "$PACKAGE_DIR/package_transaction/include/prepass_wire.h" \
    "$PACKAGE_DIR/package_transaction/include/elf_prepass_analyzer.h" \
    "$PACKAGE_DIR/package_transaction/src/prepass_bundle.cpp" \
    "$PACKAGE_DIR/package_transaction/src/elf_prepass_analyzer.cpp" \
    "$PACKAGE_DIR/jni/apk_native_inventory.h" \
    "$PACKAGE_DIR/jni/apk_native_inventory.cpp" \
    "$PACKAGE_DIR/jni/apk_native_inventory_names.cpp" \
    "$PACKAGE_DIR/jni/prepass_context_wire.h" \
    "$PACKAGE_DIR/jni/prepass_context_wire.cpp" \
    "$PACKAGE_DIR/jni/install_prepass_materializer.h" \
    "$PACKAGE_DIR/jni/install_prepass_materializer.cpp" \
    "$SOURCE_SHA" \
    "$BINARY" \
    >"$OUT/artifacts.sha256"

echo "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A01 formal_verdict=NOT_ISSUED"
