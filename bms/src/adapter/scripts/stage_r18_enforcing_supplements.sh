#!/bin/bash
# Stage the two libraries that the Enforcing appspawn-x now needs into the
# r18 generation output and refresh MANIFEST.sha256.  This makes the
# generation-to-deployment path repeatable without hand-copying from AlexPC.

set -euo pipefail
IFS=$'\n\t'
umask 022

ADAPTER=/opt/Bridge/src/adapter
GEN=$ADAPTER/out/helloworld-r18-v7-ams-parent-bound-subwindow-art64-20260725T0050HKT
LIB64=$GEN/systemandroid/lib64
OH=/opt/10.Project/16-WestLake/16.12-HanBing/oh
IMAGE=westlake-local-build:oh61-api23

STAMP=$(date +%Y%m%dT%H%M%S)
REGISTRY_BUILD=$ADAPTER/out/.work/registry-build-$STAMP
REGISTRY_OBJ=$ADAPTER/out/.work/registry-obj-$STAMP

mkdir -p "$REGISTRY_BUILD" "$REGISTRY_OBJ" "$LIB64"

echo "[stage] building libwestlake_thread_guard_registry.so from adapter source..."
docker run --rm --platform linux/amd64 \
    -v /mnt/mac/opt:/mnt/mac/opt \
    -e ADAPTER_ROOT=/mnt/mac/opt/Bridge/src/adapter \
    -e ADAPTER_OUT_DIR=/mnt/mac"$REGISTRY_BUILD" \
    -e WLTG_OBJ_DIR=/mnt/mac"$REGISTRY_OBJ" \
    -e OH_SYSROOT=/mnt/mac/opt/10.Project/16-WestLake/16.12-HanBing/oh/out/wukong100/obj/third_party/musl/usr \
    -e L03_A12_CC=/mnt/mac/opt/10.Project/16-WestLake/16.12-HanBing/oh/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang \
    -e L03_A12_READELF=/mnt/mac/opt/10.Project/16-WestLake/16.12-HanBing/oh/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf \
    -e L03_A12_OBJDUMP=/mnt/mac/opt/10.Project/16-WestLake/16.12-HanBing/oh/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-objdump \
    "$IMAGE" \
    bash /mnt/mac/opt/Bridge/src/adapter/framework/native-compat/thread-guard-registry/build_arm64.sh

cp -p "$REGISTRY_BUILD/libwestlake_thread_guard_registry.so" "$LIB64/"

echo "[stage] copying liblzma.so from OH aarch64 toolchain prebuilt..."
cp -p "$OH/prebuilts/clang/ohos/ohos-arm64/llvm/lib/liblzma.so" "$LIB64/"

echo "[stage] refreshing MANIFEST.sha256..."
(
    cd "$GEN"
    find . -type f ! -name MANIFEST.sha256 -print0 | \
        sort -z | xargs -0 shasum -a 256 > MANIFEST.sha256
)

echo ""
echo "STAGE_OK"
/usr/bin/shasum -a 256 \
    "$LIB64/libwestlake_thread_guard_registry.so" \
    "$LIB64/liblzma.so"
