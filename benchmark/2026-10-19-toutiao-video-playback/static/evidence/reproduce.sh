#!/bin/sh
# Reproduce the static media-provider closure for Toutiao libttmplayer against the RouteB (asx) runtime.
# Inputs: APK and RouteB runtime package (sealed copies; SHA-identical to the 61b parent-namespace reads),
#         OH NDK sysroot stubs for libc/EGL/GLESv2/GLESv3/OpenSLES/native_window.
# Usage: reproduce.sh <toutiao.apk> <routeb_runtime_dir> <oh_sysroot_lib_dir> <workdir>
set -eu
APK=$1; R=$2; L=$3; W=$4
mkdir -p "$W"; cd "$W"
unzip -o -q "$APK" 'lib/arm64-v8a/*'
S=lib/arm64-v8a
shasum -a 256 "$APK" "$S/libttmplayer.so" "$S/libtexturerender_native.so" "$S/libmffmpeg.so" "$S/libvcbasekit.so"
llvm-readelf -d "$S/libttmplayer.so" | grep -E 'NEEDED|FLAGS'
llvm-readelf --dyn-syms "$S/libttmplayer.so" | grep -E 'SL_IID|slCreate|ANativeWindow_'
llvm-readelf -r "$S/libttmplayer.so" | grep -E 'SL_IID|slCreate|ANativeWindow_'
: > providers.txt
for f in "$R/liblog.so" "$R/libandroid.so" "$R/libhwui.so" "$R/liboh_android_runtime.so" "$R/libwestlake_binder.so" \
         "$R/libandroidfw.so" "$R/libutils.so" "$R/libz.so" "$R/libjnigraphics.so" "$R/libandroid_native_network_compat.so" \
         "$R/webview-t-lib/libwebview_bionic_shim.so" "$S/libmffmpeg.so" "$S/libvcbasekit.so" "$S/libttcrypto.so" "$S/libttboringssl.so" \
         "$L/libc.so" "$L/libEGL.so" "$L/libGLESv2.so" "$L/libGLESv3.so" "$L/libOpenSLES.so" "$L/libnative_window.so"; do
  shasum -a 256 "$f"
  llvm-nm -D --defined-only "$f" | awk '{print $NF}' | sed 's/@.*//' >> providers.txt
done
sort -u providers.txt -o providers.txt
llvm-nm -D --undefined-only "$S/libttmplayer.so" | awk '{print $NF}' | sed 's/@.*//' | sort -u > ttm-und.txt
echo "== unresolved against known providers"; comm -23 ttm-und.txt providers.txt
echo "== RouteB exports of media entry points"
for f in "$R"/*.so "$R"/webview-t-lib/*.so; do
  o=$(llvm-nm -D --defined-only "$f" 2>/dev/null | awk '{print $NF}' | grep -E '^(ANativeWindow_|ASurfaceTexture_|slCreateEngine|SL_IID)' | tr '\n' ' ' || true)
  [ -n "$o" ] && echo "$(basename "$f"): $o"
done
strings "$R/webview-t-lib/libwebview_bionic_shim.so" | grep 'WESTLAKE-ANW'
echo "== libttmplayer JNI/Java media strings"
strings -n 8 "$S/libttmplayer.so" | grep -E 'android/media/|AJMediaCodec|MediaCodec stuck|Landroid/view/Surface;' | sort -u
