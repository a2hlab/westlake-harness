#!/bin/bash
# deploy.sh - Deploy adapter project artifacts to DAYU600 device via hdc
#
# Usage:
#   ./build/deploy.sh [--target=TARGET] [--reboot]
#
# Targets:
#   oh-services   Deploy patched OH system services only (replace .z.so)
#   android-rt    Deploy Android runtime (framework.jar, ART, adapter JARs)
#   adapter       Deploy adapter layer (appspawn-x, oh_adapter_bridge, configs)
#   all           Deploy everything
#   check         Check device status only
#
# Prerequisites:
#   - hdc in PATH and DAYU600 connected via USB
#   - Build artifacts in adapter/out/

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$ADAPTER_ROOT/out"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ============================================================
# Device deployment paths
# ============================================================

# OH system services (replace existing)
declare -A OH_SERVICE_DEPLOY
OH_SERVICE_DEPLOY[libabilityms.z.so]="/system/lib64/platformsdk/libabilityms.z.so"
OH_SERVICE_DEPLOY[libappms.z.so]="/system/lib64/platformsdk/libappms.z.so"
OH_SERVICE_DEPLOY[libwms.z.so]="/system/lib64/platformsdk/libwms.z.so"
OH_SERVICE_DEPLOY[libbms.z.so]="/system/lib64/platformsdk/libbms.z.so"

# Android runtime (new additions)
ANDROID_FRAMEWORK_DIR="/system/android/framework"
ANDROID_LIB_DIR="/system/android/lib64"

# Adapter layer
ADAPTER_BIN_DIR="/system/bin"
ADAPTER_LIB_DIR="/system/lib64"
ADAPTER_ETC_DIR="/system/etc"
ADAPTER_INIT_DIR="/system/etc/init"

# ============================================================
# Parse arguments
# ============================================================
TARGET=""
DO_REBOOT=false

for arg in "$@"; do
    case "$arg" in
        --target=*) TARGET="${arg#*=}" ;;
        --reboot)   DO_REBOOT=true ;;
        --help|-h)
            echo "Usage: $0 [--target=TARGET] [--reboot]"
            echo ""
            echo "Targets:"
            echo "  oh-services   Deploy patched OH system services"
            echo "  android-rt    Deploy Android runtime (framework.jar, ART libs)"
            echo "  adapter       Deploy adapter layer (appspawn-x, bridge, configs)"
            echo "  all           Deploy everything"
            echo "  check         Check device connection and deployment status"
            echo ""
            echo "Options:"
            echo "  --reboot      Reboot device after deployment"
            exit 0 ;;
    esac
done

[ -z "$TARGET" ] && { log_error "No target specified. Use --target=all (or --help)"; exit 1; }

# ============================================================
# Device connection check
# ============================================================
check_device() {
    log_info "Checking device connection..."

    if ! command -v hdc &>/dev/null; then
        log_error "hdc not found in PATH"
        return 1
    fi

    local device
    device=$(hdc list targets 2>/dev/null | head -1)
    if [ -z "$device" ] || [ "$device" = "[Empty]" ]; then
        log_error "No device connected. Connect DAYU600 via USB and retry."
        return 1
    fi

    log_ok "Device connected: $device"

    # Get device info
    local os_version
    os_version=$(hdc shell param get const.ohos.fullname 2>/dev/null || echo "unknown")
    log_info "OS: $os_version"

    local api_version
    api_version=$(hdc shell param get const.ohos.apiversion 2>/dev/null || echo "unknown")
    log_info "API: $api_version"
}

# ============================================================
# Remount /system as read-write
# ============================================================
remount_system() {
    log_info "Remounting /system as read-write..."
    hdc shell mount -o rw,remount / 2>/dev/null || true
    hdc shell mount -o rw,remount /system 2>/dev/null || true
    log_ok "/system remounted"
}

# ============================================================
# Deploy OH system services
# ============================================================
deploy_oh_services() {
    log_info "=== Deploying OH system services ==="

    local oh_out="$OUT_DIR/oh-services"
    if [ ! -d "$oh_out" ]; then
        log_error "OH service artifacts not found in $oh_out"
        log_error "Run: ./build.sh --target=oh-services first"
        return 1
    fi

    remount_system

    # Stop affected services before replacing
    log_info "Stopping OH system services..."
    hdc shell "kill -9 \$(pidof ability_manager_service)" 2>/dev/null || true
    hdc shell "kill -9 \$(pidof window_manager_service)" 2>/dev/null || true
    hdc shell "kill -9 \$(pidof bundle_manager_service)" 2>/dev/null || true
    sleep 2

    # Find actual .z.so location on device
    for artifact in "${!OH_SERVICE_DEPLOY[@]}"; do
        local src
        src=$(find "$oh_out" -name "$artifact" ! -path "*/lib.unstripped/*" | head -1)
        if [ -z "$src" ]; then
            log_warn "Artifact not found locally: $artifact"
            continue
        fi

        # Find actual path on device (may be in /system/lib64/ or /system/lib64/platformsdk/)
        local device_path
        device_path=$(hdc shell "find /system/lib64 -name '$artifact' | head -1" 2>/dev/null | tr -d '\r\n')
        if [ -z "$device_path" ]; then
            device_path="${OH_SERVICE_DEPLOY[$artifact]}"
            log_warn "Using default path: $device_path"
        fi

        # Backup original on device
        hdc shell "cp $device_path ${device_path}.bak" 2>/dev/null || true

        # Push new file
        log_info "Pushing $artifact -> $device_path"
        hdc file send "$src" "$device_path"
        hdc shell "chmod 644 $device_path"
        log_ok "$artifact deployed"
    done

    log_ok "OH system services deployed"
}

