#!/usr/bin/env bash
set -euo pipefail
REPO=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy
export ANL_HOST_TEST_OUT=$REPO/bms/src/.work/v3c-next3-native/host-mac
# Run the unchanged host suite on Mac, which has rg and its matching libc headers.
exec bash "$REPO/bms/src/adapter/framework/app-native-loader/tests/host/run_host_tests.sh"
