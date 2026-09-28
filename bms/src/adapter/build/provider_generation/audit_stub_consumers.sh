#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
GENERATION_ID=${WESTLAKE_PROVIDER_GENERATION_ID:-provider-inputs-v11}
GENERATION_ROOT="$PROJECT_ROOT/.work/bionic-musl-provider/$GENERATION_ID"
FROZEN="$GENERATION_ROOT/frozen"
PROVIDERS="$GENERATION_ROOT/artifacts/providers"
OUTPUT="$GENERATION_ROOT/evidence/stub-consumers.json"
IMAGE=westlake-oharm64build:local-tools

docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$FROZEN:/inputs:ro" \
    -v "$PROVIDERS:/providers:ro" \
    -v "$SCRIPT_DIR/audit_stub_consumers.py:/audit.py:ro" \
    -v "$GENERATION_ROOT/evidence:/evidence:rw" \
    "$IMAGE" \
    /usr/bin/python3 /audit.py \
        --readelf /inputs/oh/toolchain/bin/llvm-readelf \
        --providers /providers \
        --output /evidence/stub-consumers.json

test -s "$OUTPUT"
