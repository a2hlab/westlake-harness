#!/usr/bin/env bash
# Developer-owned Fn01.A16 P/N/F/restart build and test. Never a formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A16_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a16-host}

: "${FN01_A16_FIXTURE_PREFIX:?set a content-driven package namespace}"
: "${FN01_A16_FIXTURE_MEMBERS:?set the fixture member count}"
: "${FN01_A16_PAGE_SIZE:?set the requested page size}"

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A16 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi

mkdir -p "$OUT/bin" "$OUT/obj" "$OUT/raw"
INCLUDE_LIST="$PACKAGE_DIR/package_list/include"
INCLUDE_QUERY="$PACKAGE_DIR/package_query/include"
INCLUDE_TX="$PACKAGE_DIR/package_transaction/include"
INCLUDE_SHA="$PACKAGE_DIR/install_plan/include"
SOURCE_LIST="$PACKAGE_DIR/package_list/src/package_list_v1.cpp"
SOURCE_SHA="$PACKAGE_DIR/install_plan/src/sha256.c"
TEST_SOURCE="$PACKAGE_DIR/package_list/tests/package_list_host_test.cpp"
BINARY="$OUT/bin/package_list_host_test"
RESULTS="$OUT/raw/results.jsonl"
RUNNER="$SCRIPT_DIR/run_fn01_a16_host_tests.sh"

clang -std=c11 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_SHA" -c "$SOURCE_SHA" -o "$OUT/obj/sha256.o"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_LIST" -I"$INCLUDE_QUERY" -I"$INCLUDE_TX" -I"$INCLUDE_SHA" \
    "$SOURCE_LIST" "$TEST_SOURCE" "$OUT/obj/sha256.o" \
    -o "$BINARY"

printf '%s\n' \
    "clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined sha256.c" \
    "clang++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined package_list_v1.cpp package_list_host_test.cpp sha256.o" \
    "$BINARY RESULTS_JSONL FIXTURE_PREFIX FIXTURE_MEMBERS PAGE_SIZE" \
    >"$OUT/raw/commands.txt"
{
    uname -a
    clang --version
    clang++ --version
} >"$OUT/raw/environment.txt"
printf '%s\n' \
    "package_prefix=$FN01_A16_FIXTURE_PREFIX" \
    "member_count=$FN01_A16_FIXTURE_MEMBERS" \
    "page_size=$FN01_A16_PAGE_SIZE" \
    >"$OUT/raw/fixture-input.txt"

set +e
"$BINARY" "$RESULTS" "$FN01_A16_FIXTURE_PREFIX" \
    "$FN01_A16_FIXTURE_MEMBERS" "$FN01_A16_PAGE_SIZE" \
    >"$OUT/raw/host-test.stdout" 2>"$OUT/raw/host-test.stderr"
STATUS=$?
set -e
cat "$OUT/raw/host-test.stdout"
cat "$OUT/raw/host-test.stderr" >&2
if [[ "$STATUS" -ne 0 ]]; then
    exit "$STATUS"
fi

shasum -a 256 \
    "$PACKAGE_DIR/package_list/include/package_list_v1.h" \
    "$SOURCE_LIST" "$TEST_SOURCE" "$SOURCE_SHA" "$RUNNER" "$BINARY" \
    "$RESULTS" "$OUT/raw/commands.txt" "$OUT/raw/environment.txt" \
    "$OUT/raw/fixture-input.txt" "$OUT/raw/host-test.stdout" \
    "$OUT/raw/host-test.stderr" \
    >"$OUT/input-source-results.sha256"

echo "DEVELOPER_HANDOFF_READY action=Fn01.A16 formal_verdict=NOT_ISSUED"
