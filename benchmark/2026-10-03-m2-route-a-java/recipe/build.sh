#!/usr/bin/env bash
# Reproducible build + unit test for the M2 route-a Java side. Offline, no deploy.
#   ANDROID_JAR  : a public Android SDK android.jar (API 34+ has the public webkit API). Auto-detected if unset.
#   JAVA_HOME    : a JDK 17+ (DevEco JBR works). Auto-detected if unset.
#   WORKSPACES   : the orca/workspaces root (for the AOSP interface source in the skeleton compile).
set -uo pipefail
cd "$(dirname "$0")/.."
: "${WORKSPACES:=$(cd ../../.. && pwd)}"
: "${ANDROID_JAR:=$(ls "$HOME"/Library/Android/sdk/platforms/android-3*/android.jar 2>/dev/null | sort | tail -1)}"
: "${JAVA_HOME:=/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home}"
JAVAC="$JAVA_HOME/bin/javac"; JAVA="$JAVA_HOME/bin/java"
echo "ANDROID_JAR=$ANDROID_JAR"; "$JAVAC" -version

echo "== 1. GREEN SET: route-a core + reflection-seed wiring (compiles against public android.jar) =="
rm -rf out && mkdir -p out
"$JAVAC" -source 17 -target 17 -cp "$ANDROID_JAR" -d out \
  src/org/westlake/webview/NWebCallbackSink.java src/org/westlake/webview/NWebBackend.java \
  src/org/westlake/webview/NativeNWebBackend.java src/org/westlake/webview/MockNWebBackend.java \
  src/org/westlake/webview/OhNWebController.java src/org/westlake/webview/OhNWebProviderFix.java

echo "== 2. UNIT TEST (no native, no Android runtime objects) =="
rm -rf test-out && mkdir -p test-out
"$JAVAC" -source 17 -target 17 -cp "$ANDROID_JAR:out" -d test-out test/NWebRouteATest.java
"$JAVA" -cp "out:test-out:$ANDROID_JAR" NWebRouteATest

echo "== 3. PROVIDER/SETTINGS/FACTORY skeleton compile (documents the framework.jar reality) =="
# These implement the @hide android.webkit.WebViewProvider/WebViewFactoryProvider contract. The public
# android.jar is a STUB that strips the @hide types (WebView.PrivateAccess, TokenBindingService) and skews the
# WebSettings abstract set, so this compile is EXPECTED to fail against android.jar -- the concrete provider is a
# framework-classpath artifact (the deployed framework.jar, dex, carries the full contract; see evidence).
WK="$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/webkit"
mkdir -p compile-refs/android/webkit && cp "$WK/WebViewProvider.java" "$WK/WebViewFactoryProvider.java" compile-refs/android/webkit/ 2>/dev/null
"$JAVAC" -source 17 -target 17 -nowarn -cp "$ANDROID_JAR:out" -d /tmp/provout-$$ \
  src/org/westlake/webview/OhNWebProvider.java src/org/westlake/webview/OhNWebFactoryProvider.java \
  src/org/westlake/webview/OhNWebSettings.java \
  compile-refs/android/webkit/WebViewProvider.java compile-refs/android/webkit/WebViewFactoryProvider.java \
  compile-refs/android/annotation/*.java 2>&1 | grep -E 'error:' | head
echo "(skeleton compile against the public stub is expected to report @hide-symbol errors; see evidence/compile-provider.log)"
