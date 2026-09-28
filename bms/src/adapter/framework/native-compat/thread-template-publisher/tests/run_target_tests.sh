#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
MODULE=$(cd "$SCRIPT_DIR/.." && pwd -P)
PROJECT_ROOT=$(cd "$MODULE/../../../.." && pwd -P)
BUILD_LOCK=$MODULE/evidence/tool-runtime.lock
RUN_LOCK=$SCRIPT_DIR/target_runtime.lock
LOADER=$PROJECT_ROOT/adapter/frozen/product_inputs/cardwords-current/target-observed/ld-musl-aarch64.so.1
LOADER_SHA=316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98
OUT=$MODULE/out/target

for input in "$BUILD_LOCK" "$RUN_LOCK" "$LOADER"; do
    [[ -f "$input" ]] || { echo "ERROR missing input: $input" >&2; exit 2; }
done
BUILD_IMAGE=$(awk -F= '$1 == "image_id" {print $2}' "$BUILD_LOCK")
RUN_IMAGE=$(awk -F= '$1 == "image_id" {print $2}' "$RUN_LOCK")
[[ -n "$BUILD_IMAGE" && -n "$RUN_IMAGE" ]] || {
    echo "ERROR empty locked image identity" >&2
    exit 2
}
[[ $(docker image inspect "$BUILD_IMAGE" --format '{{.Id}}') == "$BUILD_IMAGE" ]]
[[ $(docker image inspect "$RUN_IMAGE" --format '{{.Id}}') == "$RUN_IMAGE" ]]
[[ $(shasum -a 256 "$LOADER" | awk '{print $1}') == "$LOADER_SHA" ]]

mkdir -p "$OUT/logs" "$OUT/tmp"
docker run --rm \
    --platform linux/amd64 \
    --read-only \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    -v "$PROJECT_ROOT:/project:rw" \
    -w /project \
    "$BUILD_IMAGE" \
    /project/adapter/framework/native-compat/thread-template-publisher/tests/build_target_in_container.sh

if [[ -f "$OUT/ld-musl-aarch64.so.1" ]]; then
    chmod 0644 "$OUT/ld-musl-aarch64.so.1"
fi
cp "$LOADER" "$OUT/ld-musl-aarch64.so.1"
chmod 0555 "$OUT/ld-musl-aarch64.so.1"
[[ $(shasum -a 256 "$OUT/ld-musl-aarch64.so.1" | awk '{print $1}') == "$LOADER_SHA" ]]

run_exact_loader()
{
    local binary=$1
    docker run --rm \
        --platform linux/arm64 \
        --read-only \
        --network none \
        --cap-drop ALL \
        --security-opt no-new-privileges \
        -v "$PROJECT_ROOT:/project:rw" \
        -v "$OUT/ld-musl-aarch64.so.1:/lib/ld-musl-aarch64.so.1:ro" \
        -w /project \
        "$RUN_IMAGE" \
        "$binary"
}

GOOD=/project/adapter/framework/native-compat/thread-template-publisher/out/target/thread-template-target
run_exact_loader "$GOOD" >"$OUT/logs/runtime-good.log" 2>&1
grep -q 'PASS exact OH loader parent-A child-B COW template generations' \
    "$OUT/logs/runtime-good.log"

: >"$OUT/runtime-receipts.tsv"
printf 'good\t0\n' >>"$OUT/runtime-receipts.tsv"
for spec in \
    'unpatched:9:new-thread TLS template copy' \
    'wrong-offset:9:new-thread TLS template copy' \
    'wrong-image:9:new-thread TLS template copy' \
    'no-restore:10:template protection not restored' \
    'conflict:9:new-thread TLS template copy' \
    'no-exact-once:11:second template publication was not rejected' \
    'skip-child-reset:19:child inherited-A reset' \
    'reuse-parent-template:19:child inherited-A reset'
do
    IFS=: read -r name expected message <<<"$spec"
    binary="/project/adapter/framework/native-compat/thread-template-publisher/out/target/mutants/$name/thread-template-target"
    set +e
    run_exact_loader "$binary" >"$OUT/logs/runtime-$name.log" 2>&1
    rc=$?
    set -e
    [[ $rc -eq $expected ]] || {
        echo "ERROR runtime mutant $name returned $rc, expected $expected" >&2
        exit 1
    }
    grep -q "$message" "$OUT/logs/runtime-$name.log"
    printf '%s\t%s\n' "$name" "$rc" >>"$OUT/runtime-receipts.tsv"
done

{
    printf 'status=exact_loader_runtime_pass\n'
    printf 'observed_loader_sha256=%s\n' "$LOADER_SHA"
    printf 'product_publisher_source_reused=true\n'
    printf 'deterministic_target_builds=2\n'
    printf 'structural_mutants_killed=9\n'
    printf 'runtime_mutants_killed=8\n'
    printf 'pt_tls_filesz=48\n'
    printf 'pt_tls_memsz=48\n'
    printf 'device_verified=false\n'
    printf 'product_activation=false\n'
} >"$OUT/result.env"

sha256sum \
    "$MODULE/include/westlake_thread_template_publisher.h" \
    "$MODULE/src/thread_template_publisher.c" \
    "$MODULE/tests/target/main_tls_template_aarch64.S" \
    "$MODULE/tests/target/template_publisher_target.c" \
    "$MODULE/tests/build_target_in_container.sh" \
    "$MODULE/tests/run_target_tests.sh" \
    "$MODULE/tests/verify_target_fixture.py" \
    "$BUILD_LOCK" \
    "$RUN_LOCK" \
    "$OUT/ld-musl-aarch64.so.1" \
    "$OUT/thread-template-target" \
    "$OUT/target-verification.json" \
    "$OUT/runtime-receipts.tsv" \
    "$OUT/result.env" \
    >"$OUT/MANIFEST.sha256"

echo "PASS exact frozen OH loader product-publisher runtime_mutants=8 product_activation=false"
