set -e
TOOL=/home/dspfac/a2hlab/source-closure/verify/out/host-tools/host/objects/bin/dex2oat
B=/private/tmp/claude-501/-Users-zhaoyue-orca-workspaces-westlake-harness/1ff6919c-26aa-4c66-b437-84a6c81b7f06/scratchpad/fxwork/build
NAMES="core-oj core-libart core-icu4j conscrypt okhttp bouncycastle apache-xml framework adapter-runtime-bcp"
FILES=""; LOCS=""
for n in $NAMES; do FILES="${FILES:+$FILES:}$B/fw/$n.jar"; LOCS="${LOCS:+$LOCS:}/system/framework/$n.jar"; done
CMD="$TOOL --runtime-arg -Xbootclasspath:$FILES --runtime-arg -Xbootclasspath-locations:$LOCS"
for n in $NAMES; do CMD="$CMD --dex-file=$B/fw/$n.jar --dex-location=/system/framework/$n.jar"; done
CMD="$CMD --instruction-set=arm64 --compiler-filter=verify --base=0x70000000 --image=$B/boot/boot.art --oat-file=$B/boot/boot.oat --oat-location=/system/framework/arm64/boot.oat --android-root=$B/boot --runtime-arg -Xms64m --runtime-arg -Xmx768m -j4"
rm -f $B/boot/*
LD_PRELOAD=/home/zhaoyue/a2hlab/tools/libmap32bit.so $CMD > $B/boot-image.log 2>&1 && echo DEX2OAT_OK || { echo DEX2OAT_FAIL; tail -20 $B/boot-image.log; exit 1; }
echo "== boot files =="; ls $B/boot/ | wc -l; ls $B/boot/ | head
