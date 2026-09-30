#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# discover_skia_rtti_syms.sh
#
# Discovers the exact set of _ZTI*/_ZTS* symbols that Android libhwui
# needs from Skia when linked against OH's ORIGINAL libskia_canvaskit.z.so
# (i.e. the -fno-rtti variant that ships on the device), and regenerates
# framework/surface/jni/skia_rtti_shim/skia_class_list.inc.
#
# Strategy:
#   1. Link libhwui.so using a STRICTER ldflags set than link_libhwui.sh:
#      - drop --unresolved-symbols=ignore-in-object-files
#      - drop --allow-shlib-undefined
#      - point to ORIGINAL libskia_canvaskit.z.so (NOT the -frtti rebuilt one)
#      so that ld.lld reports every undefined symbol, including _ZTI*.
#   2. Grep the link log for `undefined symbol: _ZTI...` / `_ZTS...`.
#   3. Demangle each one via c++filt; extract the class name.
#   4. Emit SKIA_RTTI_CLASS(<name>) lines into skia_class_list.inc.
#   5. Rebuild the shim and re-link libhwui with the full link_libhwui.sh
#      (now that the shim is on the -L path). Iterate until the undefined
#      _ZTI* set is empty (typically 1-2 rounds).
#
# This script is idempotent: running it on a fixed-point state produces
# the same skia_class_list.inc.
set -o pipefail

OH="${OH_ROOT:-$HOME/oh}"
ADAPTER="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
OH_OUT=$OH/out/rk3568
SR=$OH_OUT/obj/third_party/musl/usr
SYS_LIB=$OH_OUT/packages/phone/system/lib

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
CXXFILT=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-cxxfilt

OUT_HWUI=$ADAPTER/out/hwui-build
OBJ=$OUT_HWUI/obj
OUT_SHIM=$ADAPTER/out/skia-rtti-shim
DISCOVERY=$ADAPTER/out/skia-rtti-shim/discovery
mkdir -p $DISCOVERY

SHIM_DIR=$ADAPTER/framework/surface/jni/skia_rtti_shim
CLASS_LIST=$SHIM_DIR/skia_class_list.inc

# Original OH Skia (-fno-rtti) — this is the REAL target we want libhwui
# to be able to link against on-device. NOT the -frtti rebuilt copy under
# $OH/out/rk3568/thirdparty/skia/.
ORIG_SKIA_DIR=$SYS_LIB/platformsdk
if [ ! -f $ORIG_SKIA_DIR/libskia_canvaskit.z.so ]; then
    echo "ERROR: original libskia_canvaskit.z.so not found at $ORIG_SKIA_DIR"
    echo "       Expected the -fno-rtti OH system copy (not the rebuilt one)."
    exit 1
fi

echo "=========================================="
echo "  skia_rtti_shim symbol discovery"
echo "=========================================="
echo "  libhwui objs: $OBJ"
echo "  skia (orig):  $ORIG_SKIA_DIR/libskia_canvaskit.z.so"
echo "  class list:   $CLASS_LIST"
echo ""

if [ ! -d $OBJ ] || [ -z "$(ls $OBJ/*.o 2>/dev/null)" ]; then
    echo "ERROR: no libhwui object files in $OBJ"
    echo "       Run compile_libhwui.sh first."
    exit 1
fi

# Strict link flags — the whole point is to let ld.lld COMPLAIN about
# every undefined _ZTI*/_ZTS*.
LDFLAGS="--target=arm-linux-ohos -march=armv7-a -mfloat-abi=softfp"
LDFLAGS="$LDFLAGS -fuse-ld=lld -fPIC -shared"
LDFLAGS="$LDFLAGS --sysroot=$SR -L$SR/lib/arm-linux-ohos"
LDFLAGS="$LDFLAGS -B$SR/lib/arm-linux-ohos"
LDFLAGS="$LDFLAGS -L$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/arm-linux-ohos"
LDFLAGS="$LDFLAGS -Wl,--gc-sections -Wl,--as-needed"
# NO --allow-shlib-undefined
# NO --unresolved-symbols=ignore-in-object-files
# NO -z lazy
LDFLAGS="$LDFLAGS -Wl,-soname=libhwui.so"

LIBS="-L$ADAPTER/out/adapter"
LIBS="$LIBS -L$ADAPTER/out/aosp_lib"
LIBS="$LIBS -L$ORIG_SKIA_DIR"                                       # original Skia
LIBS="$LIBS -L$OH_OUT/innerkits/ohos-arm/graphic_2d/EGL"
LIBS="$LIBS -L$OH_OUT/innerkits/ohos-arm/graphic_2d/GLESv3"
# If shim has been built at least once, let its .so satisfy what it can.
if [ -f $OUT_SHIM/liboh_skia_rtti_shim.so ]; then
    LIBS="$LIBS -L$OUT_SHIM -loh_skia_rtti_shim"
fi
LIBS="$LIBS -loh_hwui_shim"
LIBS="$LIBS -lskia_canvaskit.z"
LIBS="$LIBS -lEGL -lGLESv3"
LIBS="$LIBS -lminikin -lharfbuzz_ng -lft2 -licuuc -licui18n"
LIBS="$LIBS -lutils -lcutils -lbase -llog"
LIBS="$LIBS -ldl -lc++ -lm -lc -lpthread"

