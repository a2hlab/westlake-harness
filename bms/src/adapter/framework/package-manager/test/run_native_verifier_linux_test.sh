#!/bin/bash
# Builds and runs the sealed-fd + native APK Signature Scheme v2/v3 verifier
# corpus. Runs inside a Linux container because CopyToSealedMemfd requires
# memfd_create/F_SEAL_* (Linux-only), and against the real canonical
# CardWords fixture so V0's positive case is a genuine v2 signature, not a
# synthetic one.
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

docker run --rm \
    --platform "$PLATFORM" \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --tmpfs /tmp:rw,nosuid,nodev,exec,size=128m \
    --mount "type=bind,src=$PACKAGE_DIR,dst=/work,readonly" \
    --mount "type=bind,src=$SIGNED_APK,dst=/fixtures/signed-v2.apk,readonly" \
    --mount "type=bind,src=$ALGO_MISMATCH_APK,dst=/fixtures/algo-mismatch.apk,readonly" \
    --mount "type=bind,src=$V31_STRIPPED_APK,dst=/fixtures/v31-stripped.apk,readonly" \
    --mount "type=bind,src=$V31_POSITIVE_APK,dst=/fixtures/v31-positive.apk,readonly" \
    "$IMAGE" bash -lc '
set -euo pipefail
mkdir -p /tmp/oh_adapter_apk_verify_tests
g++ -std=c++17 -D_GNU_SOURCE -Wall -Wextra -Werror \
  -I/work/jni \
  -I/usr/include/minizip \
  /work/jni/apk_verify_result.cpp \
  /work/jni/apk_signature_verifier.cpp \
  /work/jni/apk_verifier_client.cpp \
  /work/test/test_apk_verifier_client_native.cpp \
  -lcrypto -lminizip -lz \
  -o /tmp/oh_adapter_apk_verify_tests/test_apk_verifier_client_native
/tmp/oh_adapter_apk_verify_tests/test_apk_verifier_client_native \
  /fixtures/signed-v2.apk \
  /fixtures/algo-mismatch.apk \
  /fixtures/v31-stripped.apk \
  /fixtures/v31-positive.apk
g++ -std=c++17 -Wall -Wextra -Werror \
  -I/work/jni \
  /work/jni/game_install_plan_wire.cpp \
  /work/test/test_game_install_plan_wire.cpp \
  -o /tmp/oh_adapter_apk_verify_tests/test_game_install_plan_wire
/tmp/oh_adapter_apk_verify_tests/test_game_install_plan_wire
gcc -std=c11 -Wall -Wextra -Werror \
  -I/work/install_plan/include \
  -c /work/install_plan/src/sha256.c \
  -o /tmp/oh_adapter_apk_verify_tests/sha256.o
g++ -std=c++17 -Wall -Wextra -Werror \
  -I/work/jni \
  -I/work/install_plan/include \
  -I/usr/include/minizip \
  /work/jni/apk_native_inventory.cpp \
  /work/jni/apk_native_inventory_names.cpp \
  /work/package_transaction/tests/native_inventory_linux_test.cpp \
  /tmp/oh_adapter_apk_verify_tests/sha256.o \
  -lminizip -lz \
  -o /tmp/oh_adapter_apk_verify_tests/test_native_inventory
/tmp/oh_adapter_apk_verify_tests/test_native_inventory /fixtures/signed-v2.apk
g++ -std=c++17 -D_GNU_SOURCE -Wall -Wextra -Werror \
  -I/work/jni \
  -I/work/package_transaction/include \
  -I/work/install_plan/include \
  /work/jni/prepass_context_wire.cpp \
  /work/jni/install_prepass_materializer.cpp \
  /work/package_transaction/src/elf_prepass_analyzer.cpp \
  /work/package_transaction/src/prepass_bundle.cpp \
  /work/test/test_install_prepass_materializer.cpp \
  /tmp/oh_adapter_apk_verify_tests/sha256.o \
  -o /tmp/oh_adapter_apk_verify_tests/test_install_prepass_materializer
/tmp/oh_adapter_apk_verify_tests/test_install_prepass_materializer
'
