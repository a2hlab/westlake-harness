#!/bin/bash
# build.sh: builds out/notification-answers-probe.apk (pure Java).
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SDK=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/android-sdk}}
TOOLS="$SDK/build-tools/34.0.0"
ANDROID_JAR="$SDK/platforms/android-34/android.jar"
KEYSTORE=${WESTLAKE_DEBUG_KEYSTORE:-$HOME/.android/debug.keystore}
OUT="$ROOT/out"
for tool in "$TOOLS/aapt" "$TOOLS/d8" "$TOOLS/zipalign" "$TOOLS/apksigner" "$ANDROID_JAR" "$KEYSTORE"; do
    test -f "$tool" || { echo "missing build input: $tool" >&2; exit 1; }
done
rm -rf "$OUT"
mkdir -p "$OUT/classes" "$OUT/dex"
javac -source 8 -target 8 -Xlint:-options -cp "$ANDROID_JAR" -d "$OUT/classes" \
    "$ROOT/src/org/westlake/probe/notification/MainActivity.java"
jar cf "$OUT/classes.jar" -C "$OUT/classes" .
# build-tools 34.0.0's D8 (8.2.2-dev) fails on this probe's classes with a NullPointerException; the
# cmdline-tools R8 jar's D8 (8.2.33) takes them.
R8_JAR=${R8_JAR:-$SDK/cmdline-tools/latest/lib/r8.jar}
java -cp "$R8_JAR" com.android.tools.r8.D8 --min-api 31 --lib "$ANDROID_JAR" --output "$OUT/dex" "$OUT/classes.jar"
"$TOOLS/aapt" package -f -M "$ROOT/AndroidManifest.xml" -I "$ANDROID_JAR" -F "$OUT/unsigned.apk"
(cd "$OUT/dex" && "$TOOLS/aapt" add "$OUT/unsigned.apk" classes.dex >/dev/null)
"$TOOLS/zipalign" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$TOOLS/apksigner" sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
    --out "$OUT/notification-answers-probe.apk" "$OUT/aligned.apk"
echo "built $OUT/notification-answers-probe.apk"
