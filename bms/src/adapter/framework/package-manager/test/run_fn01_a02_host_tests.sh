#!/usr/bin/env bash
# Developer-owned host build/test for Fn01.A02. This never emits a formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A02_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a02-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A02 output escaped project: $OUT" >&2; exit 2 ;;
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
INCLUDE_QUERY="$PACKAGE_DIR/package_query/include"
INCLUDE_SHA="$PACKAGE_DIR/install_plan/include"
SOURCE_TX="$PACKAGE_DIR/package_transaction/src/package_transaction.cpp"
SOURCE_QUERY="$PACKAGE_DIR/package_query/src/package_query_v1.cpp"
SOURCE_SHA="$PACKAGE_DIR/install_plan/src/sha256.c"
TEST_SOURCE="$PACKAGE_DIR/package_query/tests/package_query_host_test.cpp"
BINARY="$OUT/bin/package_query_host_test"

clang -std=c11 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_SHA" \
    -c "$SOURCE_SHA" \
    -o "$OUT/obj/sha256.o"

clang++ -std=c++17 -DFN01_ENABLE_REFERENCE_FIXTURES \
    -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_TX" -I"$INCLUDE_QUERY" -I"$INCLUDE_SHA" \
    "$SOURCE_TX" "$SOURCE_QUERY" "$TEST_SOURCE" "$OUT/obj/sha256.o" \
    -o "$BINARY"

"$BINARY" "$RUN_ROOT"

shasum -a 256 \
    "$INCLUDE_TX/package_transaction.h" \
    "$INCLUDE_QUERY/package_query_v1.h" \
    "$SOURCE_TX" \
    "$SOURCE_QUERY" \
    "$TEST_SOURCE" \
    "$SOURCE_SHA" \
    "$BINARY" \
    >"$OUT/artifacts.sha256"

echo "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A02 formal_verdict=NOT_ISSUED"
