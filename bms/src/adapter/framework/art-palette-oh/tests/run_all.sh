#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
"$HERE/run_host_tests.sh"
"$HERE/run_target_tests.sh"
