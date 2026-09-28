#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [DEPRECATED Phase 1 — 2026-05-21] Use build_aosp_fw.sh --target=mainline-stubs.jar instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_aosp_fw.sh — Phase 4 will absorb this" >&2
# ============================================================================
# compile_mainline_real.sh — B.19 (2026-04-28)
#
# 用 AOSP packages/modules/* 的 真 mainline 源码 编译 adapter-mainline-stubs.jar，
# 替代 B.18 的 80 个 empty Java stubs（违反"stub 只在 IPC C++ 实现"原则）。
#
# 包含 9 个 mainline module 的 framework java 源:
#   - StatsD (framework-statsd)        StatsEvent / StatsLog
#   - Connectivity (framework-connectivity + framework-t)  Network/LinkAddress/NetworkCapabilities/NetworkStats etc.
#   - AppSearch (framework-appsearch)  AppSearchSchema / GenericDocument
#   - Bluetooth (framework-bluetooth)  BluetoothDevice / BluetoothCodecConfig / le.Scan*
#   - Media (framework-media)          ApplicationMediaCapabilities / Session2Token / MediaCommunicationManager
#   - HealthFitness (framework-healthfitness) HealthConnectManager
#   - Permission (framework-permission-s)  RoleManager / OnRoleHoldersChangedListener
#   - hwui apex                        ColorMatrix
#   - 手工保留现有 mainline-stubs/java/ 内非 auto-gen 文件（如 TetheringManager / FrameworkInitializers）
#
# 编译策略:
#   1. find 各 module framework src 目录下所有 .java
#   2. classpath = framework-minus-apex.jar (turbine combined) 解 framework 类型
#   3. javac → classes/  → d8 → classes.dex  → jar
#
# Per overall_design §15: stub 只在 IPC 接口 C++ 实现层；Java 层用 AOSP 真源。
# ============================================================================
set -o pipefail

ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"

JDK="$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86"
JAVAC="$JDK/bin/javac"
JAR="$JDK/bin/jar"
D8="$AOSP_ROOT/out/host/linux-x86/bin/d8"

# AOSP mainline real source roots
MAINLINE_SRC_ROOTS=(
    "$AOSP_ROOT/packages/modules/StatsD/framework/java"
    "$AOSP_ROOT/packages/modules/Connectivity/framework/src"
    "$AOSP_ROOT/packages/modules/Connectivity/framework-t/src"
    "$AOSP_ROOT/packages/modules/AppSearch/framework/java/external"
    "$AOSP_ROOT/packages/modules/Bluetooth/framework/java"
    "$AOSP_ROOT/packages/modules/Media/apex/framework/java"
    "$AOSP_ROOT/packages/modules/HealthFitness/framework/java"
    "$AOSP_ROOT/packages/modules/Permission/framework-s/java"
    "$AOSP_ROOT/packages/modules/Permission/framework/java"
    "$AOSP_ROOT/frameworks/base/libs/hwui/apex/java"
)

# Hand-written stubs we want to keep (not from AOSP source — adapter-specific)
HAND_WRITTEN_DIR="$ADAPTER_ROOT/framework/mainline-stubs-handwritten"

# Auto-gen empty-stub dir (B.18) we are RETIRING from this build
LEGACY_AUTO_GEN_DIR="$ADAPTER_ROOT/framework/mainline-stubs/java"

OUT_DIR="$ADAPTER_ROOT/out/adapter"
OUT_JAR="$OUT_DIR/adapter-mainline-stubs.jar"
BUILD_DIR="$ADAPTER_ROOT/out/adapter/mainline-real-build"
CLASS_DIR="$BUILD_DIR/classes"
DEX_DIR="$BUILD_DIR/dex"
LOG="$BUILD_DIR/compile.log"

# framework-minus-apex turbine for type resolution
FWK_TURBINE="$AOSP_ROOT/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/turbine-combined/framework-minus-apex.jar"

