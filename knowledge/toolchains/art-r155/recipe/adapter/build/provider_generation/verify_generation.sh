#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
GENERATION_ID=${WESTLAKE_PROVIDER_GENERATION_ID:-provider-inputs-v11}
GENERATION_ROOT=${WESTLAKE_PROVIDER_GENERATION_ROOT:-$PROJECT_ROOT/.work/bionic-musl-provider/$GENERATION_ID}
FROZEN="$GENERATION_ROOT/frozen"
PRIMARY="$GENERATION_ROOT/artifacts"
REPRO="$GENERATION_ROOT/artifacts-repro"
OUTPUT="$GENERATION_ROOT/evidence/verification.json"
POLICY=${WESTLAKE_PROVIDER_POLICY:-legacy-v11}

for required in "$FROZEN" "$PRIMARY/providers" "$REPRO/providers" "$SCRIPT_DIR/verify_generation.py"; do
    [[ -e "$required" && ! -L "$required" ]] || {
        echo "ERROR: missing verification input: $required" >&2
        exit 1
    }
done

IMAGE=westlake-oharm64build:local-tools
docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$FROZEN:/inputs:ro" \
    -v "$PRIMARY:/primary:ro" \
    -v "$REPRO:/repro:ro" \
    -v "$SCRIPT_DIR/verify_generation.py:/verify_generation.py:ro" \
    -v "$GENERATION_ROOT/evidence:/evidence:rw" \
    "$IMAGE" \
    /usr/bin/python3 /verify_generation.py \
        --readelf /inputs/oh/toolchain/bin/llvm-readelf \
        --primary /primary \
        --repro /repro \
        --policy "$POLICY" \
        --output /evidence/verification.json

test -s "$OUTPUT"
