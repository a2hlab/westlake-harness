#!/bin/bash
# assemble_webview_input.sh <shim build dir> <out dir>: the webview-t payload layout probe_source_app.py --webview-input reads.
set -eu
shims=$1 out=$2
. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
W=$WORKSPACES/westlake-inputs/webview
[ -e "$out" ] && { echo "exists: $out"; exit 1; }
mkdir -p "$out/webview-t-lib"
cp "$W/webview-t.apk" "$out/webview-t.apk"
cp "$W/webview-t-lib/libwebviewchromium.so" "$out/webview-t-lib/"
for l in libandroid.so libjnigraphics.so libwebview_bionic_shim.so libwebviewchromium_plat_support.so; do cp "$shims/$l" "$out/webview-t-lib/"; done
(cd "$out" && sha256sum webview-t.apk webview-t-lib/*.so)
