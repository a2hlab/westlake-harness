#!/bin/bash
# ============================================================================
# compile_fresh_jars_manifested.sh
#   Fresh, single-source, provenance-manifested BCP/adapter jar build.
#
#   Purpose (Unity 整改 批次1): rebuild framework/adapter jars from ONE explicit
#   current-generation source tree, retiring old generation 9cb1a0ee and the
#   mixed-generation out/* copies. Every build writes a provenance manifest so
#   the six-dimension consistency gate (source<->binary provenance, generation
#   coherence, evidence) is satisfiable from artifacts alone.
#
#   This wrapper is the "single blessed entry point" recommended by
#   jar_build_provenance.md §"Recommended fresh single-source build scheme".
#   It DELIBERATELY does NOT reuse the legacy dual-source / AOSP-mirror path.
#
# ---------------------------------------------------------------------------
# Design rules honored (jar_build_provenance.md 297-343 + coordinator brief)
# ---------------------------------------------------------------------------
#   1. Explicit inputs: AOSP_ROOT / ADAPTER_ROOT / OUT_ROOT / BUILD_ID.
#   2. Before compiling, write:
#        OUT_ROOT/provenance/source_roots.txt
#        OUT_ROOT/provenance/source_files.<artifact>.txt   (per-file sha256)
#        OUT_ROOT/provenance/toolchain.txt
#        OUT_ROOT/provenance/patches.txt
#        OUT_ROOT/provenance/jars.txt                       (output sha256, post-build)
#   3. oh-adapter-framework.jar: NO aosp/device/adapter mirror copy. Source
#      list is generated DIRECTLY from $ADAPTER_ROOT/framework/**/java, filtered
#      to package adapter.*, runtime-moved basenames excluded by manifest.
#   4. oh-adapter-runtime.jar: explicit source manifest; classpath consumes the
#      framework class dir produced by THIS same BUILD_ID (OUT_ROOT/adapter/classes).
#   5. adapter-mainline-stubs.jar: AOSP module roots + hand-written stubs are
#      STAGED into OUT_ROOT/stage/mainline-src and compiled only from the stage,
#      with a recorded stage manifest + hashes.
#   6. Reading jars from old adapter/out/*, nested adapter/adapter/out/*, or
#      out/aosp_fwk/*.jar as build INPUT is prohibited (guard: assert_input_ok).
#   7. Guard: refuses to run from / against a nested /adapter/adapter tree.
#   8. AOSP framework.jar / core-oj.jar / core-icu4j.jar are pure-Soong jars.
#      This wrapper does NOT fake-build them (that is the exact bug in
#      build_aosp_fw.sh). --with-aosp-soong invokes real Soong explicitly.
#
# ---------------------------------------------------------------------------
# Run location
# ---------------------------------------------------------------------------
#   The AOSP jar toolchain (prebuilts/jdk/jdk17/linux-x86, out/host/linux-x86/d8)
#   is linux-x86. Run this INSIDE the L1 ubuntu:22.04 container with the pristine
#   trees bind-mounted at the paths below. It does NOT run natively on macOS.
#   No device / hdc / adb is ever touched by this script.
#
# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
#   AOSP_ROOT=$HOME/aosp \
#   ADAPTER_ROOT=/opt/21.Game/02.unity.cardwords/adapter \
#   OUT_ROOT=/opt/21.Game/02.unity.cardwords/adapter/out-fresh \
#   BUILD_ID=unityC-$(date +%Y%m%d-%H%M) \
#   BUILD_INNER_INVOKED=1 bash compile_fresh_jars_manifested.sh --target=oh-adapter-framework.jar,oh-adapter-runtime.jar
#
#   --target=<list>          comma list of: oh-adapter-framework.jar,
#                            oh-adapter-runtime.jar, adapter-mainline-stubs.jar,
#                            framework.jar, core-oj.jar, core-icu4j.jar
#                            (default: the three adapter jars; AOSP-Soong jars
#                             excluded unless also passing --with-aosp-soong)
#   --manifest-only          write provenance manifests only, do NOT compile
#                            (safe to run anywhere with find + sha256sum)
#   --with-aosp-soong        allow framework.jar/core-*.jar via real Soong
#   --clean                  wipe OUT_ROOT class/dex caches first
#   --help
# ============================================================================
set -euo pipefail

# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED:-0}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via a build_*.sh wrapper," >&2
    echo "[GUARD] or set BUILD_INNER_INVOKED=1 explicitly for a manifested fresh build." >&2
    exit 2
fi
# === END GUARD ===

SCRIPT_SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$(basename "${BASH_SOURCE[0]}")"

# ---------------------------------------------------------------------------
# Explicit inputs (rule 1). Defaults =唯一环境本机 pristine 路径, container
# bind-mount 对齐. Override via env.
# ---------------------------------------------------------------------------
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"
ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
OUT_ROOT="${OUT_ROOT:-$ADAPTER_ROOT/out-fresh}"
BUILD_ID="${BUILD_ID:-fresh-$(date +%Y%m%d-%H%M%S)}"

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
TARGETS_CSV=""
MANIFEST_ONLY=0
WITH_AOSP_SOONG=0
CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --target=*)        TARGETS_CSV="${arg#--target=}" ;;
        --manifest-only)   MANIFEST_ONLY=1 ;;
        --with-aosp-soong) WITH_AOSP_SOONG=1 ;;
        --clean)           CLEAN=1 ;;
        --help|-h)
            sed -n '1,80p' "$SCRIPT_SELF" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "[ERROR] unknown arg: $arg" >&2; exit 1 ;;
    esac
done

declare -a ADAPTER_JARS=(
    "oh-adapter-framework.jar"
    "oh-adapter-runtime.jar"
    "adapter-mainline-stubs.jar"
)
declare -a AOSP_SOONG_JARS=(
    "framework.jar"
    "core-oj.jar"
    "core-icu4j.jar"
)

declare -a TARGETS=()
if [ -n "$TARGETS_CSV" ]; then
    IFS=',' read -ra TARGETS <<< "$TARGETS_CSV"
else
    TARGETS=("${ADAPTER_JARS[@]}")
fi

