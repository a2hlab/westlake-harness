#!/usr/bin/env bash
# Build one Fn01.A04 target artifact without deploying it.

set -euo pipefail
IFS=$'\n\t'
umask 022

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd -P)
IMAGE=westlake-local-build:oh61-api23
YUE_HOST=/opt/10.Project/16-WestLake/16.13-Yue/local-arm64-build
ADAPTER_HOST="$ROOT/src/adapter"
ADAPTER_CONTAINER="/mnt/mac$ADAPTER_HOST"
YUE_CONTAINER="/mnt/mac$YUE_HOST"
JAVA_STAGE="$ROOT/.work/fn01-a04-provenance-candidate"

case "${1:-}" in
    bridge)
        "$ADAPTER_HOST/scripts/build_oh61_v7_bridge_r8_arm64.sh"
        ;;
    installer)
        test -d "$YUE_HOST/oh61-wukong100"
        test -d "$YUE_HOST/aosp-arm64-d600"
        docker run --rm --platform linux/amd64 \
            -v /mnt/mac/opt:/mnt/mac/opt \
            -v "$YUE_CONTAINER/oh61-wukong100:/data/oh61-wukong100" \
            -v "$YUE_CONTAINER/aosp-arm64-d600:/data/aosp-arm64-d600" \
            "$IMAGE" \
            bash -lc "
                set -e
                cd '$ADAPTER_CONTAINER/build'
                ADAPTER_ROOT='$ADAPTER_CONTAINER' \
                AOSP_ROOT=/data/aosp-arm64-d600 \
                OH_ROOT=/data/oh61-wukong100 \
                BUILD_INNER_INVOKED=1 \
                    bash inner/compile_apk_installer.sh
            "
        file "$ADAPTER_HOST/out/adapter/libapk_installer.so"
        shasum -a 256 "$ADAPTER_HOST/out/adapter/libapk_installer.so"
        ;;
    java)
        local_pm="$ADAPTER_HOST/framework/package-manager/java"
        local_adapter_sha=$(shasum -a 256 "$local_pm/PackageManagerAdapter.java" | awk '{print $1}')
        local_builder_sha=$(shasum -a 256 "$local_pm/PackageInfoBuilder.java" | awk '{print $1}')
        remote_root=/opt/build-trees/aosp-arm64-d600
        remote_pm="$remote_root/device/adapter/oh_adapter_framework/java/adapter/packagemanager"
        remote_work=/opt/build-trees/.work/fn01-a04-provenance-preflight-r1
        remote_out="$remote_work/out/aosp-graph"
        remote_cache="$remote_work/cache/ccache"
        remote_check=$(ssh AlexPC "
            set -e
            sha256sum \
              '$remote_pm/PackageManagerAdapter.java' \
              '$remote_pm/PackageInfoBuilder.java'
        ")
        printf '%s\n' "$remote_check"
        printf '%s\n' "$remote_check" | grep -q "^$local_adapter_sha  $remote_pm/PackageManagerAdapter.java$"
        printf '%s\n' "$remote_check" | grep -q "^$local_builder_sha  $remote_pm/PackageInfoBuilder.java$"

        ssh AlexPC "
            set -e
            cd '$remote_root'
            export BUILD_BROKEN_DISABLE_BAZEL=true
            export OUT_DIR='$remote_out'
            export CCACHE_DIR='$remote_cache'
            export USE_CCACHE=1
            . build/envsetup.sh >/dev/null
            lunch oh_adapter-eng >/dev/null
            m oh-adapter-framework -j8
            sha256sum \
              '$remote_pm/PackageManagerAdapter.java' \
              '$remote_pm/PackageInfoBuilder.java' \
              '$remote_out/target/product/generic_arm64/system/framework/oh-adapter-framework.jar'
        "
        mkdir -p "$JAVA_STAGE"
        scp \
            "AlexPC:$remote_out/target/product/generic_arm64/system/framework/oh-adapter-framework.jar" \
            "$JAVA_STAGE/oh-adapter-framework.jar"
        file "$JAVA_STAGE/oh-adapter-framework.jar"
        shasum -a 256 "$JAVA_STAGE/oh-adapter-framework.jar"
        ;;
    *)
        echo "usage: $0 bridge|installer|java" >&2
        exit 2
        ;;
esac

printf 'BUILD_PASS=true\n'
printf 'DEPLOYED=false\n'
printf 'DEVICE_VERIFIED=false\n'
printf 'FORMAL_VERDICT=NOT_ISSUED\n'