# Read gap class list from latest report
GAP_REPORT="$ADAPTER_ROOT/doc/bcp_gap_report.txt"

echo "=============================================="
echo "  adapter-mainline-stubs.jar (REAL mainline source, B.19)"
echo "=============================================="

mkdir -p "$BUILD_DIR" "$CLASS_DIR" "$DEX_DIR"
> "$LOG"

# Pre-flight: framework-minus-apex.jar must exist
if [ ! -f "$FWK_TURBINE" ]; then
    echo "ERROR: $FWK_TURBINE not found (build it: cd ~/aosp && m framework-minus-apex)" >&2
    exit 1
fi

# Step 1: locate AOSP real .java for each gap class
echo ""
echo "[1/4] locating AOSP source for each gap class..."

# Read gap class list (lines like "  android.app.appsearch.AppSearchSchema$Builder")
mapfile -t GAP_CLASSES < <(grep '^  ' "$GAP_REPORT" 2>/dev/null | tr -d ' ')
echo "  gap classes from report: ${#GAP_CLASSES[@]}"

# Strategy: for any gap class hit in a mainline module, INCLUDE THE ENTIRE
# module's framework source tree. Mainline modules have heavy internal deps
# (NetworkStateSnapshot referenced by ConnectivityManager etc.) — picking
# only 149 gap classes leaves those deps unresolved.
declare -A SOURCE_FILES
declare -A USED_ROOTS
declare -a UNRESOLVED
for cls in "${GAP_CLASSES[@]}"; do
    outer="${cls%%\$*}"
    rel="${outer//.//}"
    found_root=""
    for root in "${MAINLINE_SRC_ROOTS[@]}"; do
        if [ -f "$root/$rel.java" ]; then
            found_root="$root"
            break
        fi
    done
    if [ -n "$found_root" ]; then
        USED_ROOTS["$found_root"]=1
    else
        UNRESOLVED+=("$outer")
    fi
done

echo "  mainline source roots needed: ${#USED_ROOTS[@]}"
for root in "${!USED_ROOTS[@]}"; do
    echo "    $root"
done

# Now collect ALL .java in each used root
for root in "${!USED_ROOTS[@]}"; do
    while IFS= read -r f; do
        SOURCE_FILES["$f"]=1
    done < <(find "$root" -name '*.java')
