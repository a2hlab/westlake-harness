#!/bin/bash
# usage: inspect.sh <apk> — run the static identity reads through rec.sh (no install, no execution).
# Needs ANDROID_BUILD_TOOLS (default $HOME/Library/Android/sdk/build-tools/37.0.0) and COMMERCIAL_G01_PRIVATE.
set -u
APK=$1; BT=${ANDROID_BUILD_TOOLS:-$HOME/Library/Android/sdk/build-tools/37.0.0}; HERE=$(cd "$(dirname "$0")" && pwd); R=$HERE/rec.sh
$R i01-sha256 shasum -a 256 "$APK"
$R i02-stat stat -f '%z %m' "$APK"
$R i03-unzip-test unzip -tqq "$APK"
$R i04-aapt2-badging "$BT/aapt2" dump badging "$APK"
$R i05-aapt2-manifest-xmltree "$BT/aapt2" dump xmltree --file AndroidManifest.xml "$APK"
$R i06-apksigner-verify "$BT/apksigner" verify --verbose --print-certs "$APK"
$R i07-zipstat python3 -I "$HERE/zipstat.py" "$APK"
