#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CROSS=$ROOT/build/inner/cross_compile_arm64.sh
MINIKIN=$ROOT/build/inner/cross_compile_minikin_stack_arm64.sh
EXTRAS=$ROOT/build/inner/cross_compile_extras_arm64.sh
BACKEND=$ROOT/build/compile_app_native_loader_arm64.sh
BRIDGE=$ROOT/build/inner/compile_oh_adapter_bridge_arm64.sh
RUNTIME=$ROOT/build/inner/compile_oh_android_runtime_arm64_stage2unity.sh
APPSPAWN=$ROOT/build/inner/compile_appspawnx.sh
PUBLIC_APPSPAWN=$ROOT/build/build_appspawn_x.sh
ORCHESTRATOR=$ROOT/build/build_l03_a12_arm64_generation.sh
WRITER=$ROOT/scripts/write_l03_a12_provider_manifest.py
INPUT_GATE=$ROOT/scripts/verify_l03_a12_input_manifest.py
TREE_GATE=$ROOT/scripts/verify_l03_a12_tree_identity.py
SHA_WRITER=$ROOT/scripts/write_l03_a12_sha_manifest.py
VERIFIER=$ROOT/scripts/verify_l03_a12_provider_closure.sh
DEPLOY_VERIFIER=$ROOT/scripts/verify_l03_a12_deploy_closure.py
LIBCXX_COMPAT=$ROOT/framework/appspawn-x/bionic_compat/include/libcxx_compat.h

for script in "$BACKEND" "$CROSS" "$MINIKIN" "$EXTRAS" "$BRIDGE" "$RUNTIME" "$APPSPAWN" "$PUBLIC_APPSPAWN" \
              "$ORCHESTRATOR" "$VERIFIER"; do
    bash -n "$script"
done
python3 -m py_compile "$WRITER" "$INPUT_GATE" "$TREE_GATE" \
    "$SHA_WRITER" "$DEPLOY_VERIFIER"

# Profile-B provider and strict ARM64 producers.
rg -q 'O="\$\{AOSP_OUT_DIR:-' "$CROSS"
rg -q 'OBJ_ROOT="\$\{AOSP_OBJ_DIR:-' "$CROSS"
rg -q -- '-Wl,-z,defs' "$CROSS"
rg -q 'L03_A12_CXX' "$CROSS"
rg -q 'L03_A12_READELF' "$CROSS"
rg -q 'L03_A12_BUILTINS' "$CROSS"
rg -q 'framework/native-loader-oh/src/native_loader.cpp' "$CROSS"
rg -q 'framework/native-loader-oh/src/system_loader.cpp' "$CROSS"
rg -q 'framework/native-loader-oh/native_loader.map' "$CROSS"
rg -q -- '-Wl,--no-as-needed -lapp_native_loader' "$CROSS"
rg -q '\[ "\$N" = "base" \].*EXTRA_LIBS="-llog -lbionic_compat"' "$CROSS"
rg -q '\[ "\$N" = "cutils" \].*EXTRA_LIBS="-llog -lbase -lbionic_compat"' "$CROSS"
rg -q 'system/core/libcutils/trace-dev[.]cpp' "$CROSS"
rg -q '\[ "\$N" = "utils" \].*EXTRA_LIBS="-lcutils -llog -lbionic_compat"' "$CROSS"
rg -q 'generate_operator_out' "$CROSS"
rg -q '^bld art-compiler ' "$CROSS"
rg -q 'missing AOSP14 ART compiler source' "$CROSS"
rg -q '^optimizing/instruction_simplifier_shared[.]cc$' "$CROSS"
rg -q '^optimizing/nodes_shared[.]cc$' "$CROSS"
rg -q 'ARTBASE_OPERATOR_SRC' "$CROSS"
rg -q 'DEXFILE_OPERATOR_SRC' "$CROSS"
rg -q 'ART_OPERATOR_SRC' "$CROSS"
rg -q '^bld lzma ' "$CROSS"
rg -q '\[ "\$N" = "dexfile" \].*-lartpalette' "$CROSS"
rg -q '\[ "\$N" = "elffile" \].*-llzma' "$CROSS"
rg -q 'musl_tgkill_compat[.]h' "$CROSS"
rg -q 'external/fmtlib/src/format[.]cc' "$CROSS"
rg -q 'arch/riscv64/instruction_set_features_riscv64[.]cc' "$CROSS"
rg -q 'arch/x86/instruction_set_features_x86[.]cc' "$CROSS"
rg -q 'signbit\(long double x\)' "$LIBCXX_COMPAT"
rg -q 'isfinite\(long double x\)' "$LIBCXX_COMPAT"
rg -q 'isinf\(long double x\)' "$LIBCXX_COMPAT"
rg -q '\[ "\$N" = "unwindstack" \].*-llzma' "$CROSS"
if rg -q -- '-not -name "ThreadUnwinder[.]cpp"' "$CROSS"; then
    echo "ARM64 ThreadUnwinder is still replaced by a width-incompatible stub" >&2
    exit 1
