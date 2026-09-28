#!/usr/bin/env bash
set -euo pipefail

ROOT=/opt/Bridge
PROBE="$ROOT/tools/experiments/d600/fn03_a05_probe"
OUT="$ROOT/.work/fn03-a05-probe"
SDK=/Users/alexyang/Library/Android/sdk
BT="$SDK/build-tools/34.0.0"
ANDROID_JAR="$SDK/platforms/android-34/android.jar"
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
KEYSTORE="$ROOT/src/adapter/out/app/hello2-debug.keystore"

rm -rf "$OUT"
mkdir -p "$OUT/classes" "$OUT/dex" "$OUT/payload/lib/arm64-v8a"

"$BT/aapt2" link \
  -I "$ANDROID_JAR" \
  --manifest "$PROBE/AndroidManifest.xml" \
  --min-sdk-version 21 \
  --target-sdk-version 34 \
  --version-code 1 \
  --version-name 1.0 \
  -o "$OUT/resources-unsigned.apk"

"$JAVA_HOME/bin/javac" \
  -encoding UTF-8 \
  -parameters \
  -source 8 \
  -target 8 \
  -bootclasspath "$ANDROID_JAR" \
  -d "$OUT/classes" \
  "$PROBE/src/com/example/helloworld/MainActivity.java"

"$JAVA_HOME/bin/jar" cf "$OUT/classes.jar" -C "$OUT/classes" .
JAVA_HOME="$JAVA_HOME" "$BT/d8" \
  --lib "$ANDROID_JAR" \
  --min-api 21 \
  --output "$OUT/dex" \
  "$OUT/classes.jar"

"/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/clang" \
  --target=aarch64-linux-ohos -fPIC -fvisibility=hidden -nostdlib -shared \
  -Wl,-z,defs -Wl,--build-id=sha1 -Wl,-soname,libwestlake_hello_abi.so \
  "$ROOT/src/adapter/app/native/hello_world_abi_marker.c" \
  -o "$OUT/payload/lib/arm64-v8a/libwestlake_hello_abi.so"

cp "$OUT/dex/classes.dex" "$OUT/payload/classes.dex"
cp "$OUT/resources-unsigned.apk" "$OUT/probe-unaligned.apk"
(
  cd "$OUT/payload"
  /usr/bin/zip -X -q -r "$OUT/probe-unaligned.apk" classes.dex lib
)
"$BT/zipalign" -f -p 4 "$OUT/probe-unaligned.apk" "$OUT/probe-aligned.apk"
JAVA_HOME="$JAVA_HOME" "$BT/apksigner" sign \
  --ks "$KEYSTORE" \
  --ks-key-alias hello2-debug \
  --ks-pass pass:android \
  --key-pass pass:android \
  --v3-signing-enabled false \
  --v4-signing-enabled false \
  --out "$OUT/Fn03A05Probe.apk" \
  "$OUT/probe-aligned.apk"

JAVA_HOME="$JAVA_HOME" "$BT/apksigner" verify --verbose "$OUT/Fn03A05Probe.apk"
"$BT/zipalign" -c -p 4 "$OUT/Fn03A05Probe.apk"
"$BT/aapt2" dump badging "$OUT/Fn03A05Probe.apk" >"$OUT/APK_BADGING.txt"
grep -Fq "package: name='com.example.helloworld'" "$OUT/APK_BADGING.txt"
shasum -a 256 "$OUT/Fn03A05Probe.apk"
