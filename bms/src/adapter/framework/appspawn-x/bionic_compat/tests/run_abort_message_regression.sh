#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../../../.." && pwd)
WORK="$SCRIPT_DIR/.work/abort-message-regression"

case "$WORK/" in
    "$PROJECT_ROOT/"*) ;;
    *) echo "FAIL work root escaped project" >&2; exit 2 ;;
esac
if [ -L "$SCRIPT_DIR/.work" ]; then
    echo "FAIL symlinked work root" >&2
    exit 2
fi

mkdir -p "$WORK"
c++ -std=c++17 -O2 -Wall -Wextra -Werror -pthread \
    "$SCRIPT_DIR/../src/abort_message_compat.cpp" \
    "$SCRIPT_DIR/abort_message_regression.cpp" \
    -o "$WORK/abort_message_regression"
"$WORK/abort_message_regression" first
"$WORK/abort_message_regression" null

