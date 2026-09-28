#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
WORK_DIR="${TMPDIR:-/tmp}/fn01-a06-host-$$"
trap 'rm -rf "$WORK_DIR"' EXIT HUP INT TERM
mkdir -p "$WORK_DIR"

CXX="${CXX:-c++}"
CC="${CC:-cc}"
"$CC" -std=c11 -O2 -Wall -Wextra -Werror \
    -I"$ROOT/install_plan/include" \
    -c "$ROOT/install_plan/src/sha256.c" \
    -o "$WORK_DIR/sha256.o"
"$CXX" -std=c++20 -O2 -Wall -Wextra -Werror -pthread \
    -DFN01_ENABLE_REFERENCE_FIXTURES \
    -I"$ROOT/component_resolver/include" \
    -I"$ROOT/package_transaction/include" \
    -I"$ROOT/install_plan/include" \
    "$ROOT/component_resolver/src/component_resolver_v1.cpp" \
    "$ROOT/component_resolver/src/component_resolver_runtime_v1.cpp" \
    "$ROOT/component_resolver/tests/component_resolver_host_test.cpp" \
    "$ROOT/package_transaction/src/package_transaction.cpp" \
    "$WORK_DIR/sha256.o" \
    -o "$WORK_DIR/component_resolver_host_test"

"$WORK_DIR/component_resolver_host_test"
python3 "$ROOT/component_resolver/tests/component_resolver_entry_audit.py"
