#!/bin/bash
# full_rebuild_libbms.sh — Path B finisher for Gap 6.
#
# Sequence:
#   1. Backup current build.ninja (the 11-line manual stub) so we can roll
#      back if something goes wrong.
#   2. Run `gn gen out/rk3568` to regenerate the full ninja tree from the
#      patched BUILD.gn (which now lists adapter_apk_install_minimal.cpp +
#      apk_manifest_parser.cpp + OH_ADAPTER_ANDROID).
#   3. Apply ninja_patches/apply_all.sh to re-establish the irtoc / arkruntime
#      / ani_helpers phony hooks (because gn gen overwrites them).
#   4. Run `ninja bundlemanager/bundle_framework/libbms.z.so` to actually
#      compile libbms with the adapter sources.
#   5. Verify the resulting libbms.z.so exports ProcessApkInstall.
#
# This script assumes:
#   - OH_ROOT defaults to ~/oh
#   - OH product is rk3568
#   - The ohos_patches/bundle_framework/services/bundlemgr/BUILD.gn.patch is
#     already applied to the OH source tree (it is, per Gap 6 audit)
#   - The replacement std::div patches in
#     ohos_patches/third_party/skia/.../{decimfmt,number_decimalquantity}.cpp.patch
#     are already applied (they are, per earlier session)
set -e

OH_ROOT="${OH_ROOT:-$HOME/oh}"
PROD="${OH_PRODUCT_NAME:-rk3568}"
ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
OUT=$OH_ROOT/out/$PROD

GN=$OH_ROOT/prebuilts/build-tools/linux-x86/bin/gn
NINJA=$OH_ROOT/prebuilts/build-tools/linux-x86/bin/ninja
NM=$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm

SAFETY_TAG="full_rebuild_libbms_$(date +%Y%m%d_%H%M%S)"

# ---------------------------------------------------------------------------
# Step 1: backup
# ---------------------------------------------------------------------------
echo '[1/5] Backup current build.ninja'
cp -v $OUT/build.ninja $OUT/build.ninja.${SAFETY_TAG}
echo

# ---------------------------------------------------------------------------
# Step 2: gn gen — regenerate ninja files from BUILD.gn (which has the patch)
# ---------------------------------------------------------------------------
echo '[2/5] gn gen out/'$PROD' (regenerating ninja files from patched BUILD.gn)'
cd $OH_ROOT
$GN --root=. gen out/$PROD 2>&1 | tail -5
echo

# Verify libbms.ninja was regenerated and now contains adapter sources
LIBBMS_NINJA=$OUT/obj/foundation/bundlemanager/bundle_framework/services/bundlemgr/libbms.ninja
if grep -q "adapter_apk_install_minimal" "$LIBBMS_NINJA" 2>/dev/null; then
    echo '[2/5] OK libbms.ninja now references adapter_apk_install_minimal.cpp'
else
    echo '[2/5] WARN libbms.ninja does NOT reference adapter_apk_install_minimal.cpp — BUILD.gn patch may not be applied'
    echo "      file: $LIBBMS_NINJA"
fi
echo

# ---------------------------------------------------------------------------
# Step 3: re-apply ninja phony patches (irtoc / arkruntime / ani_helpers)
# ---------------------------------------------------------------------------
echo '[3/5] Re-apply ninja phony patches'
bash $ADAPTER_ROOT/ohos_patches/ninja_patches/apply_all.sh
echo

# ---------------------------------------------------------------------------
# Step 4: ninja build for libbms
# ---------------------------------------------------------------------------
echo '[4/5] ninja bundlemanager/bundle_framework/libbms.z.so'
cd $OH_ROOT
$NINJA -C out/$PROD -w dupbuild=warn -j16 bundlemanager/bundle_framework/libbms.z.so 2>&1 | tail -20
echo

# ---------------------------------------------------------------------------
# Step 5: verify
# ---------------------------------------------------------------------------
echo '[5/5] Verify libbms.z.so contains ProcessApkInstall'
LIB_OUT=$OUT/lib.unstripped/bundlemanager/bundle_framework/libbms.z.so
if [ -f "$LIB_OUT" ]; then
    SIZE=$(stat -c%s "$LIB_OUT")
    echo "  size: $SIZE bytes"
    SYMS=$($NM -C "$LIB_OUT" 2>/dev/null | grep -cE "ProcessApkInstall|ApkManifestParser|adapter_apk_install" || true)
    echo "  ProcessApkInstall / ApkManifestParser symbols: $SYMS"
    if [ "$SYMS" -gt 0 ]; then
        echo '  OK Gap 6 runtime-level integration complete'
    else
        echo '  WARN libbms built but adapter symbols not found'
    fi
else
    echo "  FAIL $LIB_OUT not produced"
    exit 1
fi