log()  { echo -e "\033[0;34m[fresh-jar]\033[0m $*"; }
ok()   { echo -e "\033[0;32m[  ok   ]\033[0m $*"; }
warn() { echo -e "\033[1;33m[ warn  ]\033[0m $*"; }
die()  { echo -e "\033[0;31m[ FATAL ]\033[0m $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Guard: refuse nested /adapter/adapter tree (rule 7)
# ---------------------------------------------------------------------------
assert_not_nested() {
    local p; p="$(cd "$1" 2>/dev/null && pwd -P || echo "$1")"
    case "$p" in
        */adapter/adapter|*/adapter/adapter/*)
            die "refusing nested duplicate tree: $p
      The divergent /adapter/adapter tree has different wrappers and extra
      Java dirs (appops/jobscheduler/storage/user). Point ADAPTER_ROOT at the
      top-level adapter, and run this script from the top-level build/inner/." ;;
    esac
}
assert_not_nested "$ADAPTER_ROOT"
assert_not_nested "$(dirname "$SCRIPT_SELF")"

# ---------------------------------------------------------------------------
# Guard: no old-out jar may be used as build INPUT (rule 6)
# ---------------------------------------------------------------------------
assert_input_ok() {
    # $1 = absolute path being consumed as a compile input
    local p; p="$(cd "$(dirname "$1")" 2>/dev/null && pwd -P || echo "")/$(basename "$1")"
    case "$p" in
        "$ADAPTER_ROOT"/out/*|"$ADAPTER_ROOT"/adapter/out/*|*/out/aosp_fwk/*.jar)
            die "forbidden build input (stale/mixed-generation output): $p
      Fresh builds must never consume adapter out/* jars as source of truth." ;;
    esac
}

# ---------------------------------------------------------------------------
# Toolchain (rule: single header source, same generation)
# ---------------------------------------------------------------------------
JDK="$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86"
JAVAC="$JDK/bin/javac"
JAR="$JDK/bin/jar"
D8="$AOSP_ROOT/out/host/linux-x86/bin/d8"
FWK_TURBINE="$AOSP_ROOT/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/turbine-combined/framework-minus-apex.jar"
CORE_OJ_TURBINE="$AOSP_ROOT/out/soong/.intermediates/libcore/core-oj/android_common/turbine-combined/core-oj.jar"
CORE_LIBART_TURBINE="$AOSP_ROOT/out/soong/.intermediates/libcore/core-libart/android_common/turbine-combined/core-libart.jar"

# Portable hash (ubuntu container: sha256sum; macOS manifest-only: shasum)
_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
    elif command -v shasum   >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}';
    else echo "NO_SHA_TOOL"; fi
}

# ---------------------------------------------------------------------------
# Runtime-moved basenames excluded from the BCP oh-adapter-framework.jar.
# These live in oh-adapter-runtime.jar (non-BCP). Excluding by MANIFEST here,
# never by deleting mirror files. (mirrors compile_oh_adapter_framework.sh)
# ---------------------------------------------------------------------------
BCP_EXCLUDE_BASENAMES=(
    "AppSchedulerBridge.java"
    "OhApplicationInfoConverter.java"
    "OhConfigurationConverter.java"
    "OhDisplayProvider.java"
    "AppBindDataDefaults.java"
)
is_bcp_excluded() {
    local base="$1" ex
    for ex in "${BCP_EXCLUDE_BASENAMES[@]}"; do [ "$base" = "$ex" ] && return 0; done
    return 1
}

# ---------------------------------------------------------------------------
# Source collection (direct-from-adapter, NO mirror) — rule 3
# ---------------------------------------------------------------------------
collect_ohfw_sources() {
    # Emit adapter.* .java files from $ADAPTER_ROOT/framework/<area>/java/...
    # minus runtime-moved basenames. -mindepth 3 == framework/<area>/java/**.
    local src pkg base
    while IFS= read -r src; do
        [ -z "$src" ] && continue
        pkg=$(grep -m1 '^package ' "$src" 2>/dev/null | sed 's/^package //;s/;.*//;s/[[:space:]]//g')
        case "$pkg" in adapter.*) ;; *) continue ;; esac
        base=$(basename "$src")
        is_bcp_excluded "$base" && continue
        echo "$src"
    done < <(find "$ADAPTER_ROOT/framework" -mindepth 3 -name '*.java' 2>/dev/null | sort)
}

# oh-adapter-runtime.jar explicit source manifest (rule 4)
RUNTIME_SRCS=(
    "$ADAPTER_ROOT/framework/appspawn-x/java/com/android/internal/os/AppSpawnXInit.java"
    "$ADAPTER_ROOT/framework/appspawn-x/java/com/android/internal/os/ApkSignatureBridge.java"
    "$ADAPTER_ROOT/framework/activity/java/AppSchedulerBridge.java"
)

# adapter-mainline-stubs.jar AOSP module roots (rule 5, staged)
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
MAINLINE_GAP_REPORT="$ADAPTER_ROOT/doc/bcp_gap_report.txt"
MAINLINE_LEGACY_DIR="$ADAPTER_ROOT/framework/mainline-stubs/java"

# ---------------------------------------------------------------------------
# AOSP L5 reflection patches recorded in provenance (rule 2: patches.txt)
# ---------------------------------------------------------------------------
AOSP_FWK_PATCHES=(
    "frameworks/base/core/java/android/app/ActivityManager.java.patch"
    "frameworks/base/core/java/android/app/ActivityTaskManager.java.patch"
    "frameworks/base/core/java/android/app/ActivityThread.java.patch"
    "frameworks/base/core/java/android/view/WindowManagerGlobal.java.patch"
)

