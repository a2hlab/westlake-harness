#!/usr/bin/env bash
# Capture read-only package evidence for one CardWords staircase run directory.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
FROZEN_APK="$PROJECT_ROOT/adapter/frozen/product_inputs/cardwords-current/canonical/selfcontained_cardwords.apk"

if [[ $# -ne 1 ]]; then
  echo "usage: $(basename "$0") RUN_DIR" >&2
  exit 2
fi

RUN_DIR="$(cd "$1" && pwd -P)"
APK="${CANONICAL_APK:-$FROZEN_APK}"
APKANALYZER="${APKANALYZER:-/Users/alexyang/Library/Android/sdk/cmdline-tools/16.0/bin/apkanalyzer}"
APKSIGNER="${APKSIGNER:-/Users/alexyang/Library/Android/sdk/build-tools/37.0.0/apksigner}"
JAVA_HOME="${JAVA_HOME:-/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home}"
EXPECTED_APK_SHA256="435f0ebbf99b5f5ae76aecb411da7684052a92ef0b6aee18d50afa6a98210626"
PACKAGE="com.CardWordsStudio.CardWords"
ACTIVITY="com.unity3d.player.UnityPlayerActivity"

test -f "$APK"
APK="$(realpath "$APK")"
case "$APK" in
  "$PROJECT_ROOT"/*) ;;
  *)
    echo "canonical APK must resolve inside project root: $APK" >&2
    exit 3
    ;;
esac
case "$RUN_DIR" in
  "$PROJECT_ROOT"/*) ;;
  *)
    echo "run directory must resolve inside project root: $RUN_DIR" >&2
    exit 3
    ;;
esac
test -x "$APKANALYZER"
test -x "$APKSIGNER"
test -x "$JAVA_HOME/bin/java"
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

APK_SHA256="$(sha256sum "$APK" | awk '{print $1}')"
if [[ "$APK_SHA256" != "$EXPECTED_APK_SHA256" ]]; then
  echo "canonical APK hash mismatch: $APK_SHA256" >&2
  exit 3
fi

"$APKANALYZER" manifest print "$APK" > "$RUN_DIR/apk_manifest.xml"
"$APKSIGNER" verify --verbose --print-certs "$APK" > "$RUN_DIR/apk_signature.txt" 2>&1
unzip -Z1 "$APK" | LC_ALL=C sort > "$RUN_DIR/apk_entries.txt"

{
  for entry in \
    lib/arm64-v8a/lib_burst_generated.so \
    lib/arm64-v8a/libil2cpp.so \
    lib/arm64-v8a/libmain.so \
    lib/arm64-v8a/libunity.so; do
    digest="$(unzip -p "$APK" "$entry" | sha256sum | awk '{print $1}')"
    printf '%s  %s\n' "$digest" "$entry"
  done
} > "$RUN_DIR/apk_native_entries.sha256"

grep -F "package=\"$PACKAGE\"" "$RUN_DIR/apk_manifest.xml" >/dev/null
grep -F "android:name=\"$ACTIVITY\"" "$RUN_DIR/apk_manifest.xml" >/dev/null
grep -Fx 'lib/arm64-v8a/libmain.so' "$RUN_DIR/apk_entries.txt" >/dev/null
grep -Fx 'lib/arm64-v8a/libunity.so' "$RUN_DIR/apk_entries.txt" >/dev/null

{
  printf 'canonical_apk=%s\n' "$APK"
  printf 'canonical_apk_sha256=%s\n' "$APK_SHA256"
  printf 'apkanalyzer=%s\n' "$APKANALYZER"
  printf 'apkanalyzer_sha256=%s\n' "$(sha256sum "$APKANALYZER" | awk '{print $1}')"
  printf 'apksigner=%s\n' "$APKSIGNER"
  printf 'apksigner_sha256=%s\n' "$(sha256sum "$APKSIGNER" | awk '{print $1}')"
  printf 'java_home=%s\n' "$JAVA_HOME"
  printf 'java_sha256=%s\n' "$(sha256sum "$JAVA_HOME/bin/java" | awk '{print $1}')"
  printf 'package=%s\n' "$PACKAGE"
  printf 'activity=%s\n' "$ACTIVITY"
  printf 'result=PASS\n'
} > "$RUN_DIR/apk_inspection.env"

printf 'CARDWORDS_APK_INSPECTION_CAPTURED run_dir=%s apk_sha256=%s\n' "$RUN_DIR" "$APK_SHA256"
