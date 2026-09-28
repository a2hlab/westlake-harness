#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
OUT=$SCRIPT_DIR/out/host
CC=${CC:-clang}
CXX=${CXX:-clang++}

mkdir -p "$OUT/bin" "$OUT/logs" "$OUT/tmp"
export TMPDIR=$OUT/tmp
: >"$OUT/logs/commands.txt"

COMMON=(
    -std=c11
    -Wall
    -Wextra
    -Werror
    -pedantic
    -pthread
    -I"$SCRIPT_DIR/tests/include"
    -I"$SCRIPT_DIR/include"
    -I"$SCRIPT_DIR/../../src"
    -I"$SCRIPT_DIR/../../../native-compat/thread-guard-registry/include"
)

run_linux_product_bundle()
{
    local manifest=$SCRIPT_DIR/out/target/pass1/sealed_provider_manifest.c
    local generated=$OUT/generated-product-bundle
    local manifest_digest
    local artifact_generation
    local policy_provenance
    local policy_epoch
    local launch_generation
    local boot_id
    local hook_digest

    [[ -r /proc/sys/kernel/random/boot_id &&
       -r /proc/self/stat &&
       -f "$manifest" ]] || {
        echo "ERROR production bundle requires live procfs and actual generated manifest" >&2
        return 1
    }
    mkdir -p "$generated"
    manifest_digest=$(
        python3 - "$manifest" <<'PY'
from pathlib import Path
import re
import sys
text = Path(sys.argv[1]).read_text(encoding="utf-8")
part = text[text.index("static const WlscplManifestV2 kWlscplManifest"):]
values = re.findall(r"UINT8_C\(0x([0-9a-f]{2})\)", part)
if len(values) < 32:
    raise SystemExit("generated manifest digest absent")
print("".join(values[:32]))
PY
    )
    artifact_generation=$(sha256sum "$SCRIPT_DIR/ROUTE_A_INPUTS.json" |
        awk '{print $1}')
    policy_provenance=$(sha256sum "$SCRIPT_DIR/SOURCE_CLOSURE.json" |
        awk '{print $1}')
    policy_epoch=$((16#${policy_provenance:0:15}))
    launch_generation=$((16#${artifact_generation:0:15}))
    boot_id=$(tr -d '\r\n' </proc/sys/kernel/random/boot_id)
    hook_digest=$(
        python3 - <<'PY'
import hashlib
canonical = bytearray(64)
descriptor = b"WL-HOOK-V1-CANONICAL"
contract = b"cap=0x3ff;ptr=8;align=8"
canonical[:len(descriptor)] = descriptor
canonical[32:32 + len(contract)] = contract
print(hashlib.sha256(canonical).hexdigest())
PY
    )
    python3 "$SCRIPT_DIR/generate_generation_metadata.py" \
        --artifact-generation-digest "$artifact_generation" \
        --manifest-digest "$manifest_digest" \
        --manifest-source "$manifest" \
        --hook-digest "$hook_digest" \
        --policy-epoch "$policy_epoch" \
        --policy-provenance-digest "$policy_provenance" \
        --launch-generation "$launch_generation" \
        --boot-id "$boot_id" \
        --output-c "$generated/generated_generation_metadata.c" \
        >"$OUT/logs/generation_metadata.stdout" \
        2>"$OUT/logs/generation_metadata.stderr"
    printf '%q ' "$CC" "${COMMON[@]}" \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        "$SCRIPT_DIR/src/stage_receipt.c" \
        "$SCRIPT_DIR/src/westlake_generation_identity_facts.c" \
        "$SCRIPT_DIR/src/westlake_generation_identity_ops.c" \
        "$SCRIPT_DIR/src/westlake_generation_identity_producer.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$manifest" \
        "$generated/generated_generation_metadata.c" \
        "$SCRIPT_DIR/tests/test_production_bundle.c" \
        -o "$generated/test_production_bundle" \
        >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        "$SCRIPT_DIR/src/stage_receipt.c" \
        "$SCRIPT_DIR/src/westlake_generation_identity_facts.c" \
        "$SCRIPT_DIR/src/westlake_generation_identity_ops.c" \
        "$SCRIPT_DIR/src/westlake_generation_identity_producer.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$manifest" \
        "$generated/generated_generation_metadata.c" \
        "$SCRIPT_DIR/tests/test_production_bundle.c" \
        -o "$generated/test_production_bundle"
    ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
        "$generated/test_production_bundle" \
        >"$OUT/logs/production_bundle.stdout" \
        2>"$OUT/logs/production_bundle.stderr"
    grep -F "PRODUCTION_BUNDLE_PASS acquire=1 build=1 live_proc=1 real_getrandom=1 generated_metadata=1 stock_receipt_le=1" \
        "$OUT/logs/production_bundle.stdout"
}

if [[ ${WLGR_LINUX_BUNDLE_ONLY:-0} == 1 ]]; then
    run_linux_product_bundle
    exit 0
fi

run_product_bundle_gate()
{
    if [[ -r /proc/sys/kernel/random/boot_id ]]; then
        run_linux_product_bundle
        return
    fi

    local project_root
    local image
    project_root=$(cd "$SCRIPT_DIR/../../../../.." && pwd -P)
    image=sha256:b24ce148326aa80bfa499bccc19b0ea6c3c6f78b62fb9507d8303c9838e040b7
    docker image inspect "$image" --format '{{.Id}}' |
        grep -Fx "$image" >/dev/null
    docker run --rm \
        --platform linux/amd64 \
        --network none \
        --cap-drop ALL \
        --security-opt no-new-privileges \
        -e WLGR_LINUX_BUNDLE_ONLY=1 \
        -e CC=cc \
        -e CXX=c++ \
        -v "$project_root:/project:rw" \
        -w /project/adapter/framework/appspawn-x/security_specialization/stock_child_plugin \
        "$image" \
        ./run_host_tests.sh
}

build_stage_receipt()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/stage_receipt.c" \
        "$SCRIPT_DIR/tests/test_stage_receipt.c" "$@" -o "$output" \
        >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/stage_receipt.c" \
        "$SCRIPT_DIR/tests/test_stage_receipt.c" "$@" -o "$output"
}

build_host_services()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/host_runtime_services.c" \
        "$SCRIPT_DIR/tests/test_host_runtime_services.c" "$@" -o "$output" \
        >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/host_runtime_services.c" \
        "$SCRIPT_DIR/tests/test_host_runtime_services.c" "$@" -o "$output"
}

build_sha256()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_westlake_sha256.c" "$@" -o "$output" \
        >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_westlake_sha256.c" "$@" -o "$output"
}

build_loader_phase()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/runtime_loader_phase.c" \
        "$SCRIPT_DIR/tests/test_runtime_loader_phase.c" "$@" -o "$output" \
        >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/runtime_loader_phase.c" \
        "$SCRIPT_DIR/tests/test_runtime_loader_phase.c" "$@" -o "$output"
}

