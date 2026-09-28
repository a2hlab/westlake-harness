#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
tool_dir="$root/tools/fn07_service_metadata_probe"
jni="$root/src/adapter/framework/package-manager/jni"
zlib_root="$root/src/upstream/openharmony-6.1.0.31/third_party/zlib"
minizip="$zlib_root/contrib/minizip"
out="$tool_dir/out"
apk="$root/APKS/Fn07-ServiceProbe/dist/fn07-service-probe.apk"

test -f "$apk"
mkdir -p "$out"

cc -I"$zlib_root" -I"$minizip" -c "$minizip/ioapi.c" -o "$out/ioapi.o"
cc -I"$zlib_root" -I"$minizip" -c "$minizip/unzip.c" -o "$out/unzip.o"
c++ -std=c++17 \
    -I"$tool_dir/include" -I"$jni" -I"$zlib_root" -I"$minizip" \
    "$tool_dir/service_manifest_test.cpp" \
    "$jni/apk_manifest_parser.cpp" "$jni/axml_parser.cpp" \
    "$out/ioapi.o" "$out/unzip.o" -lz \
    -o "$out/service_manifest_test"
"$out/service_manifest_test" "$apk"
