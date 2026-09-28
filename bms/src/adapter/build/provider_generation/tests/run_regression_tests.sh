#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PRODUCER_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
PROJECT_ROOT=$(cd "$PRODUCER_ROOT/../../.." && pwd -P)
GENERATION_ID=${WESTLAKE_PROVIDER_GENERATION_ID:-provider-inputs-v11}
GENERATION_ROOT="$PROJECT_ROOT/.work/bionic-musl-provider/$GENERATION_ID"
FROZEN="$GENERATION_ROOT/frozen"
PRIMARY="$GENERATION_ROOT/artifacts"
REPRO="$GENERATION_ROOT/artifacts-repro"
NEGATIVE="$GENERATION_ROOT/work-verifier-negative"
IMAGE=westlake-oharm64build:local-tools

bash -n "$PRODUCER_ROOT/import_inputs.sh" \
    "$PRODUCER_ROOT/container_build.sh" \
    "$PRODUCER_ROOT/build_generation.sh" \
    "$PRODUCER_ROOT/verify_generation.sh"
PYTHONPYCACHEPREFIX="$GENERATION_ROOT/work-regression-pycache" \
    python3 -m py_compile "$PRODUCER_ROOT/verify_generation.py" "$SCRIPT_DIR/mutate_elf.py"

test "$(wc -l <"$PRIMARY/providers.sha256" | tr -d ' ')" = 24
cmp -s "$PRIMARY/providers.sha256" "$REPRO/providers.sha256"
test "$(shasum -a 256 "$PRIMARY/providers.sha256" | awk '{print $1}')" = \
    12eb3fbb604e6f808624e1b3f59f850e09e88fd6bbe177fc08442653332522ee

WESTLAKE_PROVIDER_GENERATION_ID="$GENERATION_ID" \
    "$PRODUCER_ROOT/verify_generation.sh"

python3 - "$GENERATION_ROOT/evidence/verification.json" <<'PY'
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["status"] == "ARTIFACT_VERIFIED_NOT_PRODUCT_ACTIVATED"
assert result["provider_count"] == 24
assert result["byte_deterministic_runs"] == 2
assert result["unique_soname_count"] == 24
assert result["build_id_complete"] is True
assert result["product_activation"] is False
assert result["device_verified"] is False
assert result["error_code_string_owner"] == "libziparchive.so"
PY

# Determinism negative: mutate a copied repro artifact and require the same
# verifier to reject it.  Frozen inputs and both canonical artifact roots are
# read-only to this test.
if [[ -e "$NEGATIVE" ]]; then
    rm -rf -- "$NEGATIVE"
fi
mkdir -p "$NEGATIVE"
cp -R "$REPRO/." "$NEGATIVE/"
python3 "$SCRIPT_DIR/mutate_elf.py" "$NEGATIVE/providers/libbase.so" >/dev/null

set +e
docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$FROZEN:/inputs:ro" \
    -v "$PRIMARY:/primary:ro" \
    -v "$NEGATIVE:/repro:ro" \
    -v "$PRODUCER_ROOT/verify_generation.py:/verify_generation.py:ro" \
    "$IMAGE" \
    /usr/bin/python3 /verify_generation.py \
        --readelf /inputs/oh/toolchain/bin/llvm-readelf \
        --primary /primary \
        --repro /repro \
        --output /tmp/forbidden.json \
        >"$GENERATION_ROOT/evidence/negative.stdout" \
        2>"$GENERATION_ROOT/evidence/negative.stderr"
negative_rc=$?
set -e
test "$negative_rc" -ne 0
grep -q 'not byte deterministic' "$GENERATION_ROOT/evidence/negative.stderr"

echo "PASS provider_generation_regression providers=24 deterministic=2 mutant_rejected=1 product_activation=false"
