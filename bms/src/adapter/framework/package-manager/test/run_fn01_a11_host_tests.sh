#!/usr/bin/env bash
# Developer-owned host build/test for Fn01.A11. This never emits formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A11_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a11-host}
KEEP_STATE=${FN01_A11_KEEP_STATE:-0}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A11 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi

mkdir -p "$OUT/bin" "$OUT/obj" "$OUT/raw"
RUN_ROOT=$(mktemp -d "$OUT/state.XXXXXX")
cleanup() {
    if [[ "$KEEP_STATE" != "1" ]]; then
        rm -rf "$RUN_ROOT"
    fi
}
trap cleanup EXIT
RUN_ROOT=$(cd "$RUN_ROOT" && pwd -P)

INCLUDE_TX="$PACKAGE_DIR/package_transaction/include"
INCLUDE_SHA="$PACKAGE_DIR/install_plan/include"
SOURCE_TX="$PACKAGE_DIR/package_transaction/src/package_transaction.cpp"
SOURCE_SHA="$PACKAGE_DIR/install_plan/src/sha256.c"
TEST_SOURCE="$PACKAGE_DIR/package_transaction/tests/package_restart_recovery_host_test.cpp"
BINARY="$OUT/bin/package_restart_recovery_host_test"
RUNNER="$SCRIPT_DIR/run_fn01_a11_host_tests.sh"

clang -std=c11 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_SHA" \
    -c "$SOURCE_SHA" \
    -o "$OUT/obj/sha256.o"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -DFN01_ENABLE_REFERENCE_FIXTURES=1 \
    -I"$INCLUDE_TX" -I"$INCLUDE_SHA" \
    "$SOURCE_TX" "$TEST_SOURCE" "$OUT/obj/sha256.o" \
    -o "$BINARY"

printf '%s\n' \
    "clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined sha256.c" \
    "clang++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -DFN01_ENABLE_REFERENCE_FIXTURES=1 package_transaction.cpp package_restart_recovery_host_test.cpp" \
    "$BINARY $RUN_ROOT" \
    >"$OUT/raw/commands.txt"
{
    uname -a
    clang --version
    clang++ --version
} >"$OUT/raw/environment.txt"

set +e
"$BINARY" "$RUN_ROOT" \
    >"$OUT/raw/host-test.stdout" \
    2>"$OUT/raw/host-test.stderr"
TEST_STATUS=$?
set -e
cat "$OUT/raw/host-test.stdout"
cat "$OUT/raw/host-test.stderr" >&2
if [[ "$TEST_STATUS" -ne 0 ]]; then
    exit "$TEST_STATUS"
fi
cp "$RUN_ROOT/results.jsonl" "$OUT/raw/results.jsonl"
printf '%s\n' "$RUN_ROOT" >"$OUT/raw/state-root.txt"
find "$RUN_ROOT" -type f -print | LC_ALL=C sort \
    >"$OUT/raw/state-files.txt"
while IFS= read -r state_file; do
    shasum -a 256 "$state_file"
done <"$OUT/raw/state-files.txt" >"$OUT/raw/state-files.sha256"

shasum -a 256 \
    "$PACKAGE_DIR/package_transaction/include/package_transaction.h" \
    "$SOURCE_TX" \
    "$TEST_SOURCE" \
    "$SOURCE_SHA" \
    "$RUNNER" \
    "$BINARY" \
    "$OUT/raw/results.jsonl" \
    "$OUT/raw/commands.txt" \
    "$OUT/raw/environment.txt" \
    "$OUT/raw/host-test.stdout" \
    "$OUT/raw/host-test.stderr" \
    "$OUT/raw/state-files.sha256" \
    >"$OUT/input-source-results.sha256"

echo "DEVELOPER_HANDOFF_READY action=Fn01.A11 formal_verdict=NOT_ISSUED"
