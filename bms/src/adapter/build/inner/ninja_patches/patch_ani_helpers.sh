#!/bin/bash
# patch_ani_helpers.sh — turn libani_helpers.z.so build edge into a phony.
# libani_helpers depends on libarkruntime (which we phony'd for the same irtoc
# reason), so this library also cannot be produced. Not needed at runtime.
#
# OLD brittle approach: sed on hard-coded line 10 of ani_helpers.ninja.
# NEW robust approach: grep-for-target then sed the matched line in place.
set -e

PROD="${OH_PRODUCT_NAME:-rk3568}"
NINJA_FILE="${OH_ROOT:-$HOME/oh}/out/$PROD/obj/arkcompiler/runtime_core/static_core/plugins/ets/runtime/libani_helpers/ani_helpers.ninja"

if [ ! -f "$NINJA_FILE" ]; then
    echo "[patch_ani_helpers] ERROR: $NINJA_FILE not found — skipping (gn gen not run yet?)" >&2; exit 1
fi

LINE=$(grep -nE "^build arkcompiler/runtime_core/libani_helpers\.z\.so " "$NINJA_FILE" 2>/dev/null | head -1 | cut -d: -f1)

if [ -z "$LINE" ]; then
    if grep -qE "^build arkcompiler/runtime_core/libani_helpers\.z\.so .*: phony" "$NINJA_FILE"; then
        echo "[patch_ani_helpers] already phony — no action"
        exit 0
    fi
    echo "[patch_ani_helpers] ERROR: no libani_helpers.z.so build line found in $NINJA_FILE" >&2
    exit 1
fi

sed -i "${LINE}s|.*|build arkcompiler/runtime_core/libani_helpers.z.so lib.unstripped/arkcompiler/runtime_core/libani_helpers.z.so: phony|" "$NINJA_FILE"
echo "[patch_ani_helpers] applied line $LINE in $NINJA_FILE"
