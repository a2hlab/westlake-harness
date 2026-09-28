#!/usr/bin/env bash
# Run package-manager result, native verifier, and typed-plan tests using
# current-project sources and a project-pinned immutable tool runtime.
set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
ADAPTER_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
REPO_ROOT=$(cd "$PROJECT_ROOT/.." && pwd -P)
LOCK=$ADAPTER_ROOT/frozen/tool-runtimes/package-manager-host-linux.lock
FIXTURE_LOCK=$ADAPTER_ROOT/frozen/test-inputs/package-manager-signed-v2.lock
OUT=${PACKAGE_MANAGER_REGRESSION_OUT:-$ADAPTER_ROOT/.work/package-manager-host-regression}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: package-manager regression output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2
    exit 2
fi
[[ -f "$LOCK" && ! -L "$LOCK" ]] || {
    echo "ERROR: missing project-local tool-runtime lock" >&2
    exit 2
}
[[ -f "$FIXTURE_LOCK" && ! -L "$FIXTURE_LOCK" ]] || {
    echo "ERROR: missing project-local signed APK fixture lock" >&2
    exit 2
}

IMAGE=$(awk -F= '$1 == "image_id" {print $2}' "$LOCK")
PLATFORM=$(awk -F= '$1 == "platform" {print $2}' "$LOCK")
FIXTURE_RELATIVE=$(awk -F= '$1 == "repo_relative_path" {print $2}' "$FIXTURE_LOCK")
FIXTURE_SHA256=$(awk -F= '$1 == "sha256" {print $2}' "$FIXTURE_LOCK")
[[ "$IMAGE" =~ ^sha256:[0-9a-f]{64}$ ]] || {
    echo "ERROR: invalid locked image ID" >&2
    exit 2
}
[[ "$PLATFORM" == "linux/arm64" ]] || {
    echo "ERROR: unexpected locked platform: $PLATFORM" >&2
    exit 2
}
case "$FIXTURE_RELATIVE" in
    var/evidence/fixtures/*) ;;
    *) echo "ERROR: signed APK fixture escaped the fixture corpus" >&2; exit 2 ;;
esac
FIXTURE=$REPO_ROOT/$FIXTURE_RELATIVE
[[ -f "$FIXTURE" && ! -L "$FIXTURE" ]] || {
    echo "ERROR: missing locked signed APK fixture" >&2
    exit 2
}
[[ "$FIXTURE_SHA256" =~ ^[0-9a-f]{64}$ ]] || {
    echo "ERROR: invalid signed APK fixture digest" >&2
    exit 2
}
ACTUAL_FIXTURE_SHA256=$(sha256sum "$FIXTURE" | awk '{print $1}')
[[ "$ACTUAL_FIXTURE_SHA256" == "$FIXTURE_SHA256" ]] || {
    echo "ERROR: signed APK fixture identity changed" >&2
    exit 1
}
ACTUAL=$(docker image inspect "$IMAGE" --format '{{.Id}}')
[[ "$ACTUAL" == "$IMAGE" ]] || {
    echo "ERROR: package-manager tool runtime identity changed" >&2
    exit 1
}

mkdir -p "$OUT"
docker run --rm \
    --platform "$PLATFORM" \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$PROJECT_ROOT:/project:ro" \
    -v "$FIXTURE:/fixtures/signed-v2.apk:ro" \
    -v "$OUT:/out:rw" \
    -w /project \
    "$IMAGE" \
    /project/adapter/framework/package-manager/test/package_manager_regression_inside.sh
