#!/bin/bash
# install_app_spawn_x_init.sh — ensure AppSpawnXInit.java is in the
# AOSP oh_adapter_framework java sources.
#
# Context: the adapter project's authoritative copy of AppSpawnXInit.java
# lives at framework/appspawn-x/java/com/android/internal/os/AppSpawnXInit.java.
# The AOSP `oh-adapter-framework` Soong target reads sources from
# device/adapter/oh_adapter_framework/java/**/*.java on ECS. After a repo
# sync, the AOSP-side copy is missing, which causes the rebuilt jar to omit
# AppSpawnXInit.class → appspawn-x preload() fails at runtime (gap 7).
#
# This script is idempotent — it overwrites the AOSP-side copy every time,
# so the authoritative source-of-truth is always framework/appspawn-x/.
#
# Called from: build/restore_after_sync.sh phase A (AOSP restoration)
# Created: 2026-04-11 to close gap 7 permanently.

set -e

ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"

SRC="$ADAPTER_ROOT/framework/appspawn-x/java/com/android/internal/os/AppSpawnXInit.java"
DST_DIR="$AOSP_ROOT/device/adapter/oh_adapter_framework/java/com/android/internal/os"
DST="$DST_DIR/AppSpawnXInit.java"

if [ ! -f "$SRC" ]; then
    echo "ERROR: source not found: $SRC"
    exit 1
fi

if [ ! -d "$AOSP_ROOT/device/adapter/oh_adapter_framework" ]; then
    echo "WARN: AOSP oh_adapter_framework dir not found: $AOSP_ROOT/device/adapter/oh_adapter_framework"
    echo "      (restore_after_sync.sh A1 should have created it — skipping for now)"
    exit 0
fi

mkdir -p "$DST_DIR"
cp "$SRC" "$DST"
echo "OK: AppSpawnXInit.java installed to $DST"