fi
if rg -q '^bld icu_jni ' "$CROSS"; then
    echo "ICU JNI still runs before its ICU providers" >&2
    exit 1
fi
if sed -n '/L03.A12 Profile B:/,/bld profile/p' "$CROSS" \
    | rg -q '\$A/art/libnativeloader/.*\.(cpp|cc)'; then
    echo "dirty AOSP libnativeloader source leaked into Profile-B build" >&2
    exit 1
fi

rg -q 'BRIDGE_OBJ_DIR' "$BRIDGE"
rg -q 'ADAPTER_OUT_DIR' "$BRIDGE"
rg -q 'AOSP_LIB_DIR' "$BRIDGE"
rg -q 'strict generation link failed; relaxed fallback is forbidden' "$BRIDGE"
rg -q -- '-Wl,-z,defs' "$BRIDGE"
rg -q -- '-Wl,--build-id=sha1' "$BRIDGE"
rg -q -- '-Wl,-soname,liboh_adapter_bridge.so' "$BRIDGE"
rg -q 'L03_A12_READELF' "$BRIDGE"
rg -q -- '-lskia_canvaskit[.]z' "$BRIDGE"
rg -q -- '-lwmutil[.]z' "$BRIDGE"
rg -q -- '-lwmutil_base[.]z' "$BRIDGE"
rg -q -- '-leventhandler[.]z' "$BRIDGE"
rg -q -- '-lhitrace_ndk[.]z' "$BRIDGE"
rg -q 'base/notification/eventhandler/interfaces/inner_api' "$BRIDGE"
if sed -n '/INCS_OH_PLATFORM=/,/^"$/p' "$BRIDGE" \
    | rg -q 'graphic_2d/rosen/modules/platform/eventhandler'; then
    echo "bridge still prioritizes graphic_2d private EventRunner ABI" >&2
    exit 1
fi
if rg -q '/usr/bin/readelf' "$BRIDGE"; then
    echo "bridge still hard-codes host readelf" >&2
    exit 1
fi

rg -q 'ADAPTER_OUT_DIR' "$RUNTIME"
rg -q 'L03_A12_AIDL' "$RUNTIME"
rg -q 'L03_A12_NM' "$RUNTIME"
rg -q -- '-Wl,--no-as-needed -lnativeloader' "$RUNTIME"
rg -q 'CreateClassLoaderNamespace' "$RUNTIME"
rg -q -- '-Wl,--no-as-needed -lnativehelper' "$RUNTIME"
rg -q 'APPSPAWN_TARGET_ARCH' "$APPSPAWN"
rg -q 'aarch64-linux-ohos' "$APPSPAWN"
rg -q 'L03_A12_BUILTINS' "$APPSPAWN"
rg -q -- '-Wl,-z,defs' "$APPSPAWN"
rg -q -- '-Wl,--build-id=sha1' "$BACKEND"
rg -q 'MINIKIN_OBJ_DIR' "$MINIKIN"
rg -q 'STRICT_MINIKIN_PASS' "$MINIKIN"
rg -q -- '-Wl,-z,defs' "$MINIKIN"
rg -q 'EXTRAS_OBJ_DIR' "$EXTRAS"
rg -q 'STRICT_EXTRAS_PASS' "$EXTRAS"
rg -q 'libcrypto.so' "$EXTRAS"
rg -q 'libicu_jni.so' "$EXTRAS"
rg -q 'libopenjdk.so' "$EXTRAS"
sed -n '/echo "=== libjavacore[.]so ==="/,/echo "=== libopenjdkjvm[.]so ==="/p' "$EXTRAS" \
    | rg -q -- '-I\$AOSP/external/zlib'
for isa in arm arm64 riscv64 x86 x86_64; do
    sed -n '/echo "=== libopenjdkjvm[.]so ==="/,/echo "=== libopenjdk[.]so ==="/p' "$EXTRAS" \
        | rg -q -- "-DART_STACK_OVERFLOW_GAP_${isa}=8192"
done
if rg -q '/tmp/cc100/musl_socket_fix[.]h' "$EXTRAS"; then
    echo "extras still consumes ambient socket compat input" >&2
    exit 1
fi

# v3 manifest/gates: bridge + immutable base + independent deploy plan.
rg -q 'westlake\.l03_a12\.provider_closure\.v3' "$WRITER"
rg -q '"bridge": "adapter/liboh_adapter_bridge.so"' "$WRITER"
rg -q -- '--immutable-base-root' "$WRITER"
rg -q -- '--external-source-manifest' "$WRITER"
rg -q -- '--generated-input-manifest' "$WRITER"
rg -q 'westlake\.l03_a12\.deploy_plan\.v1' "$WRITER"
rg -q 'PROVENANCE_PATHS' "$WRITER"
rg -q 'provenance_files' "$WRITER"
rg -q 'westlake\.l03_a12\.provider_closure\.v3' "$VERIFIER"
rg -q '^PROFILE_B_SYMBOLS=' "$VERIFIER"
rg -q 'PROVIDER_SUBGRAPH_PASS' "$VERIFIER"
rg -q 'verify_l03_a12_deploy_closure.py' "$VERIFIER"
rg -q 'DEPLOY_CLOSURE_PASS' "$DEPLOY_VERIFIER"
rg -q 'payload\+immutable_base' "$DEPLOY_VERIFIER"
rg -q 'provenance_stable' "$VERIFIER"
if rg -q '^CPP_SYMBOLS=' "$VERIFIER"; then
    echo "old Profile-A symbol contract remains active" >&2
    exit 1
