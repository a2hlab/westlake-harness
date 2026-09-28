#!/usr/bin/env bash
# One host/static Bionic/Musl regression entry point.  Every source, fixture,
# manifest and target artifact consumed by this runner is under this project.
# It never contacts a device and never upgrades host evidence to device_verified.

set -euo pipefail
IFS=$'\n\t'
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
ADAPTER_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
PROJECT_ROOT=$(cd "$ADAPTER_ROOT/.." && pwd -P)
RUN_ID=${BIONIC_MUSL_RUN_ID:-$(date -u '+%Y%m%dT%H%M%SZ')}
OUT=${BIONIC_MUSL_REGRESSION_OUT:-$ADAPTER_ROOT/research/atoms/L03/A15/evidence/runs/$RUN_ID}

case "$OUT" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "ERROR: regression output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked regression output: $OUT" >&2
    exit 2
fi
if [[ -e "$OUT/results.tsv" ]]; then
    echo "ERROR: immutable run already exists: $OUT" >&2
    exit 2
fi

mkdir -p "$OUT/logs" "$OUT/host-out"
RESULTS=$OUT/results.tsv
printf 'id\tstage\tevidence_level\tstatus\texit_code\tcommand\tlog\tnote\n' >"$RESULTS"
python3 "$SCRIPT_DIR/freeze_bionic_musl_contract.py" \
    --project-root "$PROJECT_ROOT" \
    --write "$OUT/CONTRACT_INPUTS.json" \
    >"$OUT/logs/contract-freeze.log" 2>&1

quote_command()
{
    local rendered
    printf -v rendered '%q ' "$@"
    printf '%s' "${rendered% }"
}