# ============================================================
# Deploy Android runtime
# ============================================================
deploy_android_runtime() {
    log_info "=== Deploying Android runtime ==="

    remount_system

    # Create Android framework directory structure
    hdc shell "mkdir -p $ANDROID_FRAMEWORK_DIR"
    hdc shell "mkdir -p $ANDROID_LIB_DIR"

    # Deploy Java artifacts (platform-independent DEX bytecode)
    local java_out="$OUT_DIR/java"
    if [ -d "$java_out" ]; then
        for jar in "$java_out"/*.jar; do
            [ -f "$jar" ] || continue
            local name=$(basename "$jar")
            log_info "Pushing $name -> $ANDROID_FRAMEWORK_DIR/"
            hdc file send "$jar" "$ANDROID_FRAMEWORK_DIR/$name"
            log_ok "$name"
        done
    else
        log_warn "Java artifacts not found in $java_out"
    fi

    # Deploy resource package
    local res_out="$OUT_DIR/res"
    if [ -d "$res_out" ]; then
        for res in "$res_out"/*; do
            [ -f "$res" ] || continue
            local name=$(basename "$res")
            log_info "Pushing $name -> $ANDROID_FRAMEWORK_DIR/"
            hdc file send "$res" "$ANDROID_FRAMEWORK_DIR/$name"
            log_ok "$name"
        done
    fi

    # Deploy cross-compiled native libraries (musl-linked)
    local native_out="$OUT_DIR/native"
    if [ -d "$native_out" ]; then
        for so in "$native_out"/*.so; do
            [ -f "$so" ] || continue
            local name=$(basename "$so")
            log_info "Pushing $name -> $ANDROID_LIB_DIR/"
            hdc file send "$so" "$ANDROID_LIB_DIR/$name"
            hdc shell "chmod 755 $ANDROID_LIB_DIR/$name"
            log_ok "$name"
        done
    else
        log_warn "Native artifacts not found in $native_out"
    fi

    log_ok "Android runtime deployed"
}

# ============================================================
# Deploy adapter layer
# ============================================================
deploy_adapter() {
    log_info "=== Deploying adapter layer ==="

    remount_system

    # appspawn-x executable
    local appspawnx="$OUT_DIR/adapter-modules/appspawn-x"
    if [ -f "$appspawnx" ]; then
        log_info "Pushing appspawn-x -> $ADAPTER_BIN_DIR/"
        hdc file send "$appspawnx" "$ADAPTER_BIN_DIR/appspawn-x"
        hdc shell "chmod 755 $ADAPTER_BIN_DIR/appspawn-x"
        log_ok "appspawn-x"
    else
        log_warn "appspawn-x not found in $OUT_DIR/adapter-modules/"
    fi

    # liboh_adapter_bridge.so
    local bridge="$OUT_DIR/adapter-modules/liboh_adapter_bridge.z.so"
    if [ -f "$bridge" ]; then
        log_info "Pushing liboh_adapter_bridge.z.so -> $ADAPTER_LIB_DIR/"
        hdc file send "$bridge" "$ADAPTER_LIB_DIR/liboh_adapter_bridge.z.so"
        hdc shell "chmod 755 $ADAPTER_LIB_DIR/liboh_adapter_bridge.z.so"
        log_ok "liboh_adapter_bridge.z.so"
    fi

    # libapk_installer.so
    local installer="$OUT_DIR/adapter-modules/libapk_installer.z.so"
    if [ -f "$installer" ]; then
        log_info "Pushing libapk_installer.z.so -> $ADAPTER_LIB_DIR/"
        hdc file send "$installer" "$ADAPTER_LIB_DIR/libapk_installer.z.so"
        hdc shell "chmod 755 $ADAPTER_LIB_DIR/libapk_installer.z.so"
        log_ok "libapk_installer.z.so"
    fi

    # Configuration files
    local cfg_dir="$ADAPTER_ROOT/framework/appspawn-x/config"
    if [ -f "$cfg_dir/appspawn_x.cfg" ]; then
        log_info "Pushing appspawn_x.cfg -> $ADAPTER_INIT_DIR/"
        hdc file send "$cfg_dir/appspawn_x.cfg" "$ADAPTER_INIT_DIR/appspawn_x.cfg"
        log_ok "appspawn_x.cfg"
    fi

    if [ -f "$cfg_dir/appspawn_x_sandbox.json" ]; then
        log_info "Pushing appspawn_x_sandbox.json -> $ADAPTER_ETC_DIR/"
        hdc file send "$cfg_dir/appspawn_x_sandbox.json" "$ADAPTER_ETC_DIR/appspawn_x_sandbox.json"
        log_ok "appspawn_x_sandbox.json"
    fi

    # oh-adapter-framework.jar
    local adapter_jar="$OUT_DIR/java/oh-adapter-framework.jar"
    if [ -f "$adapter_jar" ]; then
        hdc shell "mkdir -p $ANDROID_FRAMEWORK_DIR"
        log_info "Pushing oh-adapter-framework.jar -> $ANDROID_FRAMEWORK_DIR/"
        hdc file send "$adapter_jar" "$ANDROID_FRAMEWORK_DIR/oh-adapter-framework.jar"
        log_ok "oh-adapter-framework.jar"
    fi

    # Create required data directories
    hdc shell "mkdir -p /data/service/el1/public/appspawnx"
    hdc shell "chmod 0711 /data/service/el1/public/appspawnx"
    hdc shell "mkdir -p /data/misc/appspawnx/dalvik-cache/arm64"
    hdc shell "chmod 0711 /data/misc/appspawnx/dalvik-cache"
    log_ok "Data directories created"

    log_ok "Adapter layer deployed"
}

# ============================================================
# Check deployment status
# ============================================================
check_deployment() {
    log_info "=== Checking deployment status ==="

    check_device || return 1

    echo ""
    log_info "OH system services:"
    for artifact in "${!OH_SERVICE_DEPLOY[@]}"; do
        local path="${OH_SERVICE_DEPLOY[$artifact]}"
        local actual
        actual=$(hdc shell "find /system/lib64 -name '$artifact' | head -1" 2>/dev/null | tr -d '\r\n')
        if [ -n "$actual" ]; then
            local size
            size=$(hdc shell "ls -l $actual" 2>/dev/null | awk '{print $5}')
            log_ok "$artifact ($size bytes) at $actual"
        else
            log_warn "$artifact not found on device"
        fi
    done

    echo ""
    log_info "Android runtime:"
    for f in framework.jar oh-adapter-framework.jar; do
        if hdc shell "test -f $ANDROID_FRAMEWORK_DIR/$f" 2>/dev/null; then
            log_ok "$f"
        else
            log_warn "$f not found at $ANDROID_FRAMEWORK_DIR/"
        fi
    done

    echo ""
    log_info "Adapter layer:"
    for f in appspawn-x; do
        if hdc shell "test -f $ADAPTER_BIN_DIR/$f" 2>/dev/null; then
            log_ok "$f"
        else
            log_warn "$f not found"
        fi
    done
    for f in liboh_adapter_bridge.z.so libapk_installer.z.so; do
        if hdc shell "test -f $ADAPTER_LIB_DIR/$f" 2>/dev/null; then
            log_ok "$f"
        else
            log_warn "$f not found"
        fi
    done

    echo ""
    log_info "appspawn-x service:"
    local pid
    pid=$(hdc shell "pidof appspawn-x" 2>/dev/null | tr -d '\r\n')
    if [ -n "$pid" ]; then
        log_ok "appspawn-x running (PID: $pid)"
    else
        log_warn "appspawn-x not running"
    fi
}

# ============================================================
# Main dispatch
# ============================================================

case "$TARGET" in
    check)
        check_deployment
        ;;
    oh-services)
        check_device || exit 1
        deploy_oh_services
        [ "$DO_REBOOT" = true ] && { log_info "Rebooting..."; hdc shell reboot; }
        ;;
    android-rt)
        check_device || exit 1
        deploy_android_runtime
        [ "$DO_REBOOT" = true ] && { log_info "Rebooting..."; hdc shell reboot; }
        ;;
    adapter)
        check_device || exit 1
        deploy_adapter
        [ "$DO_REBOOT" = true ] && { log_info "Rebooting..."; hdc shell reboot; }
        ;;
    all)
        check_device || exit 1
        deploy_oh_services
        deploy_android_runtime
        deploy_adapter
        log_ok "=== All components deployed ==="
        if [ "$DO_REBOOT" = true ]; then
            log_info "Rebooting device..."
            hdc shell reboot
        else
            log_warn "Reboot required for changes to take effect"
            log_warn "Run: hdc shell reboot"
        fi
        ;;
    *)
        log_error "Unknown target: $TARGET"
        exit 1
        ;;
esac
