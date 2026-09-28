#!/bin/bash
# ============================================================================
# compile_mainline_real_closure.sh — G2.6 (2026-04-30)
#
# 编译 framework.jar 实际引用的 mainline 闭包子集（24 个 .java 文件，~25k 行），
# 用 AOSP packages/modules/* 真源替代 B.18 的 80 个 empty stub。
#
# 与 B.19 compile_mainline_real.sh 区别：
#   - B.19 编译全部 mainline framework src — 2118 编译错（androidx 缺、AIDL 缺、
#     transitive 内部类缺等）
#   - G2.6 只编译 framework.jar 实际引用的闭包（dexdump 算出 25 个引用，
#     去重后 23 个 outer class .java + DeviceConfig.java 共 24 文件）
#
# 闭包来源：/tmp/compute_mainline_closure.sh — comm -12 stub_classes
# framework_refs。详见 doc/graphics_jni_inventory.html.
#
# 编译时 shim：将必要的 androidx 注解 + AIDL stub + OsConstants 等放在
# framework/mainline-real-shims/ 目录，先编 shim，再 compile real source
# 用 shim + framework.jar 双 classpath 解析。
# ============================================================================
set -o pipefail

ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"

JDK="$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86"
JAVAC="$JDK/bin/javac"
JAR="$JDK/bin/jar"
D8="$AOSP_ROOT/out/host/linux-x86/bin/d8"

