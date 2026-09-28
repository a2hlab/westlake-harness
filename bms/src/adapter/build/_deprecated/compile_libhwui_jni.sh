#!/bin/bash
# Legacy wrapper (2026-05-12 G2.14bf sedimentation, [C-12] fix) — JNI source
# compilation merged into unified compile_libhwui.sh phase 1 (compile_jni_files()).
# Output dir is now $OUT_BUILD/obj (same as link), no more dual-dir cp drift.
# See compile_libhwui.sh header [C-12] for the full root-cause documentation.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/compile_libhwui.sh" --phase=1 "$@"
