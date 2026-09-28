#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../../../.." && pwd)
WORK="$SCRIPT_DIR/.work/adler32-regression"

case "$WORK/" in
    "$PROJECT_ROOT/"*) ;;
    *)
        echo "FAIL work root escaped project" >&2
        exit 2
        ;;
esac

if [ -L "$SCRIPT_DIR/.work" ]; then
    echo "FAIL symlinked work root" >&2
    exit 2
fi

mkdir -p "$WORK"
cc -std=c11 -O2 -Wall -Wextra -Werror \
    -fno-builtin-__sync_val_compare_and_swap_1 \
    "$SCRIPT_DIR/../src/sync_builtins.c" \
    "$SCRIPT_DIR/adler32_regression.c" \
    -o "$WORK/adler32_regression"
"$WORK/adler32_regression"