# ===========================================================================
# Provenance manifests (rule 2) — written BEFORE any compile
# ===========================================================================
PROV_DIR="$OUT_ROOT/provenance"
write_provenance() {
    mkdir -p "$PROV_DIR"

    # --- source_roots.txt ---
    {
        echo "# fresh jar build source roots"
        echo "build_id: $BUILD_ID"
        echo "generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "aosp_root: $AOSP_ROOT"
        echo "adapter_root: $ADAPTER_ROOT"
        echo "out_root: $OUT_ROOT"
        echo "targets: ${TARGETS[*]}"
        echo "adapter_git_head: $(git -C "$ADAPTER_ROOT" rev-parse HEAD 2>/dev/null || echo n/a)"
        echo "aosp_git_head: $(git -C "$AOSP_ROOT" rev-parse HEAD 2>/dev/null || echo n/a)"
        echo "adapter_framework_src_root: $ADAPTER_ROOT/framework"
        echo "# NOTE: oh-adapter-framework.jar compiled DIRECTLY from adapter/framework/**/java"
        echo "#       (no aosp/device/adapter/oh_adapter_framework mirror copy)."
    } > "$PROV_DIR/source_roots.txt"

    # --- toolchain.txt ---
    {
        echo "# toolchain provenance (single generation)"
        echo "build_id: $BUILD_ID"
        for t in "$JAVAC" "$JAR" "$D8" "$FWK_TURBINE" "$CORE_OJ_TURBINE" "$CORE_LIBART_TURBINE"; do
            if [ -e "$t" ]; then
                printf '%s  sha256=%s  size=%s\n' "$t" "$(_sha256 "$t")" "$(wc -c < "$t" 2>/dev/null || echo '?')"
            else
                printf '%s  MISSING\n' "$t"
            fi
        done
    } > "$PROV_DIR/toolchain.txt"

    # --- patches.txt ---
    {
        echo "# AOSP framework L5 reflection patches (applied to AOSP source before framework.jar Soong build)"
        local rel pf
        for rel in "${AOSP_FWK_PATCHES[@]}"; do
            pf="$ADAPTER_ROOT/aosp_patches/$rel"
            if [ -f "$pf" ]; then
                printf '%s  sha256=%s\n' "$rel" "$(_sha256 "$pf")"
            else
                printf '%s  MISSING\n' "$rel"
            fi
        done
    } > "$PROV_DIR/patches.txt"

    # --- per-artifact source_files manifests ---
    local t
    for t in "${TARGETS[@]}"; do
        case "$t" in
            oh-adapter-framework.jar)
                { echo "# source_files.oh-adapter-framework.jar  build_id=$BUILD_ID"
                  collect_ohfw_sources | while IFS= read -r f; do
                      printf '%s  sha256=%s\n' "$f" "$(_sha256 "$f")"
                  done
                } > "$PROV_DIR/source_files.oh-adapter-framework.jar.txt" ;;
            oh-adapter-runtime.jar)
                { echo "# source_files.oh-adapter-runtime.jar  build_id=$BUILD_ID"
                  local f
                  for f in "${RUNTIME_SRCS[@]}"; do
                      if [ -f "$f" ]; then printf '%s  sha256=%s\n' "$f" "$(_sha256 "$f")";
                      else printf '%s  MISSING\n' "$f"; fi
                  done
                } > "$PROV_DIR/source_files.oh-adapter-runtime.jar.txt" ;;
            adapter-mainline-stubs.jar)
                { echo "# source_files.adapter-mainline-stubs.jar  build_id=$BUILD_ID (staged roots listed; full list after stage)"
                  local r
                  for r in "${MAINLINE_SRC_ROOTS[@]}"; do
                      echo "root: $r  exists=$( [ -d "$r" ] && echo yes || echo no )"
                  done
                  echo "gap_report: $MAINLINE_GAP_REPORT  exists=$( [ -f "$MAINLINE_GAP_REPORT" ] && echo yes || echo no )"
                } > "$PROV_DIR/source_files.adapter-mainline-stubs.jar.txt" ;;
        esac
    done
    ok "provenance manifests written: $PROV_DIR"
}

