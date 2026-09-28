#!/bin/bash
# Build the wl-critfix LD_PRELOAD shim for board 5cd33a95 (aarch64 OHOS 6.1).
set -e
SDK=/opt/harmony-blobs/a2oh-source-audit/ohos-sdk/native
SR=$SDK/sysroot
JNI=/opt/build-trees/aosp-arm64-d600/libnativehelper/include_jni
/tmp/wl-r48-rebuild/frozen-test/toolchain/bin/clang-15 --target=aarch64-linux-ohos \
  --sysroot=$SR -I$JNI \
  -B$SR/usr/lib/aarch64-linux-ohos -L$SR/usr/lib/aarch64-linux-ohos \
  -fPIC -shared -O2 -Wall \
  -o /tmp/wl-critfix/libwlcritfix.so /tmp/wl-critfix/wl_critfix.c -ldl
ls -l /tmp/wl-critfix/libwlcritfix.so
