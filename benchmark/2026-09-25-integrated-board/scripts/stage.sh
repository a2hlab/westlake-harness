#!/bin/bash
set -euo pipefail
A=/home/dspfac/a2hlab/source-closure/verify
O=$A/out-all0925
B=$A/out
S=5cd1e3dd00000000000000000923012c
R=$HOME/a2hlab/board/$S/verify32
cd ~/a2hlab/manifest
python3 tools/probe_framework_vm.py --appspawn-build "$O/appspawn" --core-runtime "$O/native-runtime" --native-runtime "$O/native-runtime" --core-build "$B/core-java/java" --extension-build "$B/java-extensions" --framework-build "$O/framework-runtime" --boot-build "$O/framework-boot" --resources-build "$B/framework-resources" --data-build "$B/runtime-data" --firmware-abi "$A/westlake-all0925/native/oh61-firmware-abi.json" --hdc /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh --serial "$S" --cache-report "$HOME/a2hlab/board/$S/framework-1/device-report.json" --out "$R/framework" > "$R/framework.log" 2>&1