record_jar_provenance() {
    # $1 = jar path
    mkdir -p "$PROV_DIR"
    if [ -f "$1" ]; then
        printf '%s  sha256=%s  size=%s  build_id=%s\n' \
            "$1" "$(_sha256 "$1")" "$(wc -c < "$1")" "$BUILD_ID" >> "$PROV_DIR/jars.txt"
    fi
}

# ===========================================================================
# Common prerequisites for javac/d8 path
# ===========================================================================
assert_toolchain() {
    local f
    for f in "$JAVAC" "$JAR" "$D8" "$FWK_TURBINE" "$CORE_OJ_TURBINE" "$CORE_LIBART_TURBINE"; do
        assert_input_ok "$f"
        [ -e "$f" ] || die "toolchain/header prerequisite missing: $f
      (Run inside the L1 linux container with pristine AOSP bind-mounted; the
       turbine header jars come from a prior AOSP Soong build.)"
    done
    export JAVA_HOME="$JDK"
    export PATH="$JDK/bin:$PATH"
}

# ===========================================================================
# Target: oh-adapter-framework.jar (BCP, direct-from-adapter, no mirror)
# ===========================================================================
build_oh_adapter_framework() {
    log "oh-adapter-framework.jar : direct source-list build (no AOSP mirror)"
    assert_toolchain
    local CLASS_DIR="$OUT_ROOT/adapter/classes"
    local DEX_DIR="$OUT_ROOT/adapter/framework-dex"
    local OUT_JAR="$OUT_ROOT/adapter/oh-adapter-framework.jar"
    local LOG="$OUT_ROOT/adapter/compile.framework.log"
    mkdir -p "$OUT_ROOT/adapter"
    rm -rf "$CLASS_DIR" "$DEX_DIR"; mkdir -p "$CLASS_DIR" "$DEX_DIR"

    local SRC_LIST; SRC_LIST="$(mktemp)"
    collect_ohfw_sources > "$SRC_LIST"
    local n; n=$(wc -l < "$SRC_LIST")
    [ "$n" -gt 0 ] || die "no adapter.* sources found under $ADAPTER_ROOT/framework"
    log "  compiling $n adapter.* sources -> $CLASS_DIR"

    local CP="$FWK_TURBINE:$CORE_OJ_TURBINE:$CORE_LIBART_TURBINE"
    "$JAVAC" -d "$CLASS_DIR" --release 17 -classpath "$CP" -encoding UTF-8 \
        -Xmaxerrs 30 @"$SRC_LIST" > "$LOG" 2>&1 \
        || { echo "  javac FAILED — see $LOG"; head -30 "$LOG"; rm -f "$SRC_LIST"; exit 2; }
    rm -f "$SRC_LIST"

    # post-flight: AppSpawnXInit must NOT be here (belongs to runtime jar)
    if find "$CLASS_DIR" -name 'AppSpawnXInit.class' | grep -q .; then
        die "AppSpawnXInit.class leaked into BCP framework jar"
    fi

    log "  d8 -> classes.dex"
    local CLASS_FILES; CLASS_FILES=$(find "$CLASS_DIR" -name '*.class')
    "$D8" --release --output "$DEX_DIR" \
        --lib "$CORE_OJ_TURBINE" --lib "$CORE_LIBART_TURBINE" --lib "$FWK_TURBINE" \
        $CLASS_FILES >> "$LOG" 2>&1 || { echo "  d8 FAILED — see $LOG"; tail -30 "$LOG"; exit 2; }
    [ -f "$DEX_DIR/classes.dex" ] || die "d8 produced no classes.dex"

    rm -f "$OUT_JAR"
    ( cd "$DEX_DIR" && "$JAR" cf "$OUT_JAR" classes.dex )
    [ -f "$OUT_JAR" ] || die "jar packaging failed"
    record_jar_provenance "$OUT_JAR"
    ok "oh-adapter-framework.jar -> $OUT_JAR ($(wc -c < "$OUT_JAR") bytes)"
}

