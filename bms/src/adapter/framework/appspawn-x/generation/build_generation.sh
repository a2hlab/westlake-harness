#!/usr/bin/env bash
# Rebuild the frozen AArch64 compat + stock HAP wrapper + appspawn-x generation.
# This script has no external source/sysroot/library path and refuses an input
# byte change before starting the locked, read-only container.

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd -P)
GENERATION_ROOT=${WESTLAKE_GENERATION_ROOT:-$PROJECT_ROOT/.work/product-tls-generation}
MODE=full

if [[ ${1:-} == "--wrapper-id-probe" ]]; then
    MODE=probe
elif [[ $# -ne 0 ]]; then
    echo "usage: $0 [--wrapper-id-probe]" >&2
    exit 2
fi

if [[ -z "${WESTLAKE_GENERATION_ROOT:-}" ]]; then
    case "$GENERATION_ROOT" in
        "$PROJECT_ROOT"/.work/*) ;;
        *) echo "ERROR: generation root must be below $PROJECT_ROOT/.work" >&2; exit 2 ;;
    esac
fi

FROZEN="$GENERATION_ROOT/frozen"
HASHES="$GENERATION_ROOT/frozen.sha256"
PROVENANCE="$GENERATION_ROOT/provenance.tsv"
TOOL_LOCK="$GENERATION_ROOT/tool_runtime.lock"
WORK="$GENERATION_ROOT/work"
ARTIFACTS="$GENERATION_ROOT/artifacts"

for required in "$FROZEN" "$HASHES" "$PROVENANCE" "$TOOL_LOCK"; do
    [[ -e "$required" ]] || {
        echo "ERROR: missing frozen closure input: $required" >&2
        echo "Run $SCRIPT_DIR/import_inputs.sh first." >&2
        exit 1
    }
done

if find "$FROZEN" -type l -print -quit | grep -q .; then
    echo "ERROR: frozen closure contains a symlink escape" >&2
    exit 1
fi

mkdir -p "$WORK/hash-check" "$WORK/tmp" "$WORK/home" "$ARTIFACTS"
export TMPDIR="$WORK/tmp"
if ! (cd "$FROZEN" && shasum -a 256 -c "$HASHES") \
    >"$WORK/hash-check/stdout" 2>"$WORK/hash-check/stderr"; then
    echo "ERROR: frozen input closure hash check failed" >&2
    exit 1
fi

EXPECTED_IMAGE=$(awk -F= '$1 == "image_id" {print $2}' "$TOOL_LOCK")
ACTUAL_IMAGE=$(docker image inspect westlake-oharm64build:local-tools --format '{{.Id}}')
[[ -n "$EXPECTED_IMAGE" && "$ACTUAL_IMAGE" == "$EXPECTED_IMAGE" ]] || {
    echo "ERROR: locked linux/amd64 tool-runtime image changed" >&2
    exit 1
}

# All deletion is confined to this producer's own project-local writable
# output roots.  Frozen inputs and provenance remain immutable.
find "$WORK" -mindepth 1 -maxdepth 1 ! -name hash-check -exec rm -rf -- {} +
find "$ARTIFACTS" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
mkdir -p "$WORK/tmp" "$WORK/home" "$ARTIFACTS"

run_container()
{
    docker run --rm \
        --platform linux/amd64 \
        --read-only \
        --network none \
        --cap-drop ALL \
        --security-opt no-new-privileges \
        "$@" \
        -v "$FROZEN:/inputs:ro" \
        -v "$FROZEN/toolchain:/toolchain:ro" \
        -v "$WORK:/work:rw" \
        -v "$ARTIFACTS:/artifacts:rw" \
        -v "$WORK/tmp:/tmp:rw" \
        westlake-oharm64build:local-tools \
        /inputs/config/container_build.sh
}

if [[ "$MODE" == probe ]]; then
    run_container -e WESTLAKE_WRAPPER_ID_PROBE=1
else
    run_container
fi

{
    printf 'status=%s\n' "$([[ "$MODE" == full ]] && printf build_pass || printf wrapper_id_probe)"
    printf 'frozen_manifest_sha256=%s\n' "$(shasum -a 256 "$HASHES" | awk '{print $1}')"
    printf 'provenance_sha256=%s\n' "$(shasum -a 256 "$PROVENANCE" | awk '{print $1}')"
    printf 'tool_runtime_lock_sha256=%s\n' "$(shasum -a 256 "$TOOL_LOCK" | awk '{print $1}')"
    printf 'container_image_id=%s\n' "$ACTUAL_IMAGE"
    printf 'device_verified=false\n'
    printf 'bionic_slot5_guard_semantics=false\n'
    printf 'first_frame_stub_call_closure=false\n'
} >"$GENERATION_ROOT/build-result.env"

if [[ "$MODE" == full ]]; then
    echo "build_pass: project-local same-generation assets are in $ARTIFACTS"
else
    echo "wrapper-ID probe only: update child_main pin and expected_wrapper_build_id.txt before full build"
fi
