#!/bin/bash
# iterate_libbms.sh — fast iteration loop for libbms gap 6 build.
#
# Mirrors what restore_after_sync.sh does for the gap-6-related phases:
#   B8: apply BUILD.gn semantic patch (apply_BUILD_gn.py)
#   B9: apply ets2abc_config.gni collision fix (sed-based, idempotent)
#   B10: deploy adapter_apk_install_minimal.cpp + apk_manifest_parser.{h,cpp}
#        from canonical adapter sources into bundlemgr/src/
# Then: gn gen → ninja_patches/apply_all.sh → ninja libbms.z.so
#
# Idempotent: re-running on a clean state is a no-op for the patches.
set -e

OH_ROOT=/home/HanBingChen/oh
PROD=rk3568
ADAPTER=/home/HanBingChen/adapter
AOSP_ROOT=/home/HanBingChen/aosp

GN=$OH_ROOT/prebuilts/build-tools/linux-x86/bin/gn
NINJA=$OH_ROOT/prebuilts/build-tools/linux-x86/bin/ninja

cd $OH_ROOT

# ---- B8: BUILD.gn diff patch (2026-05-20: was apply_BUILD_gn.py) ----
echo "[iter] B8: bundle_framework/services/bundlemgr/BUILD.gn.patch"
BMS_BUILD_PATCH=$ADAPTER/ohos_patches/foundation/bundlemanager/bundle_framework/services/bundlemgr/BUILD.gn.patch
if patch -R --dry-run -p1 -d $OH_ROOT < $BMS_BUILD_PATCH >/dev/null 2>&1; then
    echo "  already applied"
elif patch --dry-run -p1 -d $OH_ROOT < $BMS_BUILD_PATCH >/dev/null 2>&1; then
    patch -p1 -d $OH_ROOT < $BMS_BUILD_PATCH >/dev/null && echo "  ok"
else
    echo "  WARN: BUILD.gn.patch neither forward nor reverse applies"
fi

# ---- B9: ets2abc collision fix ----
echo "[iter] B9: ets2abc_config.gni collision fix"
ETS2ABC=$OH_ROOT/build/config/components/ets_frontend/ets2abc_config.gni
ETS2ABC_PATCH=$ADAPTER/ohos_patches/build/config/components/ets_frontend/ets2abc_config.gni.collision_fix.patch
if grep -q '^ohos_ets_api_deps = ""' $ETS2ABC; then
    patch -p1 -d $OH_ROOT < $ETS2ABC_PATCH > /dev/null && echo "  ok"
else
    echo "  already applied"
fi

# ---- B10: deploy adapter source files into bundlemgr/src/ ----
echo "[iter] B10: deploy adapter sources"
BMS_SRC=$OH_ROOT/foundation/bundlemanager/bundle_framework/services/bundlemgr/src
cp $ADAPTER/framework/package-manager/jni/apk_manifest_parser.h    $BMS_SRC/apk_manifest_parser.h
cp $ADAPTER/framework/package-manager/jni/apk_manifest_parser.cpp  $BMS_SRC/apk_manifest_parser.cpp
cp $ADAPTER/ohos_patches/bundle_framework/services/bundlemgr/src/adapter_apk_install_minimal.cpp $BMS_SRC/adapter_apk_install_minimal.cpp
echo "  3 files deployed"

# ---- gn gen ----
echo "[iter] gn gen..."
$GN --root=. gen out/$PROD 2>&1 | grep -E "^ERROR" | head -5 || true

# ---- ninja phony patches ----
echo "[iter] apply ninja phony patches..."
bash $ADAPTER/build/ninja_patches/apply_all.sh > /tmp/apply.log 2>&1 && tail -1 /tmp/apply.log

# ---- ninja libbms ----
echo "[iter] ninja libbms..."
set +e
$NINJA -C out/$PROD -w dupbuild=warn -j16 bundlemanager/bundle_framework/libbms.z.so > /tmp/ninja_full.log 2>&1
RC=$?
set -e
echo "[iter] ninja exit: $RC"
grep -nE "FAILED:|fatal error|error: " /tmp/ninja_full.log | head -10 || true
echo
ls -la $OH_ROOT/out/$PROD/lib.unstripped/bundlemanager/bundle_framework/libbms.z.so 2>&1 | tail -1
exit $RC
