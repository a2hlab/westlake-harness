#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ADAPTER_ROOT="$(cd "$PACKAGE_DIR/../.." && pwd)"
PROJECT_ROOT="$(cd "$ADAPTER_ROOT/.." && pwd)"
REPO_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"
LOCK="$ADAPTER_ROOT/frozen/tool-runtimes/package-manager-host-linux.lock"
FIXTURE_LOCK="$ADAPTER_ROOT/frozen/test-inputs/package-manager-signed-v2.lock"
SIGNATURE_CORPUS_LOCK="$ADAPTER_ROOT/frozen/test-inputs/package-manager-aosp-signature-corpus.lock"
IMAGE="$(awk -F= '$1 == "image_id" {print $2}' "$LOCK")"
PLATFORM="$(awk -F= '$1 == "platform" {print $2}' "$LOCK")"
FIXTURE_RELATIVE="$(awk -F= '$1 == "repo_relative_path" {print $2}' "$FIXTURE_LOCK")"
FIXTURE_SHA256="$(awk -F= '$1 == "sha256" {print $2}' "$FIXTURE_LOCK")"
SIGNED_APK="$REPO_ROOT/$FIXTURE_RELATIVE"
ALGO_MISMATCH_NAME="v2-only-signatures-and-digests-block-mismatch.apk"
V31_STRIPPED_NAME="v31-block-stripped-v3-attr-value-33.apk"
V31_POSITIVE_NAME="v31-ec-p256_2-tgt-33-ec-p256-tgt-1-27-and-100001.apk"
lock_value()
{
    local fixture="$1"
    local key="$2"
    awk -F= -v fixture="$fixture" -v key="$key" '
        $1 == "fixture" { current = $2 }
        current == fixture && $1 == key { print $2; exit }
    ' "$SIGNATURE_CORPUS_LOCK"
}
ALGO_MISMATCH_RELATIVE="$(lock_value "$ALGO_MISMATCH_NAME" repo_relative_path)"
ALGO_MISMATCH_SHA256="$(lock_value "$ALGO_MISMATCH_NAME" sha256)"
V31_STRIPPED_RELATIVE="$(lock_value "$V31_STRIPPED_NAME" repo_relative_path)"
V31_STRIPPED_SHA256="$(lock_value "$V31_STRIPPED_NAME" sha256)"
V31_POSITIVE_RELATIVE="$(lock_value "$V31_POSITIVE_NAME" repo_relative_path)"
V31_POSITIVE_SHA256="$(lock_value "$V31_POSITIVE_NAME" sha256)"
ALGO_MISMATCH_APK="$REPO_ROOT/$ALGO_MISMATCH_RELATIVE"
V31_STRIPPED_APK="$REPO_ROOT/$V31_STRIPPED_RELATIVE"
V31_POSITIVE_APK="$REPO_ROOT/$V31_POSITIVE_RELATIVE"
HOST_OUT="${FN01_A13_HOST_OUT:-$ADAPTER_ROOT/.work/fn01-a13-host}"
RUN_ID="run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
RUN_DIR="$HOST_OUT/$RUN_ID"

mkdir -p "$RUN_DIR"

if [ ! -f "$SIGNED_APK" ]; then
    echo "signed APK fixture not found: $SIGNED_APK" >&2
    exit 1
fi
if [ "$(sha256sum "$SIGNED_APK" | awk '{print $1}')" != "$FIXTURE_SHA256" ]; then
    echo "signed APK fixture identity changed: $SIGNED_APK" >&2
    exit 1
fi
if [ "$(sha256sum "$ALGO_MISMATCH_APK" | awk '{print $1}')" != "$ALGO_MISMATCH_SHA256" ]; then
    echo "AOSP algorithm-list mismatch fixture identity changed" >&2
    exit 1
fi
if [ "$(sha256sum "$V31_STRIPPED_APK" | awk '{print $1}')" != "$V31_STRIPPED_SHA256" ]; then
    echo "AOSP v3.1 stripping fixture identity changed" >&2
    exit 1
fi
if [ "$(sha256sum "$V31_POSITIVE_APK" | awk '{print $1}')" != "$V31_POSITIVE_SHA256" ]; then
    echo "AOSP v3.1 positive fixture identity changed" >&2
    exit 1
fi
if [ "$(docker image inspect "$IMAGE" --format '{{.Id}}')" != "$IMAGE" ]; then
    echo "locked test image identity changed: $IMAGE" >&2
    exit 1
fi

{
    echo "action_id=Fn01.A13"
    echo "run_id=$RUN_ID"
    echo "image_id=$IMAGE"
    echo "platform=$PLATFORM"
    echo "fixture_relative=$FIXTURE_RELATIVE"
    echo "fixture_sha256=$FIXTURE_SHA256"
    echo "algo_mismatch_fixture_sha256=$ALGO_MISMATCH_SHA256"
    echo "v31_stripped_fixture_sha256=$V31_STRIPPED_SHA256"
    echo "v31_positive_fixture_sha256=$V31_POSITIVE_SHA256"
    echo "formal_verdict=NOT_ISSUED"
} > "$RUN_DIR/fixture-manifest.txt"

docker run --rm \
    --platform "$PLATFORM" \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --tmpfs /tmp:rw,nosuid,nodev,exec,size=256m \
    --mount "type=bind,src=$PACKAGE_DIR,dst=/work,readonly" \
    --mount "type=bind,src=$SIGNED_APK,dst=/fixtures/signed-v2.apk,readonly" \
    --mount "type=bind,src=$ALGO_MISMATCH_APK,dst=/fixtures/algo-mismatch.apk,readonly" \
    --mount "type=bind,src=$V31_STRIPPED_APK,dst=/fixtures/v31-stripped.apk,readonly" \
    --mount "type=bind,src=$V31_POSITIVE_APK,dst=/fixtures/v31-positive.apk,readonly" \
    --mount "type=bind,src=$RUN_DIR,dst=/evidence" \
    "$IMAGE" bash -lc '
set -euo pipefail
mkdir -p /tmp/fn01_a13
gcc -std=c11 -Wall -Wextra -Werror \
  -I/work/install_plan/include \
  -c /work/install_plan/src/sha256.c \
  -o /tmp/fn01_a13/sha256.o
g++ -std=c++17 -D_GNU_SOURCE -Wall -Wextra -Werror \
  -Wno-deprecated-declarations \
  -I/work/jni \
  -I/work/install_plan/include \
  -I/work/package_transaction/include \
  -I/work/signing_metadata/include \
  -I/usr/include/minizip \
  /work/package_transaction/src/package_transaction.cpp \
  /work/jni/apk_verify_result.cpp \
  /work/jni/apk_signature_verifier.cpp \
  /work/signing_metadata/src/signing_metadata_v1.cpp \
  /work/signing_metadata/tests/signing_metadata_host_test.cpp \
  /tmp/fn01_a13/sha256.o \
  -lcrypto -lminizip -lz -pthread \
  -o /tmp/fn01_a13/signing_metadata_host_test
/tmp/fn01_a13/signing_metadata_host_test \
  /fixtures/signed-v2.apk /evidence \
  /fixtures/algo-mismatch.apk /fixtures/v31-stripped.apk \
  /fixtures/v31-positive.apk
sha256sum /tmp/fn01_a13/signing_metadata_host_test \
  > /evidence/host-binary.sha256
' 2>&1 | tee "$RUN_DIR/host-build-and-test.log"

echo "$RUN_DIR"