# Closure: 24 .java files (23 outer classes + DeviceConfig.java for its inner classes)
declare -A CLOSURE_SRC
CLOSURE_SRC["AppSearchSchema"]="$AOSP_ROOT/packages/modules/AppSearch/framework/java/external/android/app/appsearch/AppSearchSchema.java"
CLOSURE_SRC["RoleManager"]="$AOSP_ROOT/packages/modules/Permission/framework-s/java/android/app/role/RoleManager.java"
CLOSURE_SRC["BluetoothDevice"]="$AOSP_ROOT/packages/modules/Bluetooth/framework/java/android/bluetooth/BluetoothDevice.java"
CLOSURE_SRC["ScanFilter"]="$AOSP_ROOT/packages/modules/Bluetooth/framework/java/android/bluetooth/le/ScanFilter.java"
CLOSURE_SRC["ColorMatrix"]="$AOSP_ROOT/frameworks/base/libs/hwui/apex/java/android/graphics/ColorMatrix.java"
CLOSURE_SRC["MediaCommunicationManager"]="$AOSP_ROOT/packages/modules/Media/apex/framework/java/android/media/MediaCommunicationManager.java"
CLOSURE_SRC["ConnectivityManager"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/ConnectivityManager.java"
CLOSURE_SRC["IkeTunnelConnectionParams"]="$AOSP_ROOT/packages/modules/IPsec/src/java/android/net/ipsec/ike/IkeTunnelConnectionParams.java"
CLOSURE_SRC["LinkAddress"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/LinkAddress.java"
CLOSURE_SRC["LinkProperties"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/LinkProperties.java"
CLOSURE_SRC["MacAddress"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/MacAddress.java"
CLOSURE_SRC["Network"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/Network.java"
CLOSURE_SRC["NetworkCapabilities"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/NetworkCapabilities.java"
CLOSURE_SRC["NetworkRequest"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/NetworkRequest.java"
CLOSURE_SRC["NetworkTemplate"]="$AOSP_ROOT/packages/modules/Connectivity/framework-t/src/android/net/NetworkTemplate.java"
CLOSURE_SRC["ProxyInfo"]="$AOSP_ROOT/packages/modules/Connectivity/framework/src/android/net/ProxyInfo.java"
CLOSURE_SRC["WifiInfo"]="$AOSP_ROOT/packages/modules/Wifi/framework/java/android/net/wifi/WifiInfo.java"
CLOSURE_SRC["DeviceConfig"]="$AOSP_ROOT/packages/modules/ConfigInfrastructure/framework/java/android/provider/DeviceConfig.java"
CLOSURE_SRC["AsYouTypeFormatter"]="$AOSP_ROOT/external/libphonenumber/repackaged/libphonenumber/src/com/android/i18n/phonenumbers/AsYouTypeFormatter.java"
CLOSURE_SRC["SSLClientSessionCache"]="$AOSP_ROOT/external/conscrypt/repackaged/common/src/main/java/com/android/org/conscrypt/SSLClientSessionCache.java"
CLOSURE_SRC["TrustedCertificateIndex"]="$AOSP_ROOT/external/conscrypt/repackaged/common/src/main/java/com/android/org/conscrypt/TrustedCertificateIndex.java"
CLOSURE_SRC["TrustManagerImpl"]="$AOSP_ROOT/external/conscrypt/repackaged/common/src/main/java/com/android/org/conscrypt/TrustManagerImpl.java"
CLOSURE_SRC["HTMLSchema"]="$AOSP_ROOT/external/tagsoup/src/org/ccil/cowan/tagsoup/HTMLSchema.java"
# rappor.Encoder: not strictly needed (low priority); skip until proven required

OUT_DIR="$ADAPTER_ROOT/out/adapter"
OUT_JAR="$OUT_DIR/adapter-mainline-stubs.jar"
BUILD_DIR="$ADAPTER_ROOT/out/adapter/mainline-closure-build"
SRC_STAGING="$BUILD_DIR/src"
CLASS_DIR="$BUILD_DIR/classes"
DEX_DIR="$BUILD_DIR/dex"
SHIM_DIR="$ADAPTER_ROOT/framework/mainline-real-shims"
LOG="$BUILD_DIR/compile.log"

FWK_TURBINE="$AOSP_ROOT/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/turbine-combined/framework-minus-apex.jar"

echo "=============================================="
echo "  G2.6 closure-based mainline real build"
echo "  Closure: ${#CLOSURE_SRC[@]} .java files"
echo "  Output: $OUT_JAR"
echo "=============================================="

rm -rf "$BUILD_DIR"
mkdir -p "$SRC_STAGING" "$CLASS_DIR" "$DEX_DIR"

# Stage closure sources
echo ""
echo "[1/5] Staging closure source files..."
for name in "${!CLOSURE_SRC[@]}"; do
    src="${CLOSURE_SRC[$name]}"
    if [ ! -f "$src" ]; then
        echo "  MISSING: $name => $src"
        continue
    fi
    cp "$src" "$SRC_STAGING/"
    echo "  ok  $name"
done
ls "$SRC_STAGING" | wc -l | xargs echo "  Total staged: "

# Verify shim dir
if [ ! -d "$SHIM_DIR" ]; then
    echo ""
    echo "[2/5] WARN: shim dir not found at $SHIM_DIR — first run will likely fail with"
    echo "          missing-symbol errors; create stubs in $SHIM_DIR/ for missing"
    echo "          androidx.annotation.* / android.system.OsConstants / IConnectivityManager etc."
    mkdir -p "$SHIM_DIR"
fi

mapfile -t SHIM_SRCS < <(find "$SHIM_DIR" -name '*.java' 2>/dev/null | sort)
echo ""
echo "[2/5] Shim sources: ${#SHIM_SRCS[@]}"
printf '       %s\n' "${SHIM_SRCS[@]}"

# Compile shims first
SHIM_CLASS_DIR="$BUILD_DIR/shim-classes"
mkdir -p "$SHIM_CLASS_DIR"
if [ ${#SHIM_SRCS[@]} -gt 0 ]; then
    echo "[3a/5] Compiling shims..."
    "$JAVAC" -source 17 -target 17 -encoding UTF-8 \
        -d "$SHIM_CLASS_DIR" \
        -bootclasspath "$JDK/jmods/java.base.jmod" \
        -classpath "$FWK_TURBINE" \
        "${SHIM_SRCS[@]}" 2>&1 | tee "$LOG"
    [ ${PIPESTATUS[0]} -eq 0 ] || { echo "  SHIM COMPILE FAIL"; exit 1; }
fi

# Compile closure source against framework + shims
echo ""
echo "[3b/5] Compiling closure sources (24 .java)..."
mapfile -t REAL_SRCS < <(find "$SRC_STAGING" -name '*.java' | sort)
echo "  Files: ${#REAL_SRCS[@]}"

CP="$FWK_TURBINE"
[ ${#SHIM_SRCS[@]} -gt 0 ] && CP="$SHIM_CLASS_DIR:$CP"

"$JAVAC" -source 17 -target 17 -encoding UTF-8 \
    -d "$CLASS_DIR" \
    -classpath "$CP" \
    -Xmaxerrs 200 \
    "${REAL_SRCS[@]}" 2>&1 | tee -a "$LOG" | tail -50

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo ""
    echo "  CLOSURE COMPILE FAIL — review errors in $LOG"
    grep -c "error:" "$LOG" 2>/dev/null | xargs echo "  Total errors:"
    exit 2
fi

# Add shim classes too (so runtime can resolve shim references if any leak)
if [ ${#SHIM_SRCS[@]} -gt 0 ]; then
    cp -r "$SHIM_CLASS_DIR"/* "$CLASS_DIR"/ 2>/dev/null || true
fi

# Convert to dex
echo ""
echo "[4/5] dex conversion..."
"$D8" --output "$DEX_DIR" --min-api 26 \
    $(find "$CLASS_DIR" -name '*.class') 2>&1 | tee -a "$LOG" | tail -10

# Pack jar
echo ""
echo "[5/5] Packing jar..."
"$JAR" cf "$OUT_JAR" -C "$DEX_DIR" classes.dex
ls -la "$OUT_JAR"
md5sum "$OUT_JAR"

echo ""
echo "=============================================="
echo "  DONE — adapter-mainline-stubs.jar (closure real source)"
echo "  Next: gen_boot_image.sh + deploy"
echo "=============================================="