# ===========================================================================
# Target: oh-adapter-runtime.jar (non-BCP; classpath = same-build framework classes)
# ===========================================================================
build_oh_adapter_runtime() {
    log "oh-adapter-runtime.jar : explicit source manifest"
    assert_toolchain
    local BCP_CLASS_DIR="$OUT_ROOT/adapter/classes"
    if [ ! -d "$BCP_CLASS_DIR" ] || [ -z "$(ls -A "$BCP_CLASS_DIR" 2>/dev/null)" ]; then
        die "BCP class dir empty: $BCP_CLASS_DIR
      Build oh-adapter-framework.jar first in the SAME BUILD_ID/OUT_ROOT so the
      runtime jar resolves adapter.* references against same-generation classes."
    fi
    local BUILD_DIR="$OUT_ROOT/adapter/runtime-build"
    local CLASS_DIR="$BUILD_DIR/classes"
    local DEX_DIR="$BUILD_DIR/dex"
    local OUT_JAR="$OUT_ROOT/adapter/oh-adapter-runtime.jar"
    local LOG="$BUILD_DIR/compile.log"
    rm -rf "$CLASS_DIR" "$DEX_DIR"; mkdir -p "$CLASS_DIR" "$DEX_DIR"

    local s
    for s in "${RUNTIME_SRCS[@]}"; do [ -f "$s" ] || die "runtime source missing: $s"; done

    local CP="$FWK_TURBINE:$CORE_OJ_TURBINE:$CORE_LIBART_TURBINE:$BCP_CLASS_DIR"
    "$JAVAC" -d "$CLASS_DIR" --release 17 -classpath "$CP" -encoding UTF-8 \
        -Xmaxerrs 30 "${RUNTIME_SRCS[@]}" > "$LOG" 2>&1 \
        || { echo "  javac FAILED — see $LOG"; head -30 "$LOG"; exit 2; }

    local CLASS_FILES; CLASS_FILES=$(find "$CLASS_DIR" -name '*.class')
    [ -n "$CLASS_FILES" ] || die "no .class produced for runtime jar"
    "$D8" --release --output "$DEX_DIR" \
        --lib "$CORE_OJ_TURBINE" --lib "$CORE_LIBART_TURBINE" --lib "$FWK_TURBINE" \
        $CLASS_FILES >> "$LOG" 2>&1 || { echo "  d8 FAILED — see $LOG"; tail -30 "$LOG"; exit 3; }
    [ -f "$DEX_DIR/classes.dex" ] || die "d8 produced no classes.dex"

    rm -f "$OUT_JAR"
    ( cd "$DEX_DIR" && "$JAR" cf "$OUT_JAR" classes.dex )
    [ -f "$OUT_JAR" ] || die "jar packaging failed"
    record_jar_provenance "$OUT_JAR"
    ok "oh-adapter-runtime.jar -> $OUT_JAR ($(wc -c < "$OUT_JAR") bytes)"
}

