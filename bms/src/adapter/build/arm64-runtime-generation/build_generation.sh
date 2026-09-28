#!/usr/bin/env bash
set -euo pipefail
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
GENERATION_ROOT=${WESTLAKE_ARM64_RUNTIME_ROOT:-$PROJECT_ROOT/.work/arm64-runtime-generation}
FROZEN="$GENERATION_ROOT/frozen"
GENERATION_ID=${WESTLAKE_ARM64_RUNTIME_GENERATION_ID:-arm64-runtime-20260713-r1}
OUTPUT=${WESTLAKE_ARM64_RUNTIME_OUTPUT:-$PROJECT_ROOT/adapter/out/$GENERATION_ID}
IMAGE=westlake-oharm64build:local-tools
EXPECTED_IMAGE=sha256:76236bc11d9359a260c3e715cfee437bed387f76ff86c9ac086c1a52c3536797

[[ -d "$FROZEN" && -f "$GENERATION_ROOT/frozen.sha256" ]] || {
    echo "ERROR: run import_inputs.sh first" >&2
    exit 2
}
case "$OUTPUT" in "$PROJECT_ROOT"/adapter/out/*) ;; *) echo "ERROR: output must be project-local adapter/out" >&2; exit 2 ;; esac
[[ ! -e "$OUTPUT" ]] || { echo "ERROR: refusing output reuse: $OUTPUT" >&2; exit 2; }

(cd "$FROZEN" && shasum -a 256 -c "$GENERATION_ROOT/frozen.sha256" >/dev/null)
ACTUAL_IMAGE=$(docker image inspect "$IMAGE" --format '{{.Id}}')
[[ "$ACTUAL_IMAGE" == "$EXPECTED_IMAGE" ]] || {
    echo "ERROR: locked container image changed: $ACTUAL_IMAGE" >&2
    exit 2
}

mkdir -p "$OUTPUT"
cleanup_on_failure()
{
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        printf 'BUILD_PENDING_OR_FAILED rc=%d\n' "$rc" >"$OUTPUT/BUILD_PENDING"
    fi
}
trap cleanup_on_failure EXIT

docker run --rm --platform linux/amd64 --network none --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,size=2g \
    --mount "type=bind,src=$PROJECT_ROOT,dst=/project,readonly" \
    --mount "type=bind,src=$OUTPUT,dst=/out" \
    --env "WESTLAKE_ARM64_RUNTIME_GENERATION_ID=$GENERATION_ID" \
    "$IMAGE" /bin/bash \
    /project/.work/arm64-runtime-generation/frozen/config/container_build.sh

rm -f "$OUTPUT/BUILD_PENDING"
echo "ARM64_RUNTIME_GENERATION_PASS output=$OUTPUT"
