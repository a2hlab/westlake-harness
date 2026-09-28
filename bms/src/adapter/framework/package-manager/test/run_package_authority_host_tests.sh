#!/usr/bin/env bash
# Developer-owned P/N/F for the dedicated Bridge package authority slice.
# This host run does not issue a device or independent verification verdict.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
ADAPTER_ROOT=$(cd "$PACKAGE_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
OUT=${PACKAGE_AUTHORITY_HOST_OUT:-$ADAPTER_ROOT/.work/package-authority-host}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: package authority output escaped project: $OUT" >&2; exit 2 ;;
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

clang -std=c11 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PACKAGE_DIR/install_plan/include" \
    -c "$PACKAGE_DIR/install_plan/src/sha256.c" \
    -o "$OUT/obj/sha256.o"

clang++ -std=c++17 -Wall -Wextra -Werror \
    -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -I"$PACKAGE_DIR/install_plan/include" \
    -I"$PACKAGE_DIR/package_transaction/include" \
    -I"$PACKAGE_DIR/package_query/include" \
    -I"$PACKAGE_DIR/package_authority/include" \
    "$PACKAGE_DIR/package_transaction/src/package_transaction.cpp" \
    "$PACKAGE_DIR/package_query/src/package_query_v1.cpp" \
    "$PACKAGE_DIR/package_authority/src/package_authority_service_v1.cpp" \
    "$PACKAGE_DIR/package_authority/tests/package_authority_host_test.cpp" \
    "$OUT/obj/sha256.o" \
    -o "$OUT/bin/package_authority_host_test"

"$OUT/bin/package_authority_host_test" "$RUN_ROOT"
echo "DEVELOPER_PNF_COMPLETE formal_verdict=NOT_ISSUED device_verdict=NOT_RUN"
