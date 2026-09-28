#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# check_skia_rtti_coverage.sh
#
# Verify that liboh_skia_rtti_shim.so provides every _ZTI*/_ZTS* Sk typeinfo
# symbol that the current libhwui .o set references as undefined. Exits 1
# with a diagnostic demangled list if any needed symbol is missing from the
# shim — call from link_libhwui.sh BEFORE linking, so class list drift is
# caught at build time instead of at runtime.
#
# This is the CI defense described in doc/skia_rtti_shim_design.html §9
# follow-ups and compile_report.html §K.9. It makes the "did I remember to
# re-run discover_skia_rtti_syms.sh + compile_skia_rtti_shim.sh after
# touching something" question automatic instead of manual.
#
# Exit codes:
#   0  — every libhwui .o UND Sk typeinfo symbol is provided by the shim
#   1  — gap exists (details printed to stderr), or prerequisite missing

set -o pipefail

OH="${OH:-${OH_ROOT:-$HOME/oh}}"
ADAPTER="${ADAPTER:-${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"

HWUI_OBJ=$ADAPTER/out/hwui-build/obj
SHIM_SO=$ADAPTER/out/skia-rtti-shim/liboh_skia_rtti_shim.so

READELF=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf
NM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm
CXXFILT=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-cxxfilt

# ---- prerequisites ----
if [ ! -d "$HWUI_OBJ" ] || [ -z "$(ls $HWUI_OBJ/*.o 2>/dev/null)" ]; then
    echo "[skia_rtti_check] ERROR: no libhwui .o files at $HWUI_OBJ" >&2
    echo "                          run compile_libhwui.sh first" >&2
    exit 1
fi
if [ ! -f "$SHIM_SO" ]; then
    echo "[skia_rtti_check] ERROR: shim .so not found at $SHIM_SO" >&2
    echo "                          run build/compile_skia_rtti_shim.sh first" >&2
    exit 1
fi
for tool in "$READELF" "$NM" "$CXXFILT"; do
    if [ ! -x "$tool" ]; then
        echo "[skia_rtti_check] ERROR: tool not found: $tool" >&2
        exit 1
    fi
done

TMPDIR=$(mktemp -d /tmp/skia_rtti_check.XXXXXX)
trap 'rm -rf $TMPDIR' EXIT

# ---- collect Sk typeinfo UND demands from libhwui .o files ----
# We want two flavors:
#   _ZTI[0-9]+Sk*                  (flat Sk classes)
#   _ZTIN[0-9]+Sk*                 (nested SkXxx::Yyy classes)
# and likewise for _ZTS. Keep both flat and nested, anything Sk-prefixed.
for f in $HWUI_OBJ/*.o; do
    $READELF --syms "$f" 2>/dev/null | awk '$7 == "UND" {print $8}'
done | grep -E '^_ZT[IS]([0-9]+Sk|N[0-9]+Sk)' | sort -u > "$TMPDIR/needed.txt"

NEEDED_COUNT=$(wc -l < "$TMPDIR/needed.txt")

# ---- collect shim exports ----
# llvm-nm prints versioned symbols with @@VERSION suffix; strip it for
# plain-name comparison against the libhwui .o demand list (which has
# no version tag — .o files reference unversioned symbols).
$NM -D --defined-only "$SHIM_SO" 2>/dev/null \
    | awk '{print $3}' \
    | sed 's/@@.*//' \
    | grep -E '^_ZT[IS]' \
    | sort -u > "$TMPDIR/provided.txt"

PROVIDED_COUNT=$(wc -l < "$TMPDIR/provided.txt")

# ---- diff ----
MISSING=$(comm -23 "$TMPDIR/needed.txt" "$TMPDIR/provided.txt")

if [ -n "$MISSING" ]; then
    echo "[skia_rtti_check] FAIL: libhwui .o files need Sk typeinfo symbols the shim does not provide" >&2
    echo "" >&2
    echo "  Missing symbols:" >&2
    echo "$MISSING" | while read sym; do
        [ -z "$sym" ] && continue
        demangled=$($CXXFILT "$sym" 2>/dev/null || echo "?")
        printf "    %-50s  %s\n" "$sym" "$demangled" >&2
    done
    echo "" >&2
    echo "  Action:" >&2
    echo "    1. bash $ADAPTER/build/internal/discover_skia_rtti_syms.sh" >&2
    echo "       (regenerates skia_class_list.inc from current libhwui .o set)" >&2
    echo "    2. bash $ADAPTER/build/internal/compile_libhwui.sh --phase=2c" >&2
    echo "       (rebuilds skia_rtti_shim with updated class list)" >&2
    echo "    3. Re-run bash $ADAPTER/build/build_aosp_lib.sh --target=libhwui.so" >&2
    echo "" >&2
    echo "  See doc/skia_rtti_shim_design.html §4.5 for the discovery flow." >&2
    exit 1
fi

# ---- success ----
printf '[skia_rtti_check] OK: %d Sk typeinfo UND in libhwui .o, all provided by shim (%d exports)\n' \
    "$NEEDED_COUNT" "$PROVIDED_COUNT"