build_child_hook_table()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/child_hook_table_v1.c" \
        "$SCRIPT_DIR/tests/test_child_hook_table_v1.c" "$@" -o "$output" \
        >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/child_hook_table_v1.c" \
        "$SCRIPT_DIR/tests/test_child_hook_table_v1.c" "$@" -o "$output"
}

build_child_hook_layout()
{
    local output=$1
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/tests/test_westlake_child_hook_table_v1_layout.c" \
        -o "$output" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/tests/test_westlake_child_hook_table_v1_layout.c" \
        -o "$output"
}

build_sealed_child_loader()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" -DWLSCPL_TESTING \
        "$SCRIPT_DIR/src/sealed_child_provider_loader.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_sealed_child_provider_loader.c" \
        "$@" -ldl -o "$output" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" -DWLSCPL_TESTING \
        "$SCRIPT_DIR/src/sealed_child_provider_loader.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_sealed_child_provider_loader.c" \
        "$@" -ldl -o "$output"
}

build_generation_identity_producer()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/westlake_generation_identity_producer.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_westlake_generation_identity_producer.c" \
        "$@" -o "$output" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/westlake_generation_identity_producer.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_westlake_generation_identity_producer.c" \
        "$@" -o "$output"
}

build_generation_identity_facts()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/westlake_generation_identity_facts.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_westlake_generation_identity_facts.c" \
        "$@" -o "$output" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/src/westlake_generation_identity_facts.c" \
        "$SCRIPT_DIR/src/westlake_sha256.c" \
        "$SCRIPT_DIR/tests/test_westlake_generation_identity_facts.c" \
        "$@" -o "$output"
}

build_generation_receipt_v2_c()
{
    local output=$1
    shift
    printf '%q ' "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/tests/test_westlake_generation_receipt_v2.c" \
        "$@" -o "$output" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CC" "${COMMON[@]}" \
        "$SCRIPT_DIR/tests/test_westlake_generation_receipt_v2.c" \
        "$@" -o "$output"
}

