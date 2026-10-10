#!/bin/bash
set -euo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
readonly ADAPTER_HOST="${REPO_ROOT}/src/adapter/sources/oh61-v7-b2133b5b"
readonly ADAPTER_CONTAINER="/mnt/mac${ADAPTER_HOST}"
readonly YUE_HOST="/opt/10.Project/16-WestLake/16.13-Yue/local-arm64-build"
readonly YUE_CONTAINER="/mnt/mac${YUE_HOST}"
readonly DEVICE_HEADER_MIRROR_CONTAINER="${YUE_CONTAINER}/oh61-wukong100/adapter/local_oh_headers/oh_mirror"
readonly AOSP_LIB_CONTAINER="${YUE_CONTAINER}/oh61-wukong100/adapter/out/aosp_lib"
readonly IMAGE="westlake-local-build:oh61-api23"
readonly CLEAN_ARG="${CLEAN_ARG:-}"

test -d "$ADAPTER_HOST/framework"
test -d "$ADAPTER_HOST/local_oh_headers/oh_mirror"
test -d "$YUE_HOST/oh61-wukong100"
test -d "$YUE_HOST/aosp-arm64-d600"

docker run --rm --platform linux/amd64 \
  -v /mnt/mac/opt:/mnt/mac/opt \
  -v "/mnt/mac${YUE_HOST}/oh61-wukong100:/data/oh61-wukong100" \
  -v "/mnt/mac${YUE_HOST}/aosp-arm64-d600:/data/aosp-arm64-d600" \
  "$IMAGE" \
  bash -lc "
    set -e
    cd '${ADAPTER_CONTAINER}/build/inner'
    ADAPTER_ROOT='${ADAPTER_CONTAINER}' \
    AOSP_ROOT=/data/aosp-arm64-d600 \
    OH_ROOT=/data/oh61-wukong100 \
    DEVICE_HEADER_MIRROR='${DEVICE_HEADER_MIRROR_CONTAINER}' \
    AOSP_LIB_DIR='${AOSP_LIB_CONTAINER}' \
    BUILD_INNER_INVOKED=1 \
    BRIDGE_JOBS=\$(nproc) \
      bash compile_oh_adapter_bridge_arm64.sh '${CLEAN_ARG}'
  "

readonly SO="$ADAPTER_HOST/out/adapter/liboh_adapter_bridge.so"
file "$SO"
shasum -a 256 "$SO"
