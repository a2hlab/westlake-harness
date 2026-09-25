#!/bin/bash
set -euo pipefail
A=/home/dspfac/a2hlab/source-closure/verify
W=$A/westlake-pkg28
O=$A/out-pkg28
B=$A/out
T=$W/tools
cd ~/a2hlab/manifest
step() { local name=$1; shift; echo "START $name $(date -Is)"; if "$@" > "$O/$name.log" 2>&1; then echo "PASS $name $(date -Is)"; else tail -70 "$O/$name.log"; return 1; fi; }
step westlake-java python3 tools/build_westlake_java.py --workspace "$A" --westlake-source "$W" --core-build "$B/core-java/java" --core-extension-build "$B/java-extensions" --framework-build "$B/framework-java" --out "$O/westlake-java"
step framework-runtime python3 tools/package_framework_runtime.py --workspace "$A" --rules "$W/framework-tools/runtime-jarjar-rules.txt" --core-build "$B/core-java/java" --core-extension-build "$B/java-extensions" --framework-build "$B/framework-java" --adapter-build "$O/westlake-java" --support-build "$B/framework-java-support" --jarjar-build "$B/jarjar" --out "$O/framework-runtime"
step framework-boot env LD_PRELOAD=/home/zhaoyue/a2hlab/tools/libmap32bit.so python3 tools/build_framework_boot.py --host-build "$B/host-tools/host" --core-build "$B/core-java/java" --extension-build "$B/java-extensions" --framework-build "$O/framework-runtime" --out "$O/framework-boot"