run_gate()
{
    local id=$1
    local stage=$2
    local evidence_level=$3
    local note=$4
    shift 4
    local log=$OUT/logs/$id.log
    local command
    command=$(quote_command "$@")
    local rc
    set +e
    "$@" >"$log" 2>&1
    rc=$?
    set -e
    local status=PASS
    if [[ $rc -ne 0 ]]; then
        status=FAIL
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$id" "$stage" "$evidence_level" "$status" "$rc" \
        "$command" "${log#$PROJECT_ROOT/}" "$note" >>"$RESULTS"
    if [[ $rc -ne 0 ]]; then
        echo "FAIL $id ($note); see ${log#$PROJECT_ROOT/}" >&2
        return "$rc"
    fi
    echo "PASS $id $note"
}

record_not_proven()
{
    local id=$1
    local stage=$2
    local note=$3
    printf '%s\t%s\t%s\tNOT_PROVEN\t-\t-\t-\t%s\n' \
        "$id" "$stage" "none" "$note" >>"$RESULTS"
}

FAILED=0
run_gate R01 S1 static_proven "02c frozen import and stronger-evidence supersession" \
    python3 "$ADAPTER_ROOT/research/atoms/L03/A15/evidence/imports/02c-verifier-20260712/verify_import.py" || FAILED=1
run_gate R02 S1 contract_tested "five-stage machine registries and total error order" \
    python3 "$ADAPTER_ROOT/research/atoms/L03/A15/acceptance/tests/validate_registries.py" || FAILED=1

CFG_RUN=$ADAPTER_ROOT/research/atoms/L03/A15/evidence/runs/20260712-cfg-unknowns-r1
run_gate R03 S1 static_proven "CFG closure local frozen-input identity" \
    python3 "$CFG_RUN/tests/verify_local_freeze.py" || FAILED=1
run_gate R04 S1 negative_tested "CFG closure fail-closed identity/class controls" \
    python3 "$CFG_RUN/tests/test_fail_closed.py" || FAILED=1
run_gate R05 S1 reproducible_static "CFG closure byte-identical two-run reproduction" \
    python3 "$CFG_RUN/tests/test_reproducibility.py" || FAILED=1

run_gate R06 S1 host_tested "install-plan immutable identity model" \
    "$ADAPTER_ROOT/framework/package-manager/install_plan/tests/host/run_host_tests.sh" || FAILED=1
run_gate R07 S1 host_tested "app-private namespace policy and negative loader cases" \
    env ANL_HOST_TEST_OUT="$OUT/host-out/app-native-loader" \
    "$ADAPTER_ROOT/framework/app-native-loader/tests/host/run_host_tests.sh" || FAILED=1
run_gate R08 S1 host_tested "native-loader C/C++ ABI and bridge policy" \
    env NATIVE_LOADER_HEADER_TEST_OUT="$OUT/host-out/native-loader-header" \
    "$ADAPTER_ROOT/framework/native-loader-oh/tests/run_header_tests.sh" || FAILED=1
run_gate R09 S1 sanitizer_tested "native-loader registry normal/ASan/TSan repeated suite" \
    env NATIVE_LOADER_REGISTRY_TEST_OUT="$OUT/host-out/native-loader-registry" \
        NATIVE_LOADER_REGISTRY_REPEATS=20 \
    "$ADAPTER_ROOT/framework/native-loader-oh/tests/run_registry_host_tests.sh" all || FAILED=1

run_gate R10 S2 negative_tested "frozen initial-closure oracle via byte-identical writable replay" \
    "$ADAPTER_ROOT/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1/run_regression_tests.sh" || FAILED=1
run_gate R11 S2 static_proven "Musl TLS allocator/ownership and collision fixtures" \
    "$ADAPTER_ROOT/framework/appspawn-x/tests/tls_layout_verifier/run_tests.sh" || FAILED=1
run_gate R12 S2 audit_only_build_pass "native-compat state machine, mutants, sanitizers, target ELF" \
    "$ADAPTER_ROOT/framework/native-compat/tests/run_all.sh" || FAILED=1

run_gate R13 S5 host_tested "real zlib adler32_combine semantics consumed by libart" \
    "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/tests/run_adler32_regression.sh" || FAILED=1
run_gate R14 S5 host_tested "AOSP abort-message magic layout, first-wins and null semantics" \
    "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/tests/run_abort_message_regression.sh" || FAILED=1
run_gate R15 S5 target_static_proven "AArch64 compatibility target build, exports, no TLS/unsafe tags" \
    "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/tests/run_target_compat_regression.sh" || FAILED=1
run_gate R16 S1 host_tested "APK verifier result and sealed-FD transport in locked local runtime" \
    env PACKAGE_MANAGER_REGRESSION_OUT="$OUT/host-out/package-manager-linux" \
    "$ADAPTER_ROOT/framework/package-manager/test/run_project_local_regressions.sh" || FAILED=1
run_gate R17 S5 disabled_fixture_build_pass "disabled aperture writer host/ARM64 fixture; product_activation=false" \
    "$ADAPTER_ROOT/framework/native-compat/tests/aperture_writer_fixture/run_all.sh" || FAILED=1
run_gate R18 S2 negative_tested "provider closure regression accurately rejects current unsafe generation" \
    "$ADAPTER_ROOT/research/atoms/L03/A15/evidence/runs/20260712-s2-provider-closure-r1/tests/run_regression.sh" || FAILED=1
run_gate R19 S5 host_target_tested "AOSP ErrorCodeString semantics and sole libziparchive ownership" \
    "$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/tests/run_error_code_string_regression.sh" || FAILED=1
run_gate R20 ALL reproducibility_guard "canonical five-stage contract remained byte-identical during run" \
    python3 "$SCRIPT_DIR/freeze_bionic_musl_contract.py" \
        --project-root "$PROJECT_ROOT" \
        --compare "$OUT/CONTRACT_INPUTS.json" || FAILED=1

record_not_proven P01 S2 \
    "current product initial closure rejects: recursive providers/prepare order/pre-prepare slot5 remain unproven"
record_not_proven P02 S2 \
    "same-generation artifacts are STALE_BY_DESIGN after cfg/provider ownership changes; recursive real libziparchive closure and refresh/rebuild remain deferred"
record_not_proven P03 S3 \
    "namespace-scoped pthread bridge and first-start-routine READY path are not implemented"
record_not_proven P04 S4 \
    "typed OH/Musl callback guard and signal ownership bridge are not implemented"
record_not_proven P05 S5 \
    "product nonzero guard publisher, complete six-entry target coverage and production-init Enforcing evidence do not exist; standalone device fixture is not product activation"
record_not_proven P06 S1 \
    "host sealed transport/namespace tests do not prove product native-certificate registry, same-FD loader API, generation binding or target provider closure"
record_not_proven P07 S5 \
    "standalone aperture fixture executed on 5EAB5, but does not prove a real issuer, appspawn callsite, all six guest-entry classes, product activation, Unity load or first frame"

python3 "$SCRIPT_DIR/write_bionic_musl_regression_report.py" \
    --project-root "$PROJECT_ROOT" \
    --run-dir "$OUT" \
    --results "$RESULTS"

if [[ $FAILED -ne 0 ]]; then
    echo "FAIL Bionic/Musl host-static regression; product status remains NOT_PROVEN" >&2
    exit 1
fi

echo "PASS Bionic/Musl host-static regression; product five-stage status=NOT_PROVEN device_used=false"
