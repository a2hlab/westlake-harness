#!/usr/bin/env bash
# Build the strict ARM64 AOSP/Bionic provider generation from only the frozen
# project-local inputs created by import_inputs.sh.

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
GENERATION_ID=${WESTLAKE_PROVIDER_GENERATION_ID:-provider-inputs-v1}
GENERATION_ROOT=${WESTLAKE_PROVIDER_GENERATION_ROOT:-$PROJECT_ROOT/.work/bionic-musl-provider/$GENERATION_ID}
BUILD_RUN=${WESTLAKE_PROVIDER_BUILD_RUN:-primary}
case "$BUILD_RUN" in
    *[!A-Za-z0-9._-]*|'') echo "ERROR: unsafe build run: $BUILD_RUN" >&2; exit 2 ;;
esac
if [[ "$BUILD_RUN" == primary ]]; then
    RUN_SUFFIX=
else
    RUN_SUFFIX="-$BUILD_RUN"
fi
FROZEN="$GENERATION_ROOT/frozen"
HASHES="$GENERATION_ROOT/frozen.sha256"
WORK="$GENERATION_ROOT/work$RUN_SUFFIX"
ARTIFACTS="$GENERATION_ROOT/artifacts$RUN_SUFFIX"
HASH_LOG="$GENERATION_ROOT/evidence/input-hash-check$RUN_SUFFIX.log"
RUNTIME_LOCK="$GENERATION_ROOT/container-runtime$RUN_SUFFIX.lock"
BUILD_STDOUT="$GENERATION_ROOT/evidence/build$RUN_SUFFIX.stdout"
BUILD_STDERR="$GENERATION_ROOT/evidence/build$RUN_SUFFIX.stderr"

case "$GENERATION_ROOT" in
    "$PROJECT_ROOT"/.work/bionic-musl-provider/*) ;;
    *) echo "ERROR: generation root must stay below the current project" >&2; exit 2 ;;
esac
for required in "$FROZEN" "$HASHES" "$GENERATION_ROOT/provenance.tsv"; do
    [[ -e "$required" && ! -L "$required" ]] || {
        echo "ERROR: missing immutable provider input: $required" >&2
        exit 1
    }
done
if find "$FROZEN" -type l -print -quit | grep -q .; then
    echo "ERROR: frozen provider closure contains a symlink" >&2
    exit 1
fi

mkdir -p "$WORK/tmp" "$WORK/home" "$ARTIFACTS" "$GENERATION_ROOT/evidence"
(cd "$FROZEN" && shasum -a 256 -c "$HASHES") \
    >"$HASH_LOG"

IMAGE=westlake-oharm64build:local-tools
IMAGE_ID=$(docker image inspect "$IMAGE" --format '{{.Id}}')
printf 'image=%s\nimage_id=%s\nnetwork=none\ninputs_read_only=true\n' \
    "$IMAGE" "$IMAGE_ID" >"$RUNTIME_LOCK"

docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$FROZEN:/inputs:ro" \
    -v "$WORK:/work:rw" \
    -v "$ARTIFACTS:/artifacts:rw" \
    -v "$WORK/tmp:/tmp:rw" \
    "$IMAGE" \
    /inputs/adapter/build/provider_generation/container_build.sh \
    >"$BUILD_STDOUT" \
    2>"$BUILD_STDERR"

echo "PASS strict provider generation built from project-local frozen inputs run=$BUILD_RUN"
