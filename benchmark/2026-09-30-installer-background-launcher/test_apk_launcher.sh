#!/usr/bin/env bash
set -euo pipefail
R=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy
E=$R/benchmark/2026-09-30-installer-background-launcher
W=$R/bms/src/.work/installer-background-launcher
PM=$R/bms/src/adapter/framework/package-manager
OH=/Users/zhaoyue/orca/workspaces/oh61-bms-kit
INC=(-I"$PM/test/host_shims" -I"$PM/jni" -I"$OH/third_party/zlib/contrib/minizip" -I"$OH/third_party/zlib")
g++ -std=c++17 -O2 "${INC[@]}" "$PM/jni/apk_manifest_parser.cpp" "$PM/jni/axml_parser.cpp" "$E/test_apk_launcher.cpp" "$W/host-test/unzip.o" "$W/host-test/ioapi.o" /lib/x86_64-linux-gnu/libz.so.1 -o "$W/test_apk_launcher"
"$W/test_apk_launcher" /Users/zhaoyue/orca/workspaces/westlake-inputs/apks/fdroid/com.ichi2.anki_22401300.apk /Users/zhaoyue/orca/workspaces/westlake-inputs/apks/fdroid/org.wikipedia_50606.apk /Users/zhaoyue/orca/workspaces/westlake-inputs/apks/fdroid100/com.github.ashutoshgngwr.noice_72.apk
