#!/bin/bash
# push_so.sh - Push patched OH system service .so files to DAYU600 device
#
# Usage:
#   ./build/push_so.sh                          # Push all .so files
#   ./build/push_so.sh all                      # Push all .so files
#   ./build/push_so.sh libabilityms.z.so        # Push single file
#   ./build/push_so.sh libabilityms.z.so libbms.z.so  # Push multiple files
#   ./build/push_so.sh --list                   # List all managed .so files
#   ./build/push_so.sh --restore                # Restore all from backups
#   ./build/push_so.sh --restore libabilityms.z.so    # Restore single file
#   ./build/push_so.sh --src=/path/to/dir libabilityms.z.so  # Custom source dir
#
# Features:
#   - Only needs .so filename, device path resolved automatically
#   - Backs up original files (skips if backup already exists)
#   - Stops foundation service before push, reboots after
#   - Supports selective or batch deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default local source directory for .so files
DEFAULT_SRC_DIR="$ADAPTER_ROOT/out/oh-service"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*"; }
log_step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

# ============================================================
# .so file registry: filename -> device path
# ============================================================
declare -A SO_DEVICE_PATH
SO_DEVICE_PATH[libabilityms.z.so]="/system/lib64/platformsdk"
SO_DEVICE_PATH[libappms.z.so]="/system/lib64"
SO_DEVICE_PATH[libscene_session_manager.z.so]="/system/lib64/platformsdk"
SO_DEVICE_PATH[libscene_session.z.so]="/system/lib64/platformsdk"
SO_DEVICE_PATH[libbms.z.so]="/system/lib64"

# All managed .so names (ordered)
ALL_SO_NAMES=(libabilityms.z.so libappms.z.so libscene_session_manager.z.so libscene_session.z.so libbms.z.so)

# ============================================================
# Parse arguments
# ============================================================
SRC_DIR="$DEFAULT_SRC_DIR"
DO_RESTORE=false
DO_LIST=false
NO_REBOOT=false
SELECTED_FILES=()

for arg in "$@"; do
    case "$arg" in
        --src=*)     SRC_DIR="${arg#*=}" ;;
        --restore)   DO_RESTORE=true ;;
        --list)      DO_LIST=true ;;
        --no-reboot) NO_REBOOT=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [so_filename ...]"
            echo ""
            echo "Push patched OH .so files to DAYU600 device via hdc."
            echo ""
            echo "Arguments:"
            echo "  (none) or all              Push all managed .so files"
            echo "  <name.z.so> [<name.z.so>]  Push specified .so files only"
            echo ""
            echo "Options:"
            echo "  --src=DIR        Local directory containing .so files (default: out/oh-service/)"
            echo "  --restore        Restore original .so from .bak backups"
            echo "  --list           List all managed .so files and their device paths"
            echo "  --no-reboot      Skip reboot after push"
            echo "  -h, --help       Show this help"
            echo ""
            echo "Managed .so files:"
            for name in "${ALL_SO_NAMES[@]}"; do
                echo "  $name  ->  ${SO_DEVICE_PATH[$name]}/"
            done
            exit 0 ;;
        all) ;; # push all, same as no args
        *.so)
            if [ -z "${SO_DEVICE_PATH[$arg]+x}" ]; then
                log_error "Unknown .so file: $arg"
                echo "Managed files: ${ALL_SO_NAMES[*]}"
                exit 1
            fi
            SELECTED_FILES+=("$arg")
            ;;
        *)
            log_error "Unknown argument: $arg"
            echo "Use --help for usage."
            exit 1 ;;
    esac
done

