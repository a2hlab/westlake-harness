#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../../.." && pwd -P)
GATE=$SCRIPT_DIR/../tools/verify_source_reachability.py
POSITIVE=$SCRIPT_DIR/fixtures/positive/build.sh
NEGATIVE=$SCRIPT_DIR/fixtures/negative_old_shim/build.sh
PYTHON=${PYTHON:-/usr/bin/python3}

[[ -x "$PYTHON" ]] || { echo "FAIL missing Python: $PYTHON" >&2; exit 2; }

positive_output=$(
    "$PYTHON" "$GATE" --project-root "$PROJECT_ROOT" --recipe "$POSITIVE"
)
case "$positive_output" in
    *"M04_REACHABILITY_PASS"*) ;;
    *) echo "FAIL positive control" >&2; exit 1 ;;
esac

set +e
negative_output=$(
    "$PYTHON" "$GATE" --project-root "$PROJECT_ROOT" --recipe "$NEGATIVE" 2>&1
)
negative_rc=$?
set -e
[[ $negative_rc -eq 3 ]] || {
    echo "FAIL negative control rc=$negative_rc" >&2
    exit 1
}
case "$negative_output" in
    *"DENY source=unity_signal_box.c refs=1"*"M04_REACHABILITY_FAIL reasons=deny_reachable"*) ;;
    *) echo "FAIL negative control did not isolate old signal shim" >&2; exit 1 ;;
esac

echo "PASS m04 source-reachability controls positive=1 negative_old_shim=1 product_claim=false"