# ===========================================================================
# Target: adapter-mainline-stubs.jar (staged single-directory compile, rule 5)
# ===========================================================================
build_mainline_stubs() {
    log "adapter-mainline-stubs.jar : stage AOSP module roots + handwritten, compile from stage"
    assert_toolchain
    [ -f "$MAINLINE_GAP_REPORT" ] || die "gap report missing: $MAINLINE_GAP_REPORT"
    local STAGE="$OUT_ROOT/stage/mainline-src"
    local BUILD_DIR="$OUT_ROOT/adapter/mainline-real-build"
    local CLASS_DIR="$BUILD_DIR/classes"
    local DEX_DIR="$BUILD_DIR/dex"
    local OUT_JAR="$OUT_ROOT/adapter/adapter-mainline-stubs.jar"
    local LOG="$BUILD_DIR/compile.log"
    rm -rf "$STAGE" "$CLASS_DIR" "$DEX_DIR"
    mkdir -p "$STAGE" "$CLASS_DIR" "$DEX_DIR"

    # gap class -> whole owning module inclusion (deps-complete)
    mapfile -t GAP_CLASSES < <(grep '^  ' "$MAINLINE_GAP_REPORT" 2>/dev/null | tr -d ' ')
    declare -A USED_ROOTS
    local cls outer rel root
    for cls in "${GAP_CLASSES[@]}"; do
        outer="${cls%%\$*}"; rel="${outer//.//}"
        for root in "${MAINLINE_SRC_ROOTS[@]}"; do
            [ -f "$root/$rel.java" ] && { USED_ROOTS["$root"]=1; break; }
        done
    done

    # stage every .java from each used root (preserve package path)
    local staged=0 f pkgrel
    for root in "${!USED_ROOTS[@]}"; do
        while IFS= read -r f; do
            pkgrel="${f#$root/}"
            mkdir -p "$STAGE/$(dirname "$pkgrel")"
            cp "$f" "$STAGE/$pkgrel"
            staged=$((staged+1))
        done < <(find "$root" -name '*.java')
    done

    # hand-written project stubs (non auto-gen) kept from legacy dir
    local HAND=(
        "android/net/TetheringManager" "android/net/ConnectivityManager"
        "android/net/ProxyInfo" "android/net/TrafficStats"
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
        "android/os/StatsFrameworkInitializer" "android/os/ext/SdkExtensions"
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
    local hkeep=0 hc cand
    for hc in "${HAND[@]}"; do
        cand="$MAINLINE_LEGACY_DIR/$hc.java"
        if [ -f "$cand" ] && ! head -1 "$cand" | grep -q "Auto-generated by scan_bcp_class_gap"; then
            mkdir -p "$STAGE/$(dirname "$hc")"
            cp "$cand" "$STAGE/$hc.java"; hkeep=$((hkeep+1))
        fi
    done
    log "  staged $staged AOSP-module files + $hkeep hand-written stubs -> $STAGE"

    # record staged manifest with hashes (rule 5)
    { echo "# staged mainline sources  build_id=$BUILD_ID"
      find "$STAGE" -name '*.java' | sort | while IFS= read -r f; do
          printf '%s  sha256=%s\n' "${f#$STAGE/}" "$(_sha256 "$f")"
      done
    } > "$PROV_DIR/source_files.adapter-mainline-stubs.jar.staged.txt"

    local SRCS_FILE="$BUILD_DIR/sources.txt"
    find "$STAGE" -name '*.java' > "$SRCS_FILE"
    local total; total=$(wc -l < "$SRCS_FILE")
    log "  javac $total staged sources"
    "$JAVAC" -source 17 -target 17 -classpath "$FWK_TURBINE" -d "$CLASS_DIR" \
        -encoding UTF-8 -nowarn -Xmaxerrs 50 @"$SRCS_FILE" > "$LOG" 2>&1 \
        || { echo "  javac FAILED — see $LOG"; tail -40 "$LOG"; exit 2; }

    local CLASS_FILES; CLASS_FILES=$(find "$CLASS_DIR" -name '*.class')
    "$D8" --release --output "$DEX_DIR" --lib "$FWK_TURBINE" $CLASS_FILES >> "$LOG" 2>&1 \
        || { echo "  d8 FAILED — see $LOG"; tail -40 "$LOG"; exit 3; }
    [ -f "$DEX_DIR/classes.dex" ] || die "d8 produced no classes.dex"

    rm -f "$OUT_JAR"
    ( cd "$DEX_DIR" && "$JAR" cf "$OUT_JAR" classes.dex )
    record_jar_provenance "$OUT_JAR"
    ok "adapter-mainline-stubs.jar -> $OUT_JAR ($(wc -c < "$OUT_JAR") bytes)"
}

# ===========================================================================
# Target: AOSP Soong jars (framework.jar / core-oj.jar / core-icu4j.jar)
#   Honest handling of the build_aosp_fw.sh bug: these are Soong-only. This
#   wrapper refuses to fake them. --with-aosp-soong invokes real Soong.
# ===========================================================================
build_aosp_soong_jar() {
    local target="$1"
    if [ "$WITH_AOSP_SOONG" != "1" ]; then
        die "$target is a pure-AOSP Soong jar; this wrapper does NOT fake-build it.
      Pass --with-aosp-soong to invoke real Soong (heavy, hours), or build it in
      the AOSP checkout directly:  (cd $AOSP_ROOT && source build/envsetup.sh &&
      lunch <target> && m framework core-oj core-icu4j)
      NOTE: build_aosp_fw.sh's framework.jar/core-*.jar targets are MISLEADING —
      they route to oh-adapter-framework.jar and never call Soong."
    fi
    log "$target : applying AOSP L5 reflection patches then invoking Soong"
    # apply patches (records provenance already written to patches.txt)
    export BUILD_INNER_INVOKED=1
    if [ -f "$ADAPTER_ROOT/build/inner/apply_aosp_fwk_patches.sh" ]; then
        # minimal logging shims so the sourced applier's contract is satisfied
        log_info(){ echo "[A3] $*"; }; log_ok(){ echo "[A3][ok] $*"; }
        log_warn(){ echo "[A3][warn] $*"; }
        run(){ eval "$@"; }
        DRY_RUN=0
        # shellcheck disable=SC1090
        source "$ADAPTER_ROOT/build/inner/apply_aosp_fwk_patches.sh"
        apply_aosp_fwk_patches || warn "some L5 patches failed to apply"
    fi
    local soong_target
    case "$target" in
        framework.jar)   soong_target="framework" ;;
        core-oj.jar)     soong_target="core-oj" ;;
        core-icu4j.jar)  soong_target="core-icu4j" ;;
        *) die "unknown Soong target: $target" ;;
    esac
    [ -n "${LUNCH_TARGET:-}" ] || die "set LUNCH_TARGET=<product-variant> for Soong build of $target"
    ( cd "$AOSP_ROOT" && source build/envsetup.sh && lunch "$LUNCH_TARGET" && m "$soong_target" )
    ok "$target : Soong build finished (collect artifact from out/soong intermediates)"
}

