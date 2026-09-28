#!/bin/bash
# patch_arkruntime.sh — turn the libarkruntime.so build edge into a phony,
# because irtoc segfaults when building the interpreter .bc for this target.
# This project does NOT need libarkruntime.so at runtime — confirmed by the
# user 2026-04-11 — so a phony edge is the correct way to let the build graph
# complete without actually producing (or attempting to produce) the library.
#
# OLD brittle approach: sed on hard-coded line 10 of libarkruntime.ninja.
# NEW robust approach: grep-for-target then sed the matched line in place.
set -e

PROD="${OH_PRODUCT_NAME:-rk3568}"
NINJA_FILE="${OH_ROOT:-$HOME/oh}/out/$PROD/obj/arkcompiler/runtime_core/static_core/runtime/libarkruntime.ninja"

if [ ! -f "$NINJA_FILE" ]; then
    echo "[patch_arkruntime] WARN: $NINJA_FILE not found — skipping (gn gen not run yet?)" >&2
    exit 0
fi

# Find the line starting with "build arkcompiler/runtime_core/libarkruntime.so"
LINE=$(grep -nE "^build arkcompiler/runtime_core/libarkruntime\.so " "$NINJA_FILE" 2>/dev/null | head -1 | cut -d: -f1)

if [ -z "$LINE" ]; then
    # Maybe it's already been phony'd — check for a phony edge with the same output
    if grep -qE "^build arkcompiler/runtime_core/libarkruntime\.so .*: phony" "$NINJA_FILE"; then
        echo "[patch_arkruntime] already phony — no action"
        exit 0
    fi
    echo "[patch_arkruntime] ERROR: no libarkruntime.so build line found in $NINJA_FILE" >&2
    exit 1
fi

# Replace just that line (in place) with a clean phony edge
sed -i "${LINE}s|.*|build arkcompiler/runtime_core/libarkruntime.so lib.unstripped/arkcompiler/runtime_core/libarkruntime.so: phony|" "$NINJA_FILE"
echo "[patch_arkruntime] applied line $LINE in $NINJA_FILE"
