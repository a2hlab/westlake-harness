#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../../.." && pwd -P)
[[ -n ${WESTLAKE_GENERATION_ROOT:-} ]] || {
    echo "ERROR: WESTLAKE_GENERATION_ROOT must name the exact Fn02 frozen generation" >&2
    exit 1
}
[[ -d "$WESTLAKE_GENERATION_ROOT" ]] || {
    echo "ERROR: WESTLAKE_GENERATION_ROOT is not a directory" >&2
    exit 1
}
HOST_GENERATION_ROOT=$(cd "$WESTLAKE_GENERATION_ROOT" && pwd -P)
# Frozen provider provenance names the historical product closure.  Keep it
# distinct from the isolated current generation selected above.
HOST_LOGICAL_GENERATION_ROOT=$PROJECT_ROOT/.work/product-tls-generation
LOCK=$HOST_GENERATION_ROOT/tool_runtime.lock
IDENTITY_CONTRACT=$SCRIPT_DIR/r45_adapter_identity.env

[[ -f "$IDENTITY_CONTRACT" ]] || {
    echo "ERROR: missing R45 adapter identity contract" >&2
    exit 1
}
set -a
# shellcheck disable=SC1090
source "$IDENTITY_CONTRACT"
set +a
for identity_name in \
    WLAR_ADAPTER_BRIDGE_PATH \
    WLAR_ADAPTER_BRIDGE_SHA256_HEX \
    WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX \
    WLAR_ANDROID_RUNTIME_PATH \
    WLAR_ANDROID_RUNTIME_SHA256_HEX \
    WLAR_ANDROID_RUNTIME_BUILD_ID_HEX
do
    [[ -n ${!identity_name:-} ]] || {
        echo "ERROR: incomplete R45 adapter identity contract: $identity_name" >&2
        exit 1
    }
done

[[ -f "$LOCK" ]] || {
    echo "ERROR: missing project-local frozen tool runtime lock" >&2
    exit 1
}
IMAGE=$(awk -F= '$1 == "image_id" {print $2}' "$LOCK")
[[ -n "$IMAGE" ]] || {
    echo "ERROR: empty locked image identity" >&2
    exit 1
}
ACTUAL=$(docker image inspect "$IMAGE" --format '{{.Id}}')
[[ "$ACTUAL" == "$IMAGE" ]] || {
    echo "ERROR: locked image identity changed" >&2
    exit 1
}

CONTAINER_GENERATION_ROOT=/project/.work/fn02-active-generation
CONTAINER_LOGICAL_GENERATION_ROOT=/.work/product-tls-generation
DOCKER_INPUT_ARGS=(
    -e "WESTLAKE_GENERATION_ROOT=$CONTAINER_GENERATION_ROOT"
    -v "$HOST_GENERATION_ROOT:$CONTAINER_GENERATION_ROOT:ro"
    -v "$HOST_LOGICAL_GENERATION_ROOT:$CONTAINER_LOGICAL_GENERATION_ROOT:ro"
)
if [[ -n ${WESTLAKE_BIONIC_PROVIDER_ORIGIN:-} ]]; then
    CONTAINER_BIONIC_PROVIDER_ROOT=/fn02-bionic-provider
    DOCKER_INPUT_ARGS+=(
        -e "WESTLAKE_BIONIC_PROVIDER_ORIGIN=$CONTAINER_BIONIC_PROVIDER_ROOT"
        -v "$WESTLAKE_BIONIC_PROVIDER_ORIGIN:$CONTAINER_BIONIC_PROVIDER_ROOT:ro"
    )
fi

docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$PROJECT_ROOT:/project:ro" \
    "${DOCKER_INPUT_ARGS[@]}" \
    -w /project \
    "$IMAGE" \
    sh -c '
        set -eu
        test -x "$WESTLAKE_GENERATION_ROOT/frozen/toolchain/bin/clang-15"
        test -f /project/upstream/openharmony-6.1.0.31/third_party/zlib/BUILD.gn
        test -f /project/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/frozen/runtime_provider/libraries/oh/libhilog.so
        test -f /.work/product-tls-generation/frozen/libraries/oh/libhilog.so
        cmp \
            /project/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/frozen/runtime_provider/libraries/oh/libhilog.so \
            /.work/product-tls-generation/frozen/libraries/oh/libhilog.so
        printf "PASS route-A container input preflight generation_root=%s zlib=%s\n" \
            "$WESTLAKE_GENERATION_ROOT" \
            /project/upstream/openharmony-6.1.0.31/third_party/zlib/BUILD.gn
    '

"$SCRIPT_DIR/run_host_tests.sh"

docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -e WLAR_ADAPTER_BRIDGE_PATH \
    -e WLAR_ADAPTER_BRIDGE_SHA256_HEX \
    -e WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX \
    -e WLAR_ANDROID_RUNTIME_PATH \
    -e WLAR_ANDROID_RUNTIME_SHA256_HEX \
    -e WLAR_ANDROID_RUNTIME_BUILD_ID_HEX \
    -v "$PROJECT_ROOT:/project:rw" \
    "${DOCKER_INPUT_ARGS[@]}" \
    -w /project \
    "$IMAGE" \
    /project/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/build_route_a_generation_in_container.sh

echo "PASS route-A final link; all-thread-admission=false product_activation=false device_verified=false"