fi

# Orchestrator must own the entire generation and provenance closure.
rg -q 'WESTLAKE_DIAGNOSTIC_LEGACY_SHARED_OUT' "$PUBLIC_APPSPAWN"
rg -q 'build_l03_a12_arm64_generation[.]sh' "$PUBLIC_APPSPAWN"
rg -q 'not GroundTruth, ROM, deploy, or acceptance eligible' "$PUBLIC_APPSPAWN"
rg -q 'L03_A12_GENERATION_ROOT' "$ORCHESTRATOR"
rg -q 'generation root already exists; refusing reuse' "$ORCHESTRATOR"
rg -q 'L03_A12_BUILD_LOCK' "$ORCHESTRATOR"
rg -q 'FILESYSTEM_TYPE.*findmnt' "$ORCHESTRATOR"
rg -q 'FILESYSTEM_TYPE" = ext4' "$ORCHESTRATOR"
rg -q 'flock -n 9' "$ORCHESTRATOR"
rg -q 'L03_A12_EXTERNAL_SOURCE_MANIFEST' "$ORCHESTRATOR"
rg -q 'L03_A12_IMMUTABLE_BASE_MANIFEST' "$ORCHESTRATOR"
rg -q 'L03_A12_DEPLOY_PLAN' "$ORCHESTRATOR"
rg -q 'all_input_coverage_before' "$ORCHESTRATOR"
rg -q 'all_input_coverage_after' "$ORCHESTRATOR"
rg -q 'immutable_base_identity_after' "$ORCHESTRATOR"
rg -q 'generated_input_manifest' "$ORCHESTRATOR"
rg -q 'provenance_snapshot' "$ORCHESTRATOR"
rg -q 'meta/inputs' "$ORCHESTRATOR"
rg -q 'work/aosp' "$ORCHESTRATOR"
rg -q 'work/adapter' "$ORCHESTRATOR"
rg -q 'payload/aosp' "$ORCHESTRATOR"
rg -q 'payload/adapter' "$ORCHESTRATOR"
rg -q 'L03_A12_STRICT_BUILD=1' "$ORCHESTRATOR"
rg -q 'libc++ include tree must belong to the selected OH toolchain' "$ORCHESTRATOR"
rg -q 'libc++ include tree lacks a regular target __config_site' "$ORCHESTRATOR"
rg -q 'run_phase art64_pair verify_art64_pair' "$ORCHESTRATOR"
rg -q 'libart-compiler[.]so' "$ORCHESTRATOR"
rg -q '\$ROOT/build/inner/oh_adapter_bridge\.ninja\.template' "$ORCHESTRATOR"
rg -q 'run_phase adapter_bridge' "$ORCHESTRATOR"
rg -q 'run_phase aosp_icu_androidfw' "$ORCHESTRATOR"
rg -q 'run_phase aosp_jni_extras' "$ORCHESTRATOR"
rg -q 'work/adapter/liboh_adapter_bridge.so' "$ORCHESTRATOR"
rg -q 'elf_build_id' "$ORCHESTRATOR"
rg -q 'deploy_destination adapter/liboh_adapter_bridge.so' "$ORCHESTRATOR"
rg -q 'deploy_destination adapter/liboh_android_runtime.so' "$ORCHESTRATOR"
for identity in \
    WLAR_ADAPTER_BRIDGE_PATH \
    WLAR_ADAPTER_BRIDGE_SHA256_HEX \
    WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX \
    WLAR_ANDROID_RUNTIME_PATH \
    WLAR_ANDROID_RUNTIME_SHA256_HEX \
    WLAR_ANDROID_RUNTIME_BUILD_ID_HEX; do
    rg -q "$identity" "$ORCHESTRATOR"
done
rg -q 'PROVIDER_SUBGRAPH_PASS' "$ORCHESTRATOR"
rg -q 'DEPLOY_CLOSURE_PASS' "$ORCHESTRATOR"
if rg -q 'L03_A12_BRIDGE_INPUT' "$ORCHESTRATOR"; then
    echo "prebuilt bridge input leaked back into the generation" >&2
    exit 1
fi
if rg -n '(^|[[:space:]])(hdc|adb|ssh|scp)([[:space:]]|$)|deploy/' "$ORCHESTRATOR"; then
    echo "device, remote, or deploy action leaked into generation orchestrator" >&2
    exit 1
fi

echo "L03.A12 Profile-B v3 generation wiring static gates: PASS"