build_generation_receipt_v2_cpp()
{
    local output=$1
    printf '%q ' "$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
        -I"$SCRIPT_DIR/include" \
        "$SCRIPT_DIR/tests/test_westlake_generation_receipt_v2.cpp" \
        -o "$output" >>"$OUT/logs/commands.txt"
    printf '\n' >>"$OUT/logs/commands.txt"
    "$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
        -I"$SCRIPT_DIR/include" \
        "$SCRIPT_DIR/tests/test_westlake_generation_receipt_v2.cpp" \
        -o "$output"
}

build_stage_receipt "$OUT/bin/test_good"
"$OUT/bin/test_good" >"$OUT/logs/good.stdout" \
    2>"$OUT/logs/good.stderr"

build_stage_receipt "$OUT/bin/test_asan_ubsan" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_asan_ubsan" >"$OUT/logs/asan_ubsan.stdout" \
    2>"$OUT/logs/asan_ubsan.stderr"

build_host_services "$OUT/bin/test_host_runtime_services"
"$OUT/bin/test_host_runtime_services" \
    >"$OUT/logs/host_runtime_services.stdout" \
    2>"$OUT/logs/host_runtime_services.stderr"

build_host_services "$OUT/bin/test_host_runtime_services_asan_ubsan" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_host_runtime_services_asan_ubsan" \
    >"$OUT/logs/host_runtime_services_asan_ubsan.stdout" \
    2>"$OUT/logs/host_runtime_services_asan_ubsan.stderr"

build_sha256 "$OUT/bin/test_westlake_sha256" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_westlake_sha256" \
    >"$OUT/logs/westlake_sha256.stdout" \
    2>"$OUT/logs/westlake_sha256.stderr"

build_loader_phase "$OUT/bin/test_runtime_loader_phase" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_runtime_loader_phase" \
    >"$OUT/logs/runtime_loader_phase.stdout" \
    2>"$OUT/logs/runtime_loader_phase.stderr"

build_child_hook_table "$OUT/bin/test_child_hook_table_v1"
"$OUT/bin/test_child_hook_table_v1" \
    >"$OUT/logs/child_hook_table_v1.stdout" \
    2>"$OUT/logs/child_hook_table_v1.stderr"

build_child_hook_table "$OUT/bin/test_child_hook_table_v1_p0" \
    -DWLASC_P0_TYPED_REJECT_CAPABILITIES=1
"$OUT/bin/test_child_hook_table_v1_p0" \
    >"$OUT/logs/child_hook_table_v1_p0.stdout" \
    2>"$OUT/logs/child_hook_table_v1_p0.stderr"

build_child_hook_layout "$OUT/bin/test_child_hook_table_v1_layout"
"$OUT/bin/test_child_hook_table_v1_layout" \
    >"$OUT/logs/child_hook_table_v1_layout.stdout" \
    2>"$OUT/logs/child_hook_table_v1_layout.stderr"

build_sealed_child_loader "$OUT/bin/test_sealed_child_provider_loader" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_sealed_child_provider_loader" \
    >"$OUT/logs/sealed_child_provider_loader.stdout" \
    2>"$OUT/logs/sealed_child_provider_loader.stderr"

build_generation_identity_producer "$OUT/bin/test_generation_identity_producer" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_generation_identity_producer" \
    >"$OUT/logs/generation_identity_producer.stdout" \
    2>"$OUT/logs/generation_identity_producer.stderr"

build_generation_identity_facts "$OUT/bin/test_generation_identity_facts" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_generation_identity_facts" \
    >"$OUT/logs/generation_identity_facts.stdout" \
    2>"$OUT/logs/generation_identity_facts.stderr"

run_product_bundle_gate \
    >"$OUT/logs/production_bundle_gate.stdout" \
    2>"$OUT/logs/production_bundle_gate.stderr"

build_generation_receipt_v2_c \
    "$OUT/bin/test_westlake_generation_receipt_v2_c" \
    -fsanitize=address,undefined -fno-omit-frame-pointer
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_westlake_generation_receipt_v2_c" \
    >"$OUT/logs/westlake_generation_receipt_v2_c.stdout" \
    2>"$OUT/logs/westlake_generation_receipt_v2_c.stderr"

build_generation_receipt_v2_cpp \
    "$OUT/bin/test_westlake_generation_receipt_v2_cpp"
