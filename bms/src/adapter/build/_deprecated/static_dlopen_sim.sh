#!/bin/bash
# static_dlopen_sim.sh — predict runtime dlopen UND for any .so.
#
# Usage:
#   build/static_dlopen_sim.sh <path/to/target.so>
#
# Output: unresolved GLOBAL + WEAK symbols (grouped), with optional provider
# hint via /tmp/oh_symbol_index.txt if already built. Run
# `build/static_dlopen_sim.sh --build-index` to prebuild the OH symbol index
# (~1.5 min, 525K entries).
#
# Fixes in this version vs raw readelf `$NF`:
#   - awk $8 (not $NF) — UND rows have NF=9 when versioned ("@1.0 (2)" suffix),
#     $NF picks "(2)" instead of name
#   - regex `sub(/@.*$/,"",$8)` — strips @version and @@version suffix, so UND
#     "@1.0" matches DEFINED "@@1.0" after normalization
#
# Exit code: 0 = unresolved count is 0 (all resolvable at runtime), 1 = any
# unresolved GLOBAL.
set -o pipefail

OH=${OH:-/home/HanBingChen/oh}
ADAPTER=${ADAPTER:-/home/HanBingChen/adapter}

if [ "$1" = "--build-index" ]; then
    INDEX=/tmp/oh_symbol_index.txt
    : > $INDEX
    echo "[building OH symbol -> lib index]"
    for d in $OH/out/rk3568/packages/phone/system/lib $OH/out/rk3568/packages/phone/system/lib/platformsdk $OH/out/rk3568/packages/phone/system/lib/ndk $OH/out/rk3568/packages/phone/system/lib/chipset-sdk $OH/out/rk3568/packages/phone/system/lib/chipset-sdk-sp $OH/out/rk3568/thirdparty/skia $ADAPTER/out/aosp_lib $ADAPTER/out/adapter; do
        for so in $d/*.so; do
            [ -f "$so" ] || continue
            n=$(basename "$so")
            readelf -Ws "$so" 2>/dev/null | \
                awk -v n=$n "\$7 != \"UND\" && (\$5 == \"GLOBAL\" || \$5 == \"WEAK\") && (\$4 == \"FUNC\" || \$4 == \"OBJECT\") {sub(/@.*\$/, \"\", \$8); print \$8, n}" >> $INDEX
        done
    done
    sort -u $INDEX -o $INDEX
    echo "  index size: $(wc -l $INDEX | awk "{print \$1}") entries"
    exit 0
fi

LIB="$1"
if [ -z "$LIB" ] || [ ! -f "$LIB" ]; then
    echo "usage: $0 <target.so> | --build-index" >&2
    exit 2
fi

SEARCH_DIRS="$ADAPTER/out/adapter $ADAPTER/out/aosp_lib $ADAPTER/out/skia-rtti-shim $ADAPTER/out/oh-service \
    $OH/out/rk3568/thirdparty/skia \
    $OH/out/rk3568/packages/phone/system/lib \
    $OH/out/rk3568/packages/phone/system/lib/platformsdk \
    $OH/out/rk3568/packages/phone/system/lib/ndk \
    $OH/out/rk3568/packages/phone/system/lib/chipset-sdk \
    $OH/out/rk3568/packages/phone/system/lib/chipset-sdk-sp \
    $OH/out/rk3568/packages/phone/system/lib/module \
    $OH/out/rk3568/obj/third_party/musl/usr/lib/arm-linux-ohos"

NEEDED=$(readelf -d "$LIB" 2>/dev/null | awk -F"[][]" "/\(NEEDED\)/ {print \$2}")
declare -A LP
for lib in $NEEDED; do
    for d in $SEARCH_DIRS; do
        if [ -f "$d/$lib" ]; then LP[$lib]="$d/$lib"; break; fi
    done
done
NRES=${#LP[@]}
NT=$(echo $NEEDED | wc -w)

TMP=/tmp/static_sim_$$
mkdir -p $TMP
: > $TMP/exports.txt
for lib in "${!LP[@]}"; do
    readelf -Ws "${LP[$lib]}" 2>/dev/null | \
        awk "\$7 != \"UND\" && (\$5 == \"GLOBAL\" || \$5 == \"WEAK\") && (\$4 == \"FUNC\" || \$4 == \"OBJECT\") {sub(/@.*\$/, \"\", \$8); print \$8}" >> $TMP/exports.txt
done
sort -u $TMP/exports.txt -o $TMP/exports.txt

readelf -Ws "$LIB" 2>/dev/null | awk "\$7 == \"UND\" && \$5 == \"GLOBAL\" {sub(/@.*\$/, \"\", \$8); print \$8}" | sort -u > $TMP/und.txt
readelf -Ws "$LIB" 2>/dev/null | awk "\$7 == \"UND\" && \$5 == \"WEAK\" {sub(/@.*\$/, \"\", \$8); print \$8}" | sort -u > $TMP/und_weak.txt

comm -23 $TMP/und.txt $TMP/exports.txt > $TMP/unres.txt
comm -23 $TMP/und_weak.txt $TMP/exports.txt > $TMP/unres_weak.txt

echo "=== $(basename $LIB) static dlopen sim ==="
echo "  DT_NEEDED resolved: $NRES / $NT"
echo "  GLOBAL UND total:   $(wc -l <$TMP/und.txt)"
echo "  WEAK   UND total:   $(wc -l <$TMP/und_weak.txt)"
echo
NU=$(wc -l <$TMP/unres.txt)
NW=$(wc -l <$TMP/unres_weak.txt)
echo "=== GLOBAL unresolved: $NU (hard-fail at dlopen) ==="
cat $TMP/unres.txt
echo
echo "=== WEAK unresolved: $NW (soft, null call may SEGV) ==="
cat $TMP/unres_weak.txt

if [ -f /tmp/oh_symbol_index.txt ] && [ $NU -gt 0 ]; then
    echo
    echo "=== provider hint (--build-index must have been run) ==="
    while read sym; do
        prov=$(awk -v s="$sym" "\$1 == s {print \$2}" /tmp/oh_symbol_index.txt | sort -u | paste -sd ", ")
        [ -z "$prov" ] && prov="(none in OH .so set)"
        printf "  %-80s %s\n" "$sym" "$prov"
    done < $TMP/unres.txt
fi

rm -rf $TMP
[ $NU -eq 0 ]