# ===========================================================================
# Main
# ===========================================================================
log "BUILD_ID=$BUILD_ID"
log "AOSP_ROOT=$AOSP_ROOT"
log "ADAPTER_ROOT=$ADAPTER_ROOT"
log "OUT_ROOT=$OUT_ROOT"
log "targets=${TARGETS[*]}  manifest_only=$MANIFEST_ONLY  with_aosp_soong=$WITH_AOSP_SOONG"

[ -d "$ADAPTER_ROOT/framework" ] || die "ADAPTER_ROOT/framework missing: $ADAPTER_ROOT/framework"

# validate targets
for t in "${TARGETS[@]}"; do
    ok_t=0
    for v in "${ADAPTER_JARS[@]}" "${AOSP_SOONG_JARS[@]}"; do [ "$t" = "$v" ] && ok_t=1; done
    [ "$ok_t" = "1" ] || die "unknown target: $t"
done

if [ "$CLEAN" = "1" ]; then
    log "clean: wiping $OUT_ROOT/adapter class/dex caches and stage"
    rm -rf "$OUT_ROOT/adapter/classes" "$OUT_ROOT/adapter/framework-dex" \
           "$OUT_ROOT/adapter/runtime-build" "$OUT_ROOT/adapter/mainline-real-build" \
           "$OUT_ROOT/stage"
fi

# rule 2: manifests always written first
write_provenance

if [ "$MANIFEST_ONLY" = "1" ]; then
    ok "manifest-only mode: no compilation performed. See $PROV_DIR"
    exit 0
fi

for t in "${TARGETS[@]}"; do
    case "$t" in
        oh-adapter-framework.jar)   build_oh_adapter_framework ;;
        oh-adapter-runtime.jar)     build_oh_adapter_runtime ;;
        adapter-mainline-stubs.jar) build_mainline_stubs ;;
        framework.jar|core-oj.jar|core-icu4j.jar) build_aosp_soong_jar "$t" ;;
    esac
done

ok "fresh jar build complete. provenance: $PROV_DIR"
[ -f "$PROV_DIR/jars.txt" ] && { echo "--- output jars ---"; cat "$PROV_DIR/jars.txt"; }
warn "BCP jar bytes changed => 27-段 boot 全量连贯重烤 required (batch 2)."
