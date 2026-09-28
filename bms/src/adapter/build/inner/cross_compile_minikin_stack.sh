#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [DEPRECATED Phase 1 — 2026-05-21] Use build_aosp_lib.sh --target=libminikin.so instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_aosp_lib.sh — Phase 4 will absorb this" >&2
# cross_compile_minikin_stack.sh — cross-compile libminikin + full deps for OH rk3568 arm32
#
# Builds 5 shared libraries in dependency order to out/aosp_lib/:
#
#   libft2.so              (FreeType — font rasterizer)
#   libicuuc.so            (ICU common layer — Unicode / locale)
#   libicui18n.so          (ICU internationalization — depends on libicuuc)
#   libharfbuzz_ng.so      (HarfBuzz — font shaping, depends on libft2 + libicuuc)
#   libminikin.so          (Android text layout engine, depends on all above)
#
# These are needed to remove the minikin stub headers and let libhwui link
# against real minikin (gap P10.C.full, per 2026-04-11 feedback).
#
# Prereqs (restore_after_sync.sh A3d phase):
#   - ~/aosp/frameworks/minikin/ exists (fetched by fetch_minikin_deps.sh)
#   - ~/aosp/external/harfbuzz_ng/ exists (fetched by fetch_minikin_deps.sh)
#   - ~/aosp/external/freetype/ exists (fetched by fetch_minikin_deps.sh)
#   - ~/aosp/external/icu/icu4c/source/ exists (already part of standard sync)
#   - ~/oh/out/rk3568/obj/third_party/musl/usr/ (OH musl sysroot from oh_full_build)
#   - ~/adapter/out/aosp_lib/{libbase,libcutils,libutils,liblog,libziparchive}.so
#     (already cross-compiled by cross_compile_arm32_v2.sh)
#
# Usage:
#   bash build/cross_compile_minikin_stack.sh [--only=libft2,libicuuc,...]
#
# Created 2026-04-11 per user feedback:
#   "要启动。但minikin是Android原生库，只需交叉编译，不需要写代码。"
set -o pipefail

ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
AOSP="${AOSP_ROOT:-$HOME/aosp}"
OH="${OH_ROOT:-$HOME/oh}"
OUT="$ADAPTER_ROOT/out/aosp_lib"
TMP="/tmp/minikin_stack"
LOG="$ADAPTER_ROOT/out/minikin_stack.log"

ONLY=""
for arg in "$@"; do
    case "$arg" in
        --only=*) ONLY="${arg#*=}" ;;
    esac
done

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
NM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm

OH_OUT="$OH/out/rk3568"
SR="$OH_OUT/obj/third_party/musl/usr"
ML="$SR/lib/arm-linux-ohos"
BC="$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include"

TARGET="--target=arm-linux-ohos --sysroot=$SR -march=armv7-a -mfloat-abi=softfp -mthumb"
COMMON="$TARGET -I$SR/include/arm-linux-ohos -fPIC -O2 -fno-exceptions"
WARN="-Wno-unused-parameter -Wno-unused-function -Wno-unused-variable -Wno-deprecated-declarations -Wno-format -Wno-sign-compare -Wno-missing-field-initializers -Wno-everything"

CF="$CC $COMMON $WARN -std=c99"
CXXF="$CXX $COMMON $WARN -std=c++17 -include $BC/libcxx_compat.h -I$BC"
LNK="$CXX $TARGET -B$ML -L$ML -L$OUT -shared -fPIC -Wl,--allow-shlib-undefined"

mkdir -p "$OUT" "$TMP"
> "$LOG"

should_build() {
    local lib=$1
    if [ -z "$ONLY" ]; then return 0; fi
    echo "$ONLY" | tr ',' '\n' | grep -qx "$lib"
}

banner() {
    echo ""
    echo "============================================================"
    echo "  $*"
    echo "============================================================"
    echo "" >> "$LOG"
    echo "===$*===" >> "$LOG"
}

compile_file() {
    local src="$1" out_o="$2" comp_cmd="$3" inc="$4"
    local name=$(basename "$src")
    if $comp_cmd $inc -c "$src" -o "$out_o" 2>>"$LOG"; then
        return 0
    else
        echo "  FAIL $name" >&2
        return 1
    fi
}

