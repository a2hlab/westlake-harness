#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
python3 "$SCRIPT_DIR/verify_product_source.py"
"$SCRIPT_DIR/run_host_tests.sh"
"$SCRIPT_DIR/run_target_tests.sh"