OBJS=$(ls $OBJ/*.o | tr '\n' ' ')
NUM_OBJS=$(ls $OBJ/*.o | wc -l)
LINK_LOG=$DISCOVERY/strict_link.log

echo "  linking libhwui.so under STRICT resolution ($NUM_OBJS object files)"
$CXX $LDFLAGS -o $DISCOVERY/libhwui.strict.so \
    $OBJS \
    $LIBS \
    -Wl,-rpath-link=$SYS_LIB \
    -Wl,-rpath-link=$ORIG_SKIA_DIR \
    > $LINK_LOG 2>&1 || true

# ld.lld error lines look like:
#   ld.lld: error: undefined symbol: typeinfo for SkDrawable
# or
#   ld.lld: error: undefined symbol: _ZTI10SkDrawable
# We capture both forms, normalize to mangled, then demangle to class name.
echo "  extracting undefined _ZTI*/_ZTS* symbols"

RAW=$DISCOVERY/undef_raw.txt
ZTI=$DISCOVERY/zti_symbols.txt
ZTS=$DISCOVERY/zts_symbols.txt

# 1. Mangled-form undefined refs
grep -oE '_ZTI[0-9A-Za-z_]+' $LINK_LOG | sort -u > $ZTI || true
grep -oE '_ZTS[0-9A-Za-z_]+' $LINK_LOG | sort -u > $ZTS || true

# 2. Typeinfo-for human form — demangle by taking the class name after
#    "typeinfo for " and remangling via c++filt reverse isn't trivial;
#    instead we rely on ld.lld's `error: undefined symbol: typeinfo for X`
#    where X is the demangled name. We match both the demangled text AND
#    the raw _ZTI symbol in the log.
grep -E 'undefined (symbol|hidden symbol|reference)' $LINK_LOG > $RAW || true

# Demangle each _ZTI symbol to a class name.
DEMANGLED=$DISCOVERY/demangled_classes.txt
> $DEMANGLED
while read sym; do
    [ -z "$sym" ] && continue
    name=$($CXXFILT "$sym" | sed -E 's/^typeinfo for //')
    # Keep only top-level Sk* names for SKIA_RTTI_CLASS; nested names
    # (containing "::") get flagged for manual review — they need a
    # different declaration style (nested class in C++).
    case "$name" in
        Sk*::*)
            echo "NESTED:$name" >> $DEMANGLED
            ;;
        Sk*)
            echo "FLAT:$name" >> $DEMANGLED
            ;;
        *)
            echo "OTHER:$name" >> $DEMANGLED
            ;;
    esac
done < $ZTI

FLAT_NAMES=$(grep '^FLAT:' $DEMANGLED | sed 's/^FLAT://' | sort -u)
NESTED_NAMES=$(grep '^NESTED:' $DEMANGLED | sed 's/^NESTED://' | sort -u)
OTHER_NAMES=$(grep '^OTHER:' $DEMANGLED | sed 's/^OTHER://' | sort -u)

FLAT_COUNT=$(echo "$FLAT_NAMES" | grep -c . || true)
NESTED_COUNT=$(echo "$NESTED_NAMES" | grep -c . || true)
OTHER_COUNT=$(echo "$OTHER_NAMES" | grep -c . || true)

echo ""
echo "  undefined _ZTI symbol counts:"
echo "    flat Sk* classes:    $FLAT_COUNT"
echo "    nested Sk*::Xx:      $NESTED_COUNT"
echo "    non-Skia (unexpected): $OTHER_COUNT"

if [ "$NESTED_COUNT" -gt 0 ]; then
    echo ""
    echo "  NESTED classes require manual class_list.inc update:"
    echo "$NESTED_NAMES" | sed 's/^/    /'
fi
if [ "$OTHER_COUNT" -gt 0 ]; then
    echo ""
    echo "  OTHER undefined typeinfo (not Sk*):"
    echo "$OTHER_NAMES" | sed 's/^/    /'
    echo "  (these are likely missing libs, not a shim problem)"
fi

# Regenerate skia_class_list.inc if we got any flat names.
if [ "$FLAT_COUNT" -gt 0 ]; then
    TMP=$DISCOVERY/skia_class_list.inc.new
    {
        echo "// skia_class_list.inc — auto-generated by discover_skia_rtti_syms.sh"
        echo "// Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "// Source: strict libhwui link against $ORIG_SKIA_DIR/libskia_canvaskit.z.so"
        echo "// Do not hand-edit."
        echo ""
        echo "$FLAT_NAMES" | while read n; do
            [ -z "$n" ] && continue
            echo "SKIA_RTTI_CLASS($n)"
        done
        if [ "$NESTED_COUNT" -gt 0 ]; then
            echo ""
            echo "// --- NESTED names, require manual nested-class declarations ---"
            echo "$NESTED_NAMES" | while read n; do
                [ -z "$n" ] && continue
                echo "// TODO: nested $n"
            done
        fi
    } > $TMP

    if ! diff -q $TMP $CLASS_LIST > /dev/null 2>&1; then
        echo ""
        echo "  class list changed; writing new $CLASS_LIST"
        cp $TMP $CLASS_LIST
        echo "  now re-run compile_skia_rtti_shim.sh and re-link libhwui."
    else
        echo ""
        echo "  class list unchanged — FIXED POINT REACHED."
    fi
else
    echo ""
    if [ -s $ZTI ]; then
        echo "  _ZTI symbols observed but none matched Sk*; investigate."
    else
        echo "  no undefined _ZTI symbols — libhwui link is clean under strict mode."
        echo "  (either shim already provides everything, or libhwui was built"
        echo "   without -frtti references, or nothing in libhwui inherits from Sk*)"
    fi
fi

echo ""
echo "=========================================="
echo "  Discovery artifacts: $DISCOVERY/"
echo "    strict_link.log    — raw linker output"
echo "    zti_symbols.txt    — undefined _ZTI* symbols"
echo "    zts_symbols.txt    — undefined _ZTS* symbols"
echo "    demangled_classes.txt — FLAT:/NESTED:/OTHER: classified"
echo "=========================================="