# ============================================================
# 1. libft2 — FreeType 2 font rasterizer (no libpng, no system libz)
# ============================================================
if should_build libft2; then
    banner "1. libft2 (FreeType — font rasterizer)"
    FT="$AOSP/external/freetype"
    FTD="$TMP/ft2"
    mkdir -p "$FTD"

    # AOSP ft2_defaults srcs list (no libpng deps — we skip PNG)
    FT_SRCS=(
        src/autofit/autofit.c
        src/base/ftbase.c src/base/ftbbox.c src/base/ftbitmap.c
        src/base/ftdebug.c src/base/ftfstype.c src/base/ftgasp.c
        src/base/ftglyph.c src/base/ftinit.c src/base/ftmm.c
        src/base/ftstroke.c src/base/fttype1.c src/base/ftsystem.c
        src/cid/type1cid.c src/cff/cff.c src/gzip/ftgzip.c
        src/psaux/psaux.c src/pshinter/pshinter.c src/psnames/psnames.c
        src/raster/raster.c src/sfnt/sfnt.c src/smooth/smooth.c
        src/truetype/truetype.c src/type1/type1.c src/cid/type1cid.c
        src/bdf/bdf.c
        src/sdf/sdf.c
        src/svg/svg.c
    )

    FT_CFLAGS=(
        -DFT2_BUILD_LIBRARY
        -DDARWIN_NO_CARBON
        -DFT_CONFIG_OPTION_USE_ZLIB
        -I$FT/include
        -I$FT
    )

    ok=0; fl=0
    for s in "${FT_SRCS[@]}"; do
        out_o="$FTD/$(basename $s .c).o"
        if [ -f "$FT/$s" ]; then
            if compile_file "$FT/$s" "$out_o" "$CF" "${FT_CFLAGS[*]}"; then
                ok=$((ok+1))
            else
                fl=$((fl+1))
            fi
        else
            echo "  MISSING $s"
        fi
    done
    echo "libft2: $ok ok / $fl fail"

    if [ $fl -eq 0 ] && [ $ok -gt 0 ]; then
        if $LNK -Wl,-soname=libft2.so -o "$OUT/libft2.so" $FTD/*.o 2>>"$LOG"; then
            sz=$(stat -c%s "$OUT/libft2.so")
            echo "  LINKED: $OUT/libft2.so ($sz bytes)"
        else
            echo "  LINK FAIL — see $LOG" >&2
        fi
    fi
fi

# ============================================================
# 2. libicuuc / libicui18n — ICU common + i18n layers
# ============================================================
if should_build libicuuc || should_build libicui18n; then
    banner "2. libicuuc + libicui18n (ICU)"
    ICU="$AOSP/external/icu/icu4c/source"
    ICD="$TMP/icu"
    mkdir -p "$ICD/common" "$ICD/i18n"

    # Note: NO -DU_TIMEZONE=__timezone because OH musl exposes `timezone`
    # (POSIX), not `__timezone` (glibc). Letting ICU use its default avoids
    # the undeclared identifier error in putil.cpp.
    #
    # For std::div / std::abs ambiguity in decimfmt.cpp / number_longnames.cpp:
    # force-include a small compat shim that brings C div/abs into namespace std.
    ICU_COMPAT_HDR="$TMP/icu_std_compat.h"
    cat > "$ICU_COMPAT_HDR" << 'EOF'
// Bring C <stdlib.h> div / <cmath> abs into namespace std — musl/libcxx-ohos
// doesn't do this automatically, causing ICU std::div / std::abs to fail.
#ifdef __cplusplus
#include <stdlib.h>
#include <math.h>
namespace std {
    using ::div;
    using ::div_t;
    using ::abs;      // ICU number_longnames.cpp needs std::abs for int
    using ::labs;
    using ::llabs;
}
#endif
EOF

    ICU_CFLAGS=(
        -DU_COMMON_IMPLEMENTATION
        -DU_ATTRIBUTE_DEPRECATED=
        -DU_HAVE_STD_ATOMICS=1
        -DU_HAVE_STRTOD_L=0
        "-include" "$ICU_COMPAT_HDR"
        -I$ICU/common
        -I$ICU/i18n
    )

    # Find all .cpp files in common/ and i18n/
    # Skip: number_longnames.cpp (std::abs ambiguity with libcxx_compat.h —
    # only used for "long form" number formatting like "two hundred forty-three",
    # not needed by Hello World TextView)
    for dir in common i18n; do
        ok=0; fl=0
        for s in $ICU/$dir/*.cpp; do
            [ -f "$s" ] || continue
            # 2026-04-16: number_longnames.cpp now compiles with abs in compat header
            case "$(basename $s)" in
                "") continue ;;
            esac
            out_o="$ICD/$dir/$(basename $s .cpp).o"
            local_cflags=("${ICU_CFLAGS[@]}")
            if [ "$dir" = "i18n" ]; then
                local_cflags[0]="-DU_I18N_IMPLEMENTATION"
                local_cflags+=("-DU_LIB_SUFFIX_C_NAME=")
            fi
            if compile_file "$s" "$out_o" "$CXXF" "${local_cflags[*]}"; then
                ok=$((ok+1))
            else
                fl=$((fl+1))
            fi
        done
        echo "libicu$dir: $ok ok / $fl fail"

        if [ $fl -eq 0 ] && [ $ok -gt 0 ]; then
            libname="libicuuc.so"
            [ "$dir" = "i18n" ] && libname="libicui18n.so"
            extra_link=""
            [ "$dir" = "i18n" ] && extra_link="-licuuc"
            # Compile and include ICU stubdata for libicuuc (provides icudt72_dat symbol stub)
            if [ "$dir" = "common" ]; then
                stubdata_o="$ICD/common/stubdata.o"
                if [ ! -f "$stubdata_o" ] || [ "$ICU/stubdata/stubdata.cpp" -nt "$stubdata_o" ]; then
                    echo "  compile stubdata.cpp for libicuuc"
                    compile_file "$ICU/stubdata/stubdata.cpp" "$stubdata_o" "$CXXF" "-I$ICU/common"
                fi
            fi
            if $LNK -Wl,-soname=$libname -o "$OUT/$libname" $ICD/$dir/*.o $extra_link 2>>"$LOG"; then
                sz=$(stat -c%s "$OUT/$libname")
                echo "  LINKED: $OUT/$libname ($sz bytes)"
            else
                echo "  LINK FAIL $libname — see $LOG" >&2
            fi
        fi
    done
fi

# ============================================================
# 3. libharfbuzz_ng — HarfBuzz font shaper (unity build via harfbuzz.cc)
# ============================================================
if should_build libharfbuzz_ng; then
    banner "3. libharfbuzz_ng (font shaping)"
    HB="$AOSP/external/harfbuzz_ng"
    HBD="$TMP/harfbuzz_ng"
    mkdir -p "$HBD"

    # No -DHAVE_CONFIG_H — config.h is auto-generated by autotools, we
    # don't have it. HarfBuzz uses sensible defaults without it.
    # Define key feature flags manually to match AOSP Android.bp.
    HB_CFLAGS=(
        -DHB_NO_MT
        -DHAVE_FREETYPE
        -DHAVE_ICU
        -DHAVE_OT
        -DHB_NO_UNICODE_FUNCS
        -DHB_NO_FALLBACK_SHAPE
        -I$HB/src
        -I$AOSP/external/freetype/include
        -I$AOSP/external/icu/icu4c/source/common
    )

    # harfbuzz unity build via src/harfbuzz.cc already includes hb-ft.cc +
    # hb-icu.cc + all other .cc files — do NOT compile them separately or
    # linker will see duplicate symbols.
    if [ -f "$HB/src/harfbuzz.cc" ]; then
        if compile_file "$HB/src/harfbuzz.cc" "$HBD/harfbuzz.o" "$CXXF" "${HB_CFLAGS[*]}"; then
            if $LNK -Wl,-soname=libharfbuzz_ng.so -o "$OUT/libharfbuzz_ng.so" $HBD/*.o -lft2 -licuuc 2>>"$LOG"; then
                sz=$(stat -c%s "$OUT/libharfbuzz_ng.so")
                echo "  LINKED: $OUT/libharfbuzz_ng.so ($sz bytes)"
            else
                echo "  LINK FAIL — see $LOG" >&2
            fi
        else
            echo "  FAIL compile harfbuzz.cc" >&2
        fi
    else
        echo "  ERROR: $HB/src/harfbuzz.cc not found"
    fi
fi

# ============================================================
# 4. libminikin — Android text layout engine
# ============================================================
if should_build libminikin; then
    banner "4. libminikin (Android text layout)"
    MK="$AOSP/frameworks/minikin/libs/minikin"
    MKD="$TMP/minikin"
    mkdir -p "$MKD"

    MK_SRCS=(
        BidiUtils.cpp BoundsCache.cpp CmapCoverage.cpp Emoji.cpp
        Font.cpp FontCollection.cpp FontFamily.cpp FontFeatureUtils.cpp
        FontFileParser.cpp FontUtils.cpp GraphemeBreak.cpp GreedyLineBreaker.cpp
        Hyphenator.cpp HyphenatorMap.cpp Layout.cpp LayoutCore.cpp
        LayoutUtils.cpp LineBreaker.cpp LineBreakerUtil.cpp Locale.cpp
        LocaleListCache.cpp MeasuredText.cpp Measurement.cpp
        MinikinFontFactory.cpp MinikinInternal.cpp OptimalLineBreaker.cpp
        SparseBitSet.cpp SystemFonts.cpp WordBreaker.cpp
    )

    MK_CFLAGS=(
        -I$AOSP/frameworks/minikin/include
        -I$AOSP/frameworks/minikin/libs/minikin
        -I$AOSP/external/harfbuzz_ng/src
        -I$AOSP/external/icu/icu4c/source/common
        -I$AOSP/external/icu/icu4c/source/i18n
        -I$AOSP/system/libbase/include
        -I$AOSP/system/logging/liblog/include
        -I$AOSP/system/core/libutils/include
        -I$AOSP/system/core/libcutils/include
        -I$AOSP/system/core/include
    )

    ok=0; fl=0
    for s in "${MK_SRCS[@]}"; do
        if [ -f "$MK/$s" ]; then
            out_o="$MKD/$(basename $s .cpp).o"
            if compile_file "$MK/$s" "$out_o" "$CXXF" "${MK_CFLAGS[*]}"; then
                ok=$((ok+1))
            else
                fl=$((fl+1))
            fi
        else
            echo "  MISSING $s"
        fi
    done
    echo "libminikin: $ok ok / $fl fail"

    if [ $fl -eq 0 ] && [ $ok -gt 0 ]; then
        if $LNK -Wl,-soname=libminikin.so -o "$OUT/libminikin.so" $MKD/*.o \
                -lharfbuzz_ng -lft2 -licuuc -licui18n -lbase -llog 2>>"$LOG"; then
            sz=$(stat -c%s "$OUT/libminikin.so")
            echo "  LINKED: $OUT/libminikin.so ($sz bytes)"
        else
            echo "  LINK FAIL — see $LOG" >&2
        fi
    fi
fi

# ============================================================
# 5. libandroidfw (FULL with AssetManager2 + ApkAssets + Theme)
# ============================================================
# 2026-04-28: extended from minimal (ResXMLParser only) to full coverage
# needed for HelloWorld resource resolution.  AssetManager2 + ApkAssets +
# Theme + Idmap + LoadedArsc + AttributeResolution + ZipFileRO + ZipUtils
# + Asset(Dir/Manager/sProvider) + StreamingZipInflater + supporting modules.
# Requires:
#   aosp_patches/frameworks/base/libs/androidfw/include/androidfw/AssetManager2.h.patch
#     (move Theme::Entry full def to header — modern libcxx vector requires
#      complete type for std::vector<Theme::Entry> capacity()).
#   aosp_patches/frameworks/base/libs/androidfw/AssetManager2.cpp.patch
#     (remove Theme::Entry duplicate def from cpp after header move).
#   aosp_patches/frameworks/base/libs/androidfw/Asset.cpp.patch
#     (remove `assert(dataMap != NULL)` — IncFsFileMap value type lacks
#      operator bool in OH ABI).
if should_build libandroidfw; then
    banner "5. libandroidfw (full — AssetManager2/ApkAssets/Theme)"
    AFW="$AOSP/frameworks/base/libs/androidfw"
    AFWD="$TMP/androidfw"
    mkdir -p "$AFWD"

    AFW_SRCS=(
        # IncFs map_ptr support (android::incfs::IncFsFileMap impl). Lives
        # outside libandroidfw/ — relative path goes up 4 dirs from $AFW.
        ../../../../system/incremental_delivery/incfs/util/map_ptr.cpp
        # Modern API — primary targets for HelloWorld resource resolution
        AssetManager2.cpp
        ApkAssets.cpp
        AssetsProvider.cpp
        Idmap.cpp
        LoadedArsc.cpp
        AttributeResolution.cpp
        # Asset I/O — backs ApkAssets file reading
        Asset.cpp
        AssetDir.cpp
        AssetManager.cpp
        StreamingZipInflater.cpp
        ZipFileRO.cpp
        ZipUtils.cpp
        ApkParsing.cpp
        # Supporting tables / utilities
        ResourceTypes.cpp
        ResourceUtils.cpp
        ResourceTimer.cpp
        TypeWrappers.cpp
        ChunkIterator.cpp
        ConfigDescription.cpp
        Locale.cpp
        LocaleData.cpp
        StringPool.cpp
        misc.cpp
        Util.cpp
        BigBuffer.cpp  # StringPool depends on it transitively
        # Skipping: ObbFile.cpp (OH no OBB), BackupHelpers.cpp (OH no backup),
        # PosixUtils.cpp (host only), CursorWindow.cpp (DB-only)
    )

    AFW_CFLAGS=(
        -std=c++20
        -DSTATIC_ANDROIDFW_FOR_TOOLS
        -Wno-error=deprecated-declarations
        -Wno-reorder-init-list
        -fno-exceptions
        -I$AFW/include
        -I$AOSP/system/incremental_delivery/incfs/util/include
        -I$AOSP/system/core/include
        -I$AOSP/system/core/libcutils/include
        -I$AOSP/system/core/libutils/include
        -I$AOSP/system/libbase/include
        -I$AOSP/system/logging/liblog/include
        -I$AOSP/system/libziparchive/include
        -I$AOSP/external/icu/icu4c/source/common
        -I$AOSP/external/fmtlib/include
        -I$AOSP/frameworks/native/include
        -I$AOSP/external/zlib
    )

    ok=0; fl=0; failed=()
    for s in "${AFW_SRCS[@]}"; do
        if [ -f "$AFW/$s" ]; then
            out_o="$AFWD/$(basename $s .cpp).o"
            if compile_file "$AFW/$s" "$out_o" "$CXXF" "${AFW_CFLAGS[*]}"; then
                ok=$((ok+1))
            else
                fl=$((fl+1))
                failed+=("$s")
            fi
        fi
    done
    echo "libandroidfw: $ok ok / $fl fail"
    if [ $fl -gt 0 ]; then
        echo "  failed sources: ${failed[*]}"
    fi

    if [ $fl -eq 0 ] && [ $ok -gt 0 ]; then
        OH_PSDK="${OH_ROOT:-$HOME/oh}/out/rk3568/packages/phone/system/lib/platformsdk"
        if $LNK -Wl,-soname=libandroidfw.so -o "$OUT/libandroidfw.so" $AFWD/*.o \
                -L"$OH_PSDK" \
                -lbase -lutils -lcutils -llog -licuuc -l:libz.so -lziparchive 2>>"$LOG"; then
            sz=$(stat -c%s "$OUT/libandroidfw.so")
            echo "  LINKED: $OUT/libandroidfw.so ($sz bytes)"
        else
            echo "  LINK FAIL — see $LOG" >&2
        fi
    fi
fi

echo ""
echo "============================================================"
echo "  Done. Outputs in $OUT:"
ls -la "$OUT"/lib{ft2,icuuc,icui18n,harfbuzz_ng,minikin,androidfw}.so 2>/dev/null
echo "============================================================"
echo "  Log: $LOG"
