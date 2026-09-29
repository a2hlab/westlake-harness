#!/bin/bash
# hw248 build driver for #25 — runs inside /opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve
# Fix 1: SRCS existence check with a hyphen-safe pattern.
# Fix 2: stage hw248's real .so locations into the layout compile_apk_installer.sh expects
#        (the shared OH tree is read-only; staging lives under our build-run dir only).
set -uo pipefail
R=/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve
A=$R/full-src/src/adapter
OH=/opt/build-trees/oh610_lts_source
OH_OUT=$OH/out/wukong100

echo "--- 1. SRCS existence (hyphen-safe) ---"
miss=0
grep -o '\$ADAPTER/[a-zA-Z0-9_/.-]*\.cpp' "$A/build/inner/compile_apk_installer.sh" | while read -r rel; do
  f="$A/${rel#\$ADAPTER/}"
  [ -f "$f" ] || echo "MISS $rel"
done | tee /tmp/srcs_miss.txt
[ -s /tmp/srcs_miss.txt ] && { echo "SRCS incomplete"; exit 1; }
echo "all SRCS present"

echo "--- 2. stage syslib layout ---"
ST=$R/stage
rm -rf "$ST"; mkdir -p "$ST/lib64/platformsdk" "$ST/sdksp"
ln -sf $OH_OUT/obj/third_party/musl/usr/lib/aarch64-linux-ohos/libc.so      "$ST/lib64/libc.so"
ln -sf $OH_OUT/obj/third_party/musl/usr/lib/aarch64-linux-ohos/libdl.so     "$ST/lib64/libdl.so" 2>/dev/null || true
ln -sf $OH/out/sdk/obj/interface/sdk_c/third_party/zlib/ohos_clang_arm64/libz.so "$ST/lib64/libz.so"
ln -sf $OH/out/sdk/commonlibrary/c_utils/libutils.z.so                      "$ST/lib64/libutils.z.so"
ln -sf $OH/out/sdk/hiviewdfx/hilog/libhilog.so                              "$ST/lib64/platformsdk/libhilog.so"
ln -sf $OH_OUT/thirdparty/openssl/libcrypto_openssl.z.so                    "$ST/lib64/libcrypto_openssl.z.so"
ln -sf $OH_OUT/thirdparty/openssl/libssl_openssl.z.so                       "$ST/lib64/libssl_openssl.z.so"
/bin/ls -l "$ST/lib64" | tail -n +2

echo "--- 3. patch MY copy of compile_apk_installer.sh to use the stage layout ---"
S=$A/build/inner/compile_apk_installer.sh
if ! grep -q "LABEL-RESOLVE hw248 stage" "$S"; then
  # insert override right after the SDK_SP assignment inside the link section
  perl -0pi -e 's{(SYS_SP="?\$OH_OUT/packages/phone/system/lib/chipset-sdk-sp"?\n)}{$1# LABEL-RESOLVE hw248 stage: shared OH tree has no packages/phone layout; use staged symlinks\nSYS_LIB=\$ST/lib64; SYS_LIB_SDK=\$SYS_LIB/platformsdk; SDK_SP=\$ST/sdksp\n}' "$S"
  perl -0pi -e 's{(ST=\$R/stage\n)}{}g' "$S"
  # define ST near the top (after OH_OUT resolution)
  perl -0pi -e 's{(else echo "ERROR: OH output dir not found[^\n]*\n)}{$1ST=/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve/stage\n}' "$S"
  grep -q 'ST=/opt/build-runs' "$S" || sed -i '3i ST=/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve/stage' "$S"
fi
grep -n "LABEL-RESOLVE hw248 stage\|^ST=" "$S" | head -3

echo "--- 4. build ---"
cd "$A"
BUILD_INNER_INVOKED=1 OH_ROOT=$OH ADAPTER_ROOT=$A \
  APK_INSTALLER_BUILD_TMP=$R/tmp-apk-installer \
  bash build/inner/compile_apk_installer.sh 2>&1 | tail -25

echo "--- 5. verify ---"
SO=$A/out/adapter/libapk_installer.so
if [ -f "$SO" ]; then
  sha256sum "$SO"
  strings "$SO" | grep -c "ResolveApkLabel\|ResolveLabelResId" || true
  llvm-nm -D "$SO" 2>/dev/null | grep -c "ResolveApkLabel" || true
else
  echo "NO OUTPUT SO"
fi
