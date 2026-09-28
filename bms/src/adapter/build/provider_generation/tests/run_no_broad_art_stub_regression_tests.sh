#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PRODUCER_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
PROJECT_ROOT=$(cd "$PRODUCER_ROOT/../../.." && pwd -P)
GENERATION_ID=${WESTLAKE_PROVIDER_GENERATION_ID:-provider-inputs-v12-nobroadstub}
GENERATION_ROOT="$PROJECT_ROOT/.work/bionic-musl-provider/$GENERATION_ID"
FROZEN="$GENERATION_ROOT/frozen"
PRIMARY="$GENERATION_ROOT/artifacts"
REPRO="$GENERATION_ROOT/artifacts-repro"
NEGATIVE_ROOT="$GENERATION_ROOT/work-no-broad-stub-negative"
IMAGE=westlake-oharm64build:local-tools

bash -n "$PRODUCER_ROOT/import_inputs.sh" \
    "$PRODUCER_ROOT/container_build.sh" \
    "$PRODUCER_ROOT/build_generation.sh" \
    "$PRODUCER_ROOT/verify_generation.sh"
PYTHONPYCACHEPREFIX="$GENERATION_ROOT/work-regression-pycache" \
    python3 -m py_compile \
        "$PRODUCER_ROOT/verify_generation.py" \
        "$SCRIPT_DIR/mutate_elf.py" \
        "$SCRIPT_DIR/mutate_symbol_name.py"

test "$(wc -l <"$PRIMARY/providers.sha256" | tr -d ' ')" = 23
cmp -s "$PRIMARY/providers.sha256" "$REPRO/providers.sha256"
test "$(shasum -a 256 "$PRIMARY/providers.sha256" | awk '{print $1}')" = \
    3177745fafb7b4cc9f49c1c535a11de0c79bbec51b4a7cee6f42ee2386425752
test ! -e "$PRIMARY/providers/libart_runtime_stubs.so"
test ! -e "$REPRO/providers/libart_runtime_stubs.so"

WESTLAKE_PROVIDER_GENERATION_ID="$GENERATION_ID" \
WESTLAKE_PROVIDER_POLICY=no-broad-art-stub-v1 \
    "$PRODUCER_ROOT/verify_generation.sh"

python3 - "$GENERATION_ROOT/evidence/verification.json" <<'PY'
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["status"] == "ARTIFACT_VERIFIED_NOT_PRODUCT_ACTIVATED"
assert result["policy"] == "no-broad-art-stub-v1"
assert result["provider_count"] == 23
assert result["byte_deterministic_runs"] == 2
assert result["unique_soname_count"] == 23
assert result["broad_art_runtime_stub_absent"] is True
assert result["broad_art_runtime_stub_consumers"] == []
assert result["product_activation"] is False
assert result["device_verified"] is False
PY

# Determinism mutant: one changed provider in the copied repro must be rejected.
rm -rf -- "$NEGATIVE_ROOT"
mkdir -p "$NEGATIVE_ROOT/determinism"
cp -R "$REPRO/." "$NEGATIVE_ROOT/determinism/"
python3 "$SCRIPT_DIR/mutate_elf.py" \
    "$NEGATIVE_ROOT/determinism/providers/libbase.so" >/dev/null
set +e
docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$FROZEN:/inputs:ro" \
    -v "$PRIMARY:/primary:ro" \
    -v "$NEGATIVE_ROOT/determinism:/repro:ro" \
    -v "$PRODUCER_ROOT/verify_generation.py:/verify_generation.py:ro" \
    "$IMAGE" \
    /usr/bin/python3 /verify_generation.py \
        --readelf /inputs/oh/toolchain/bin/llvm-readelf \
        --primary /primary \
        --repro /repro \
        --policy no-broad-art-stub-v1 \
        --output /tmp/forbidden.json \
        >"$NEGATIVE_ROOT/determinism.stdout" \
        2>"$NEGATIVE_ROOT/determinism.stderr"
determinism_rc=$?
set -e
test "$determinism_rc" -ne 0
grep -q 'not byte deterministic' "$NEGATIVE_ROOT/determinism.stderr"

# Real-owner mutant: make both runs byte-identical after removing the exact
# Palette client symbol. This bypasses the determinism gate and must be killed
# by the typed-owner contract itself.
mkdir -p "$NEGATIVE_ROOT/owner-primary" "$NEGATIVE_ROOT/owner-repro"
cp -R "$PRIMARY/." "$NEGATIVE_ROOT/owner-primary/"
cp -R "$REPRO/." "$NEGATIVE_ROOT/owner-repro/"
for root in "$NEGATIVE_ROOT/owner-primary" "$NEGATIVE_ROOT/owner-repro"; do
    python3 "$SCRIPT_DIR/mutate_symbol_name.py" \
        "$root/providers/libartpalette.so" \
        PaletteTraceBegin PaletteTraceBegio >/dev/null
done
set +e
docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$FROZEN:/inputs:ro" \
    -v "$NEGATIVE_ROOT/owner-primary:/primary:ro" \
    -v "$NEGATIVE_ROOT/owner-repro:/repro:ro" \
    -v "$PRODUCER_ROOT/verify_generation.py:/verify_generation.py:ro" \
    "$IMAGE" \
    /usr/bin/python3 /verify_generation.py \
        --readelf /inputs/oh/toolchain/bin/llvm-readelf \
        --primary /primary \
        --repro /repro \
        --policy no-broad-art-stub-v1 \
        --output /tmp/forbidden.json \
        >"$NEGATIVE_ROOT/owner.stdout" \
        2>"$NEGATIVE_ROOT/owner.stderr"
owner_rc=$?
set -e
test "$owner_rc" -ne 0
grep -q 'real owner mismatch for PaletteTraceBegin' "$NEGATIVE_ROOT/owner.stderr"

echo "PASS no_broad_art_stub_regression providers=23 deterministic=2 broad_stub_absent=1 mutants=2 product_activation=false"
