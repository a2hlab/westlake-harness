#!/bin/bash
# ============================================================================
# compile_mainline_stubs.sh
#
# Build adapter-mainline-stubs.jar — BCP-prepended stubs for AOSP 14
# Mainline APEX classes that adapter's framework.jar doesn't ship.
# Hello World ActivityThread.main() references them early (lines 8146-8170)
# and ART verifier NoClassDefFoundError's on missing classes.
#
# Scope: ONLY class shells (no method bodies) so <clinit> is trivial and
# ART class-load + verifier pass. Method impls are all no-op because the
# adapter neither needs telephony/stats/media mainline functionality nor
# has the APEX infra to host real impls.
#
# Deployment: push jar to /system/android/framework/ and update
# appspawn-x VM -Xbootclasspath to include it (boot image does NOT need
# rebuild — new classes JIT at first use; existing boot-image classes
# unchanged).
# ============================================================================
set -o pipefail

ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"

JDK="$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86"
JAVAC="$JDK/bin/javac"
JAR="$JDK/bin/jar"
D8="$AOSP_ROOT/out/host/linux-x86/bin/d8"

SRC_ROOT="$ADAPTER_ROOT/framework/mainline-stubs/java"
# Paths chosen to match AOSP 14 ActivityThread.java import lines (verified
# against ~/aosp/frameworks/base/core/java/android/app/ActivityThread.java).
# First pass used guessed packages that turned out wrong — see AA.18 for
# the correction.
# Glob all generated .java files — gen_mainline_initializer_stubs.sh
# (auto-generated set) plus any hand-curated ones (e.g.
# TrustedCertificateStore which has a non-FrameworkInitializer signature).
mapfile -t SRCS < <(find "$SRC_ROOT" -name '*.java' | sort)
echo "  Source files (${#SRCS[@]}):"
printf '    %s\n' "${SRCS[@]}"

OUT_DIR="$ADAPTER_ROOT/out/adapter"
OUT_JAR="$OUT_DIR/adapter-mainline-stubs.jar"
BUILD_DIR="$ADAPTER_ROOT/out/adapter/mainline-stubs-build"
CLASS_DIR="$BUILD_DIR/classes"
DEX_DIR="$BUILD_DIR/dex"
LOG="$BUILD_DIR/compile.log"

# Turbine header jars for framework refs (Context / File / StatsServiceManager etc.)
FWK_JAR="$AOSP_ROOT/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/turbine-combined/framework-minus-apex.jar"
CORE_OJ_JAR="$AOSP_ROOT/out/soong/.intermediates/libcore/core-oj/android_common/turbine-combined/core-oj.jar"
CORE_LIBART_JAR="$AOSP_ROOT/out/soong/.intermediates/libcore/core-libart/android_common/turbine-combined/core-libart.jar"

echo "=============================================="
echo "adapter-mainline-stubs.jar build (BCP stubs)"
echo "=============================================="

for f in "$JAVAC" "$JAR" "$D8" "$FWK_JAR" "$CORE_OJ_JAR" "$CORE_LIBART_JAR"; do
    [ -e "$f" ] || { echo "ERROR: missing $f" >&2; exit 1; }
done
for s in "${SRCS[@]}"; do
    [ -f "$s" ] || { echo "ERROR: source missing: $s" >&2; exit 1; }
done

mkdir -p "$BUILD_DIR" "$CLASS_DIR" "$DEX_DIR" "$OUT_DIR"
rm -rf "$CLASS_DIR" "$DEX_DIR"
mkdir -p "$CLASS_DIR" "$DEX_DIR"

echo "[1/3] javac ${#SRCS[@]} stub sources..."
CP="$FWK_JAR:$CORE_OJ_JAR:$CORE_LIBART_JAR"
if ! "$JAVAC" -d "$CLASS_DIR" --release 17 -classpath "$CP" \
        -encoding UTF-8 -Xmaxerrs 30 "${SRCS[@]}" >"$LOG" 2>&1; then
    echo "  FAIL — see $LOG"; head -40 "$LOG"; exit 2
fi
NUM=$(find "$CLASS_DIR" -name '*.class' | wc -l)
echo "  OK: $NUM .class files"

echo "[2/3] d8 → classes.dex..."
# d8 wrapper invokes `java` (system). Default may be Java 11; d8 jar needs 17+.
# Force JAVA_HOME/PATH to JDK17 so the exec finds a compatible JVM.
export JAVA_HOME="$JDK"
export PATH="$JDK/bin:$PATH"
if ! "$D8" --release --output "$DEX_DIR" \
        --min-api 28 \
        --lib "$CORE_OJ_JAR" --lib "$CORE_LIBART_JAR" --lib "$FWK_JAR" \
        $(find "$CLASS_DIR" -name '*.class') >>"$LOG" 2>&1; then
    echo "  FAIL — see $LOG"; tail -40 "$LOG"; exit 3
fi
DEX_SIZE=$(stat -c%s "$DEX_DIR/classes.dex")
echo "  OK: classes.dex ($DEX_SIZE bytes)"

echo "[3/3] jar → adapter-mainline-stubs.jar..."
rm -f "$OUT_JAR"
(cd "$DEX_DIR" && "$JAR" cf "$OUT_JAR" classes.dex)
JAR_SIZE=$(stat -c%s "$OUT_JAR")

echo "=============================================="
echo "DONE — $OUT_JAR ($JAR_SIZE bytes)"
echo "Deploy: scp + push to /system/android/framework/adapter-mainline-stubs.jar"
echo "Wire:   appspawn-x BCP env var must include this jar (see main.cpp seedLongEnvs)"
echo "=============================================="