# If no specific files selected, use all
if [ ${#SELECTED_FILES[@]} -eq 0 ]; then
    SELECTED_FILES=("${ALL_SO_NAMES[@]}")
fi

# ============================================================
# --list: Show managed files and exit
# ============================================================
if [ "$DO_LIST" = true ]; then
    echo ""
    echo "Managed .so files:"
    echo "─────────────────────────────────────────────────────────────────"
    printf "  %-38s %s\n" "Filename" "Device Path"
    echo "─────────────────────────────────────────────────────────────────"
    for name in "${ALL_SO_NAMES[@]}"; do
        printf "  %-38s %s/\n" "$name" "${SO_DEVICE_PATH[$name]}"
    done
    echo ""
    echo "Local source: $SRC_DIR"
    exit 0
fi

# ============================================================
# Device connection check
# ============================================================
check_device() {
    if ! command -v hdc &>/dev/null; then
        log_error "hdc not found in PATH"
        exit 1
    fi

    local device
    device=$(hdc list targets 2>/dev/null | head -1)
    if [ -z "$device" ] || [ "$device" = "[Empty]" ]; then
        log_error "No device connected. Connect DAYU600 via USB."
        exit 1
    fi
    log_ok "Device: $device"
}

# ============================================================
# Remount /system as read-write
# ============================================================
remount_system() {
    log_step "Remounting /system as read-write..."
    hdc shell "mount -o rw,remount /" 2>/dev/null || true
    hdc shell "mount -o rw,remount /system" 2>/dev/null || true
    log_ok "Filesystem remounted"
}

# ============================================================
# Backup: skip if .bak already exists (protect originals)
# ============================================================
backup_files() {
    log_step "Backing up original .so files..."
    local backed=0 skipped=0

    for name in "${SELECTED_FILES[@]}"; do
        local dir="${SO_DEVICE_PATH[$name]}"
        local full="$dir/$name"
        local bak="${full}.bak"

        # Check if backup already exists
        local bak_exists
        bak_exists=$(hdc shell "test -f '$bak' && echo yes || echo no" 2>/dev/null | tr -d '\r\n')

        if [ "$bak_exists" = "yes" ]; then
            log_warn "Backup exists, skip: $bak"
            ((skipped++))
        else
            # Check if original file exists before backing up
            local orig_exists
            orig_exists=$(hdc shell "test -f '$full' && echo yes || echo no" 2>/dev/null | tr -d '\r\n')
            if [ "$orig_exists" = "yes" ]; then
                hdc shell "cp '$full' '$bak'"
                log_ok "Backed up: $name -> ${name}.bak"
                ((backed++))
            else
                log_warn "Original not found on device: $full"
            fi
        fi
    done

    echo "    Backed up: $backed, Skipped (already exists): $skipped"
}

# ============================================================
# Stop foundation service
# ============================================================
stop_foundation() {
    log_step "Stopping foundation service..."

    # Use begetctl to gracefully stop (preferred over kill -9)
    hdc shell "begetctl stop_service foundationserver" 2>/dev/null || true
    sleep 2

    # Verify foundation stopped
    local pid
    pid=$(hdc shell "pidof foundation" 2>/dev/null | tr -d '\r\n')
    if [ -n "$pid" ]; then
        log_warn "foundation still running (PID: $pid), force stopping..."
        hdc shell "kill -9 $pid" 2>/dev/null || true
        sleep 1
    fi
    log_ok "Foundation service stopped"
}

# ============================================================
# Push .so files to device
# ============================================================
push_files() {
    log_step "Pushing .so files to device..."
    local success=0 fail=0

    for name in "${SELECTED_FILES[@]}"; do
        local dir="${SO_DEVICE_PATH[$name]}"
        local device_full="$dir/$name"

        # Find local .so file (search recursively in SRC_DIR)
        local local_file=""
        if [ -f "$SRC_DIR/$name" ]; then
            local_file="$SRC_DIR/$name"
        else
            # Search recursively, exclude lib.unstripped (debug symbols, too large)
            local_file=$(find "$SRC_DIR" -name "$name" ! -path "*/lib.unstripped/*" 2>/dev/null | head -1)
        fi

        if [ -z "$local_file" ] || [ ! -f "$local_file" ]; then
            log_error "Local file not found: $name (searched in $SRC_DIR)"
            ((fail++))
            continue
        fi

        local size
        size=$(stat -c%s "$local_file" 2>/dev/null || stat -f%z "$local_file" 2>/dev/null || echo "?")
        log_info "Pushing $name ($size bytes) -> $device_full"
        hdc file send "$local_file" "$device_full"
        hdc shell "chmod 644 '$device_full'"
        log_ok "$name deployed"
        ((success++))
    done

    echo ""
    if [ $fail -gt 0 ]; then
        log_warn "Result: $success succeeded, $fail failed"
    else
        log_ok "Result: $success files pushed successfully"
    fi

    return $fail
}

# ============================================================
# Restore from backups
# ============================================================
restore_files() {
    log_step "Restoring .so files from backups..."

    check_device
    remount_system
    stop_foundation

    local restored=0

    for name in "${SELECTED_FILES[@]}"; do
        local dir="${SO_DEVICE_PATH[$name]}"
        local full="$dir/$name"
        local bak="${full}.bak"

        local bak_exists
        bak_exists=$(hdc shell "test -f '$bak' && echo yes || echo no" 2>/dev/null | tr -d '\r\n')

        if [ "$bak_exists" = "yes" ]; then
            hdc shell "cp '$bak' '$full'"
            hdc shell "chmod 644 '$full'"
            log_ok "Restored: $bak -> $name"
            ((restored++))
        else
            log_error "Backup not found: $bak"
        fi
    done

    log_ok "$restored files restored"

    if [ "$NO_REBOOT" = false ]; then
        log_step "Rebooting device..."
        hdc shell reboot
        log_ok "Device is rebooting"
    fi
}

# ============================================================
# Main
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          OH System Service .so Deployment Tool          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Handle --restore mode
if [ "$DO_RESTORE" = true ]; then
    restore_files
    exit 0
fi

# Print selected files
log_info "Selected files: ${SELECTED_FILES[*]}"
log_info "Source dir: $SRC_DIR"
echo ""

# Step 1: Check device
check_device

# Step 2: Remount filesystem
remount_system

# Step 3: Backup originals (skip if backup exists)
backup_files

# Step 4: Stop foundation service
stop_foundation

# Step 5: Push .so files
push_files
push_result=$?

# Step 6: Reboot
if [ "$NO_REBOOT" = false ]; then
    log_step "Rebooting device..."
    hdc shell reboot
    log_ok "Device is rebooting. Wait ~60s, then: hdc list targets"
else
    log_warn "Skipped reboot (--no-reboot). Run 'hdc shell reboot' manually."
fi

echo ""
echo "Done."
exit $push_result
