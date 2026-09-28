#!/usr/bin/env bash
# Developer-owned Fn01.A09 P/N/F/restart build and test. Never a formal PASS.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${FN01_A09_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a09-host}

: "${FN01_A09_FIXTURE_PREFIX:?set a content-driven package namespace}"
: "${FN01_A09_PRIMARY_COMPONENT:?set an external launcher component}"
: "${FN01_A09_SECONDARY_COMPONENT:?set a distinct external launcher component}"
: "${FN01_A09_PRIMARY_LOCALE:?set an external primary locale}"
: "${FN01_A09_SECONDARY_LOCALE:?set a distinct external secondary locale}"

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: Fn01.A09 output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi

mkdir -p "$OUT/bin" "$OUT/obj" "$OUT/raw"
INCLUDE_PRESENTATION="$PACKAGE_DIR/launcher_presentation/include"
INCLUDE_SHA="$PACKAGE_DIR/install_plan/include"
SOURCE_PRESENTATION="$PACKAGE_DIR/launcher_presentation/src/launcher_presentation_v1.cpp"
SOURCE_SHA="$PACKAGE_DIR/install_plan/src/sha256.c"
TEST_SOURCE="$PACKAGE_DIR/launcher_presentation/tests/launcher_presentation_host_test.cpp"
BINARY="$OUT/bin/launcher_presentation_host_test"
RESULTS="$OUT/raw/results.jsonl"
RUNNER="$SCRIPT_DIR/run_fn01_a09_host_tests.sh"

clang -std=c11 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_SHA" -c "$SOURCE_SHA" -o "$OUT/obj/sha256.o"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$INCLUDE_PRESENTATION" -I"$INCLUDE_SHA" \
    "$SOURCE_PRESENTATION" "$TEST_SOURCE" "$OUT/obj/sha256.o" \
    -o "$BINARY"

printf '%s\n' \
    "clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined sha256.c" \
    "clang++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined launcher_presentation_v1.cpp launcher_presentation_host_test.cpp sha256.o" \
    "$BINARY RESULTS_JSONL FIXTURE_PREFIX PRIMARY_COMPONENT SECONDARY_COMPONENT PRIMARY_LOCALE SECONDARY_LOCALE" \
    >"$OUT/raw/commands.txt"
{
    uname -a
    clang --version
    clang++ --version
} >"$OUT/raw/environment.txt"
printf '%s\n' \
    "package_prefix=$FN01_A09_FIXTURE_PREFIX" \
    "primary_component=$FN01_A09_PRIMARY_COMPONENT" \
    "secondary_component=$FN01_A09_SECONDARY_COMPONENT" \
    "primary_locale=$FN01_A09_PRIMARY_LOCALE" \
    "secondary_locale=$FN01_A09_SECONDARY_LOCALE" \
    >"$OUT/raw/fixture-input.txt"

set +e
"$BINARY" "$RESULTS" "$FN01_A09_FIXTURE_PREFIX" \
    "$FN01_A09_PRIMARY_COMPONENT" "$FN01_A09_SECONDARY_COMPONENT" \
    "$FN01_A09_PRIMARY_LOCALE" "$FN01_A09_SECONDARY_LOCALE" \
    >"$OUT/raw/host-test.stdout" 2>"$OUT/raw/host-test.stderr"
STATUS=$?
set -e
cat "$OUT/raw/host-test.stdout"
cat "$OUT/raw/host-test.stderr" >&2
if [[ "$STATUS" -ne 0 ]]; then
    exit "$STATUS"
fi

shasum -a 256 \
    "$PACKAGE_DIR/launcher_presentation/include/launcher_presentation_v1.h" \
    "$SOURCE_PRESENTATION" "$TEST_SOURCE" "$SOURCE_SHA" "$RUNNER" "$BINARY" \
    "$RESULTS" "$OUT/raw/commands.txt" "$OUT/raw/environment.txt" \
    "$OUT/raw/fixture-input.txt" "$OUT/raw/host-test.stdout" \
    "$OUT/raw/host-test.stderr" \
    >"$OUT/input-source-results.sha256"

echo "DEVELOPER_HANDOFF_READY action=Fn01.A09 formal_verdict=NOT_ISSUED"
