#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
MODULE=$(cd "$SCRIPT_DIR/.." && pwd -P)
PROJECT_ROOT=$(cd "$MODULE/../../.." && pwd -P)
LOCK=$PROJECT_ROOT/.work/product-tls-generation/tool_runtime.lock

"$SCRIPT_DIR/run_host_tests.sh"

[[ -f "$LOCK" ]] || {
    echo "ERROR: missing project-local frozen tool runtime lock: $LOCK" >&2
    exit 1
}
IMAGE=$(awk -F= '$1 == "image_id" {print $2}' "$LOCK")
[[ -n "$IMAGE" ]] || { echo "ERROR: empty locked image id" >&2; exit 1; }
ACTUAL=$(docker image inspect "$IMAGE" --format '{{.Id}}')
[[ "$ACTUAL" == "$IMAGE" ]] || {
    echo "ERROR: locked container image identity changed" >&2
    exit 1
}

mkdir -p "$MODULE/out/target/tmp"
docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$PROJECT_ROOT:/project:rw" \
    -w /project \
    "$IMAGE" \
    /project/adapter/framework/native-compat/tests/build_target_in_container.sh

echo "PASS native-compat audit-only gate; device_verified=false"
