#!/usr/bin/env bash
set -euo pipefail
R=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy
E=$R/benchmark/2026-09-29-bms-network-permissions
W=$R/bms/src/.work/b89-network-permissions/host-test
OH=/Users/zhaoyue/orca/workspaces/oh61-bms-kit
PM=$R/bms/src/adapter/framework/package-manager
mkdir -p "$W/android"
INC=(-I"$PM/test/host_shims" -I"$PM/jni" -I"$R/bms/src/adapter/third_party/lodepng" -I"$OH/third_party/zlib/contrib/minizip" -I"$OH/third_party/zlib" -I"$OH/third_party/json/include")
for file in unzip zip ioapi; do gcc -O2 -DUSE_FILE32API "${INC[@]}" -c "$OH/third_party/zlib/contrib/minizip/$file.c" -o "$W/$file.o"; done
g++ -std=c++17 -O2 -ffunction-sections -fdata-sections "${INC[@]}" \
 "$PM/jni/apk_installer.cpp" "$PM/jni/apk_label_resolver.cpp" "$PM/jni/arsc_resolver.cpp" \
 "$PM/jni/apk_manifest_parser.cpp" "$PM/jni/axml_parser.cpp" "$PM/jni/icon_normalize.cpp" \
 "$PM/jni/adaptive_icon.cpp" "$PM/jni/directory_ex_shim.cpp" \
 "$R/bms/src/adapter/third_party/lodepng/lodepng.cpp" "$E/test_network_hap.cpp" \
 "$W/unzip.o" "$W/zip.o" "$W/ioapi.o" -Wl,--gc-sections /lib/x86_64-linux-gnu/libz.so.1 -o "$W/test_network_hap"
for apk in /Users/zhaoyue/orca/workspaces/westlake-inputs/apks/fdroid/org.wikipedia_50606.apk /Users/zhaoyue/orca/workspaces/westlake-inputs/apks/fdroid100/com.github.ashutoshgngwr.noice_72.apk; do
 "$W/test_network_hap" "$apk" "$W/$(basename "$apk").hap"
done
