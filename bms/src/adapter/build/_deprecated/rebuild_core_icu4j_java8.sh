#!/bin/bash
# Rebuild core-icu4j.jar with Java 8 compilation for CacheValue.java only,
# so the synthetic accessor for the private NullValue.<init>() is generated.
#
# Background
# ----------
# Default Soong builds core-icu4j with Java 17, which uses NestMembers /
# NestHost attributes (Java 11+) for nest-mate access.  d8 propagates these
# to dex as MemberClasses / EnclosingClass annotations.  But ART on this
# device's libart implementation does NOT honor nest-mate access in
# CanAccessMember (mirror/class-inl.h:1156 returns false for kAccPrivate
# regardless of nest membership).  Result: CacheValue.<clinit> throws
# IllegalAccessError calling private NullValue.<init>().
#
# Fix: recompile CacheValue.java with --release 8 so javac emits a synthetic
# NullValue.<init>(CacheValue$1) accessor in NullValue, which is package-
# private and accessible.  All other classes in the jar can stay Java 17.
#
# Output: $OUT_DIR/core-icu4j.jar (dex-form)
#         $OUT_DIR/core-icu4j-classes.jar (class-form, intermediate)
#
# Idempotent.

set -e

ADAPTER_ROOT=${ADAPTER_ROOT:-$HOME/adapter}
AOSP_ROOT=${AOSP_ROOT:-$HOME/aosp}

OUT_DIR=$ADAPTER_ROOT/out/aosp_fwk
WORK=$ADAPTER_ROOT/out/icu_recompile
JDK=$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86
JAVAC=$JDK/bin/javac
JAR=$JDK/bin/jar
D8=$AOSP_ROOT/out/host/linux-x86/bin/d8

ICU_SRC=$AOSP_ROOT/external/icu/android_icu4j/src/main/java/android/icu/impl/CacheValue.java
CLASSES_JAR_SRC=$AOSP_ROOT/out/soong/.intermediates/external/icu/android_icu4j/core-icu4j/android_common/withres/core-icu4j.jar

if [ ! -f "$ICU_SRC" ]; then
    echo "ERROR: $ICU_SRC not found"; exit 1
fi
if [ ! -f "$CLASSES_JAR_SRC" ]; then
    echo "ERROR: $CLASSES_JAR_SRC not found — run a baseline AOSP build first"; exit 1
fi
if [ ! -x "$D8" ]; then
    echo "ERROR: d8 not found at $D8 (run: m d8-host)"; exit 1
fi

rm -rf "$WORK"; mkdir -p "$WORK/java8_classes" "$WORK/merged"

echo "[1/5] Compile CacheValue.java with Java 8 (synthetic accessor mode)..."
"$JAVAC" --release 8 -d "$WORK/java8_classes" \
    -cp "$AOSP_ROOT/out/soong/.intermediates/external/icu/android_icu4j/core-repackaged-icu4j/android_common/javac/core-repackaged-icu4j.jar" \
    "$ICU_SRC"

ls "$WORK/java8_classes/android/icu/impl/" | sed 's/^/  /'

echo "[2/5] Extract class-form jar to merge..."
mkdir -p "$WORK/merged"
(cd "$WORK/merged" && "$JAR" xf "$CLASSES_JAR_SRC")

echo "[3/5] Replace 6 CacheValue* class files with Java 8 versions..."
for c in CacheValue CacheValue\$1 CacheValue\$NullValue CacheValue\$Strength CacheValue\$StrongValue CacheValue\$SoftValue; do
    SRC="$WORK/java8_classes/android/icu/impl/${c}.class"
    DST="$WORK/merged/android/icu/impl/${c}.class"
    if [ ! -f "$SRC" ]; then
        echo "  ERROR: $SRC missing"; exit 1
        continue
    fi
    cp "$SRC" "$DST"
    echo "  replaced android/icu/impl/${c}.class"
done

echo "[4/5] Repack class-form jar then d8 → classes.dex ..."
CLASSJAR="$WORK/core-icu4j-classes.jar"
(cd "$WORK/merged" && "$JAR" cf "$CLASSJAR" .)

DEXOUT="$WORK/dex"
rm -rf "$DEXOUT"; mkdir -p "$DEXOUT"
PATH="$JDK/bin:$PATH" "$D8" --release --min-api 30 --output "$DEXOUT" "$CLASSJAR"

echo "[5/5] Build dex-form jar (classes.dex + resources)..."
DEXJAR="$WORK/core-icu4j.jar"
rm -f "$DEXJAR"
# Copy classes.dex into a fresh staging dir along with the resource files
# (everything that was NOT a .class — typically android_icu4j keeps locale
# .res files and similar under the same path layout)
STAGE="$WORK/stage"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp "$DEXOUT/classes.dex" "$STAGE/classes.dex"
# Pick resource files (anything that isn't .class) from the merged tree
(cd "$WORK/merged" && find . -type f ! -name '*.class' -print0 | tar --null -cf - -T -) | (cd "$STAGE" && tar -xf -)
(cd "$STAGE" && "$JAR" cf "$DEXJAR" .)

mkdir -p "$OUT_DIR"
cp "$DEXJAR" "$OUT_DIR/core-icu4j.jar"

echo ""
echo "=========================================="
echo "Output: $OUT_DIR/core-icu4j.jar"
ls -la "$OUT_DIR/core-icu4j.jar"
md5sum "$OUT_DIR/core-icu4j.jar"
echo ""
echo "Next: rebuild boot-core-icu4j.{art,oat,vdex} via dex2oat then deploy."
echo "=========================================="
