#!/bin/bash
set -euo pipefail
A=/home/dspfac/a2hlab/source-closure/verify
O=$A/out-touch21/wake
B=$A/out
S=5ea34a4500000000000000001123012c
R=$HOME/a2hlab/board/$S/touch25
mkdir -p "$R"
cd ~/a2hlab/manifest
python3 tools/probe_framework_vm.py --appspawn-build "$O/appspawn" --core-runtime "$O/native-runtime" --native-runtime "$O/native-runtime" --core-build "$B/core-java/java" --extension-build "$B/java-extensions" --framework-build "$A/out-touch21/framework-runtime" --boot-build "$A/out-touch21/framework-boot" --resources-build "$B/framework-resources" --data-build "$B/runtime-data" --firmware-abi "$A/westlake-touch21/native/oh61-firmware-abi.json" --hdc /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh --serial "$S" --cache-report "$HOME/a2hlab/board/$S/framework-1/device-report.json" --out "$R/framework-wake" > "$R/framework-wake.log" 2>&1