done
echo "  total source files (whole modules): ${#SOURCE_FILES[@]}"
if [ ${#UNRESOLVED[@]} -gt 0 ]; then
    echo "  WARNING: ${#UNRESOLVED[@]} gap classes have no AOSP source (likely SDK-only / removed):"
    for c in "${UNRESOLVED[@]}"; do echo "    $c"; done | head -10
fi

# Add hand-written non-mainline stubs (TetheringManager / FrameworkInitializers etc.)
# These are kept because they're project-specific (not mirroring AOSP source)
echo ""
echo "[1.5/4] including hand-written project stubs..."
HAND_WRITTEN_CANDIDATES=(
    "android/net/TetheringManager"
    "android/net/ConnectivityManager"
    "android/net/ProxyInfo"
    "android/net/TrafficStats"
    "android/app/appsearch/AppSearchManagerFrameworkInitializer"
    "android/app/blob/BlobStoreManagerFrameworkInitializer"
    "android/app/job/JobSchedulerFrameworkInitializer"
    "android/app/role/RoleFrameworkInitializer"
    "android/app/sdksandbox/SdkSandboxManagerFrameworkInitializer"
    "android/bluetooth/BluetoothFrameworkInitializer"
    "android/content/rollback/RollbackManagerFrameworkInitializer"
    "android/devicelock/DeviceLockFrameworkInitializer"
    "android/health/connect/HealthServicesInitializer"
    "android/media/MediaFrameworkInitializer"
    "android/media/MediaFrameworkPlatformInitializer"
    "android/nearby/NearbyFrameworkInitializer"
    "android/net/ConnectivityFrameworkInitializer"
    "android/net/ConnectivityFrameworkInitializerTiramisu"
    "android/net/wifi/WifiFrameworkInitializer"
    "android/nfc/NfcFrameworkInitializer"
    "android/ondevicepersonalization/OnDevicePersonalizationFrameworkInitializer"
    "android/os/StatsFrameworkInitializer"
    "android/os/ext/SdkExtensions"
    "android/provider/DeviceConfigInitializer"
    "android/safetycenter/SafetyCenterFrameworkInitializer"
    "android/scheduling/SchedulingFrameworkInitializer"
    "android/system/virtualmachine/VirtualizationFrameworkInitializer"
    "android/telephony/TelephonyFrameworkInitializer"
    "android/uwb/UwbFrameworkInitializer"
    "android/adservices/AdServicesFrameworkInitializer"
    "android/content/pm/permission/PermissionManagerFrameworkInitializer"
    "com/android/org/conscrypt/TrustedCertificateStore"
)
HAND_KEEP=0
for hcls in "${HAND_WRITTEN_CANDIDATES[@]}"; do
    cand="$LEGACY_AUTO_GEN_DIR/$hcls.java"
    if [ -f "$cand" ]; then
        # Only keep if NOT auto-gen (check first line for marker)
        if ! head -1 "$cand" | grep -q "Auto-generated by scan_bcp_class_gap"; then
            SOURCE_FILES["$cand"]=1
            HAND_KEEP=$((HAND_KEEP + 1))
        fi
    fi
done
echo "  hand-written stubs kept: $HAND_KEEP"

# Step 2: write source list file for javac
SRCS_FILE="$BUILD_DIR/sources.txt"
> "$SRCS_FILE"
for f in "${!SOURCE_FILES[@]}"; do
    echo "$f" >> "$SRCS_FILE"
done
TOTAL_SRC=$(wc -l < "$SRCS_FILE")
echo ""
echo "[2/4] javac compile $TOTAL_SRC sources..."

# javac with framework-minus-apex.jar on classpath (resolves android.* core types)
# --source/--target 17 for module_lib API level
# Suppress warnings (mainline source has many @hide / @NonNull annotations
# that may not all resolve; ignore)
"$JAVAC" \
    -source 17 -target 17 \
    -classpath "$FWK_TURBINE" \
    -d "$CLASS_DIR" \
    -encoding UTF-8 \
    -nowarn \
    -Xmaxerrs 50 \
    @"$SRCS_FILE" \
    >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
    echo "  FAIL — see $LOG (showing last 40 lines):"
    tail -40 "$LOG"
    exit 2
fi

CLASS_COUNT=$(find "$CLASS_DIR" -name '*.class' | wc -l)
echo "  OK: $CLASS_COUNT .class files"

# Step 3: d8 → classes.dex
echo ""
echo "[3/4] d8 .class → classes.dex..."
export JAVA_HOME="$JDK"
export PATH="$JDK/bin:$PATH"

CLASS_FILES_LIST=$(find "$CLASS_DIR" -name '*.class')
"$D8" --release \
    --output "$DEX_DIR" \
    --lib "$FWK_TURBINE" \
    $CLASS_FILES_LIST \
    >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
    echo "  FAIL — see $LOG"
    tail -40 "$LOG"
    exit 3
fi
DEX_SIZE=$(stat -c%s "$DEX_DIR/classes.dex")
echo "  OK: classes.dex = $DEX_SIZE bytes"

# Step 4: jar
echo ""
echo "[4/4] jar → adapter-mainline-stubs.jar..."
rm -f "$OUT_JAR"
(cd "$DEX_DIR" && "$JAR" cf "$OUT_JAR" classes.dex)
JAR_SIZE=$(stat -c%s "$OUT_JAR")
echo "=============================================="
echo "DONE — $OUT_JAR ($JAR_SIZE bytes, $CLASS_COUNT classes from AOSP real source)"
echo "Deploy: scp + push to /system/android/framework/adapter-mainline-stubs.jar"
echo "=============================================="