"$OUT/bin/test_westlake_generation_receipt_v2_cpp" \
    >"$OUT/logs/westlake_generation_receipt_v2_cpp.stdout" \
    2>"$OUT/logs/westlake_generation_receipt_v2_cpp.stderr"

build_sealed_child_loader "$OUT/bin/test_sealed_child_loader_swap_mutant" \
    -DWLSCPL_MUTANT_SKIP_MAPPED_INODE_BIND \
    -fsanitize=address,undefined -fno-omit-frame-pointer
if ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$OUT/bin/test_sealed_child_loader_swap_mutant" \
    >"$OUT/logs/sealed_child_loader_swap_mutant.stdout" \
    2>"$OUT/logs/sealed_child_loader_swap_mutant.stderr"; then
    echo "ERROR: mapped-inode swap mutant survived" >&2
    exit 1
fi

MUTANTS=(
    WLASC_MUTANT_ALLOW_MISSING_PARENT
    WLASC_MUTANT_ALLOW_NO_SANDBOX
    WLASC_MUTANT_ALLOW_MISSING_GUARD
    WLASC_MUTANT_ALLOW_MISSING_CHILD_TAIL
)
for mutant in "${MUTANTS[@]}"; do
    build_stage_receipt "$OUT/bin/test_$mutant" -D"$mutant"
    if "$OUT/bin/test_$mutant" >"$OUT/logs/$mutant.stdout" \
        2>"$OUT/logs/$mutant.stderr"; then
        echo "ERROR: dangerous stock-stage mutant survived: $mutant" >&2
        exit 1
    fi
done

python3 "$SCRIPT_DIR/generate_source_closure.py" --verify \
    >"$OUT/logs/source_closure.stdout" \
    2>"$OUT/logs/source_closure.stderr"
python3 "$SCRIPT_DIR/verify_stock_origin.py" \
    >"$OUT/logs/stock_origin.stdout" \
    2>"$OUT/logs/stock_origin.stderr"
python3 "$SCRIPT_DIR/verify_route_a_source.py" \
    >"$OUT/logs/route_a_source.stdout" \
    2>"$OUT/logs/route_a_source.stderr"
"$SCRIPT_DIR/../../../app-native-loader/tests/host/run_host_tests.sh" \
    >"$OUT/logs/app_native_loader.stdout" \
    2>"$OUT/logs/app_native_loader.stderr"
"$SCRIPT_DIR/../../../art-palette-oh/tests/run_host_tests.sh" \
    >"$OUT/logs/art_palette_oh.stdout" \
    2>"$OUT/logs/art_palette_oh.stderr"
python3 "$SCRIPT_DIR/generate_route_a_inputs.py" --verify \
    >"$OUT/logs/route_a_inputs.stdout" \
    2>"$OUT/logs/route_a_inputs.stderr"

{
    printf 'status=build_pass\n'
    printf 'tests=70\n'
    printf 'host_runtime_services_negative_controls=41\n'
    printf 'runtime_loader_phase_negative_controls=10\n'
    printf 'child_hook_table_pnf=pass\n'
    printf 'child_hook_table_abi_layout=pass\n'
    printf 'sealed_child_provider_loader_pnf=30\n'
    printf 'generation_identity_producer_pnf=9\n'
    printf 'generation_identity_facts_pnf=9\n'
    printf 'production_bundle_acquire_build=pass\n'
    printf 'sealed_child_loader_swap_mutant_killed=1\n'
    printf 'generation_receipt_v2_c_semantics=10\n'
    printf 'generation_receipt_v2_cpp_layout=pass\n'
    printf 'mutants_killed=%s\n' "${#MUTANTS[@]}"
    printf 'app_native_loader_contract_checks=70\n'
    printf 'art_palette_real_priority_mutants_killed=1\n'
    printf 'stock_origin_gate=pass\n'
    printf 'route_a_source_gate=pass\n'
    printf 'route_a_input_closure=pass\n'
    printf 'wltg_canonical_bionic_process_guard_equals_all_admitted_slot5=false\n'
    printf 'product_activation=false\n'
    printf 'device_verified=false\n'
} >"$OUT/result.env"

echo "PASS stock child contracts tests=70 host_services_negative_controls=41 loader_phase_negative_controls=10 child_hook_pnf=pass child_hook_abi_layout=pass sealed_loader_pnf=30 generation_identity_producer_pnf=9 sealed_loader_swap_mutant=kill generation_receipt_v2=pass mutants_killed=${#MUTANTS[@]} app_native_loader_checks=70 art_palette_real_priority=pass"
