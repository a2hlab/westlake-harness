#!/usr/bin/env python3
"""Fail-closed source ownership gate for the final Route A path."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[5]
PLUGIN = Path(__file__).resolve().parent


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def legacy_child_fails_closed(source: str) -> bool:
    if "westlake_native_compat_prepare_main_thread" in source:
        return False
    entry = source[source.index("void ChildMain::run("):]
    return ("_exit(125);" in entry and
            entry.index("_exit(125);") < entry.index("applyAccessToken(msg)"))


def legacy_parent_art_target_disabled(build_gn: str, parent_main: str) -> bool:
    return ('ohos_executable("appspawn-x")' not in build_gn and
            '":appspawn-x"' not in build_gn and
            'group("appspawn_x_legacy_parent_art_disabled")' in build_gn and
            'WESTLAKE_LEGACY_PARENT_ART_TEST_ONLY' in parent_main and
            '#error "Route A forbids the legacy parent-ART appspawn-x main' in
            parent_main)


def class_loader_reinjection_fails_closed(source: str) -> bool:
    if ("bool ReinjectAdapterClassLoader" not in source or
            "if (!ReinjectAdapterClassLoader(env, runtime))" not in source or
            "_exit(21);" not in source):
        return False
    entry = source[source.index("void ChildMain::runAfterStockSpecialization("):]
    reinject = entry.index("if (!ReinjectAdapterClassLoader(env, runtime))")
    failure_exit = entry.index("_exit(21);", reinject)
    launch = entry.index("LaunchActivityThreadAfterStock", reinject)
    return reinject < failure_exit < launch


def fresh_child_vm_avoids_unpaired_zygote_hooks(source: str) -> bool:
    entry = source[source.index(
        "void ChildMain::runAfterStockSpecialization("):]
    return ("zygotePostForkChild" not in entry and
            "zygotePostForkCommon" not in entry and
            "fresh child VM requires no zygote post-fork hooks" in entry and
            entry.index("runtime->onChildInit()") <
            entry.index("LaunchActivityThreadAfterStock"))


def specialized_child_vm_uses_non_zygote_mode(runtime: str,
                                               provider: str) -> bool:
    legacy = runtime[runtime.index("int AppSpawnXRuntime::startVm()"):
                     runtime.index("int AppSpawnXRuntime::startVm(bool")]
    explicit = runtime[runtime.index("int AppSpawnXRuntime::startVm(bool"):
                       runtime.index("// Previously forced interpreter mode")]
    create = provider[provider.index("int CreateChildVm"):
                      provider.index("int CompleteChildJni")]
    return ("return startVm(true);" in legacy and
            "if (zygoteMode)" in explicit and
            'makeOption("-Xzygote")' in explicit and
            "specialized-child VM uses non-zygote runtime mode" in explicit and
            "context->runtime->startVm(false)" in create)


def graphics_child_marker_uses_exact_loaded_group(source: str) -> bool:
    marker = source[source.index("void MarkGraphicsChild()"):
                    source.index("int InitAdapterLayerAfterStock")]
    return ('"/system/android/lib64/libhwui.so"' in marker and
            "RTLD_NOW | RTLD_NOLOAD" in marker and
            'dlsym(hwui, "oh_typeface_mark_child")' in marker and
            "dlsym(RTLD_DEFAULT" not in marker)


def typeface_warmup_override_is_narrow_and_ordered(source: str) -> bool:
    override = source[source.index("bool InstallTypefaceWarmUpOverride"):
                      source.index("int InitAdapterLayerAfterStock")]
    entry = source[source.index(
        "void ChildMain::runAfterStockSpecialization(") :]
    return ('"nativeWarmUpCache"' in override and
            '"(Ljava/lang/String;)V"' in override and
            "env->RegisterNatives(typeface, &method, 1)" in override and
            "if (rc != JNI_OK || env->ExceptionCheck())" in override and
            entry.index("runtime->onChildInit()") <
            entry.index("InstallTypefaceWarmUpOverride(env)") <
            entry.index("InitAdapterLayerAfterStock(env, runtime)"))


def host_services_contract_fails_closed(provider: str, registry: str) -> bool:
    provider_required = (
        "int WLAR_GetRuntimeIdentity(",
        "WLAR_HostServicesInstall(&gHostServicesRegistry",
        "ProviderGeneration(), kProviderGenerationSha, services",
        "gState != ProviderState::READY",
        "gState = ProviderState::CHILD_ENTERING",
        "WLAR_HostServicesBeginChild(&gHostServicesRegistry)",
        "WLAR_HostServicesPrepareMain(",
        "WLAR_HostServicesGetAuditSnapshot(",
        "WLAR_HostServicesMarkChildConsumed(",
        "gState != ProviderState::CHILD_ENTERING",
    )
    registry_required = (
        "services == NULL",
        "services->abi_version != WLASC_HOST_SERVICES_ABI_VERSION",
        "services->struct_size != sizeof(*services)",
        "services->runtime_generation != expected_generation",
        "memcmp(services->runtime_provider_sha256",
        "services->current_thread_token == NULL",
        "services->prepare_parent_runtime == NULL",
        "services->verify_parent_preload_thread_ready == NULL",
        "services->prepare_main_thread == NULL",
        "services->verify_current_thread_ready == NULL",
        "services->get_audit_snapshot == NULL",
        "registry->services = *services",
        "WLAR_HOST_SERVICES_CALLBACK_ACTIVE",
        "IdentityValid(registry, identity)",
        "identity->runtime_generation ==",
        "identity->child_stage_tail_reached == UINT32_C(1)",
        "WLAR_HOST_SERVICES_VERIFY_SLOTS == WLTG_MAX_THREAD_RECORDS",
        "AcquireVerifyToken",
        "ReleaseVerifyToken",
    )
    return (all(item in provider for item in provider_required) and
            all(item in registry for item in registry_required))


def exact_plugin_install_fails_closed(source: str, identity: str) -> bool:
    host_required = (
        "WLASC_PLUGIN_ELF_SHA256_HEX",
        "WLEI_VerifyFileHex(",
        "dlopen(plugin_path, RTLD_NOW | RTLD_NOLOAD)",
        "WLEI_VerifyLoadedSymbolHex(",
        "contract->request_size",
        "services.plugin_elf_sha256",
        "services.plugin_build_id",
    )
    identity_required = (
        "VerifyBuildId(descriptor, &status, expected_machine",
        "realpath(expected_absolute_path, resolved_path)",
        "strcmp(resolved_path, expected_absolute_path) != 0",
        "dladdr(symbol, &information)",
        "strcmp(symbol_path, file_path) != 0",
    )
    if (not all(item in source for item in host_required) or
            not all(item in identity for item in identity_required)):
        return False
    main = source[source.index("int main("):]
    first_sha = main.index("VerifyPluginFileSha256(plugin_path)")
    module = main.index("AppSpawnModuleMgrInstall(WLASC_PLUGIN_NAME)")
    second_sha = main.index("VerifyPluginFileSha256(plugin_path_after_load)")
    exact_handle = main.index("dlopen(plugin_path, RTLD_NOW | RTLD_NOLOAD)")
    typed_install = main.index(
        "InstallPluginHostServices(plugin_handle, plugin_path)")
    start = main.index("StartSpawnService(&start_argument")
    return (first_sha < module < second_sha < exact_handle < typed_install <
            start)


def stock_host_table_fails_closed(source: str) -> bool:
    required = (
        "WLASC_InstallStockHostServicesV1(",
        "WLASC_STOCK_SERVICES_INSTALLING",
        "StockServicesValid(services)",
        "services->abi_version == WLASC_STOCK_HOST_SERVICES_ABI_VERSION",
        "services->struct_size == sizeof(*services)",
        "services->runtime_generation ==",
        "services->runtime_provider_sha256",
        "services->plugin_generation_sha256",
        "services->plugin_elf_sha256",
        "services->plugin_build_id",
        "services->add_server_stage_hook != 0",
        "services->add_app_spawn_hook != 0",
        "services->get_app_spawn_msg_info != 0",
        "services->check_app_spawn_msg_flag != 0",
        "services->reg_child_looper != 0",
        "services->clear_child_environment != 0",
        "g_stock_host_services = *services",
        "WestlakeServerPrepareInert",
        "ImmutableGenerationReady()",
        "WLASC_STOCK_SERVICES_INSTALLED",
    )
    return all(item in source for item in required)


def generation_identity_producer_fails_closed(source: str,
                                              header: str) -> bool:
    source_required = (
        "WlgrIpBuild(", "WlgrIpValidate(", "WlgrIpGetIdentity(",
        "wlgr_v2_runtime_key_valid", "wlgr_v2_identity_valid",
        "ReadCurrentProcess(ops, &pid, &start) != 0",
        "InputDigest(&candidate, digest) != 0",
        "DigestEqual(producer)",
        "wlgr_v2_identity_equal(&producer->identity, &candidate)",
        "WLGR_IP_REPLAY_CONFLICT", "WLGR_IP_TAMPERED",
    )
    header_required = (
        "typedef struct WlgrIpSourceFacts", "typedef struct WlgrIpOps",
        "typedef struct WlgrIpProducer", "WlgrIpBuild(",
        "WlgrIpValidate(", "WlgrIpGetIdentity(",
        "westlake_generation_identity_v2",
    )
    return all(item in source for item in source_required) and all(
        item in header for item in header_required)


def production_generation_bundle_fails_closed(
    facts: str,
    facts_header: str,
    ops: str,
    ops_header: str,
    generator: str,
    target_build: str,
    route_build: str,
    host_tests: str,
    integration_test: str,
) -> bool:
    context_fields = (
        "const WlgrIfChildRequest *child_request",
        "const WlascStockStageReceiptV1 *stock_receipt",
        "const WlgrIfGenerationMetadata *sealed_metadata",
        "const WlgrIfHookContract *published_hook",
        "const WlscplManifestV2 *build_manifest",
    )
    callback_assignments = (
        "ops->read_boot_id = WlgrIfProductionReadBootId",
        "ops->read_process = WlgrIfProductionReadProcess",
        "ops->read_metadata = WlgrIfProductionReadMetadata",
        "ops->read_receipt = WlgrIfProductionReadReceipt",
        "ops->read_manifest = WlgrIfProductionReadManifest",
        "ops->read_hook = WlgrIfProductionReadHook",
        "ops->random_bytes = WlgrIfProductionRandom",
    )
    receipt_binding = (
        "WlgrIfSerializeStockReceipt(",
        "PutLe32(out + offset",
        "PutLe64(out + offset",
        "WlgrIfDigestStockReceipt(production->stock_receipt",
        "out->stock_receipt_digest",
        "receipt.stock_receipt_digest",
        "out->specialization_receipt_digest",
    )
    generator_fields = (
        "--artifact-generation-digest",
        "--manifest-digest",
        "--manifest-source",
        "--hook-digest",
        "--policy-epoch",
        "--policy-provenance-digest",
        "--launch-generation",
        "--boot-id",
        "--output-c",
        "whole-generation composite digest must be distinct",
        "manifest source and --manifest-digest are mixed-generation",
        "manifest deployment paths do not name the whole-generation digest",
        "struct.pack(\"<QII\"",
        "struct.pack(\"<QQ\"",
        "WlgrIfGetBuildGeneratedMetadata",
    )
    target_wiring = (
        "generate_generation_metadata.py",
        "--artifact-generation-digest \"$GENERATION_SHA\"",
        "--manifest-source \"$dir/sealed_provider_manifest.c\"",
        "--policy-provenance-digest \"$POLICY_PROVENANCE_DIGEST\"",
        "generated_generation_metadata.c",
        "generated_generation_metadata.o",
    )
    integration = (
        "WlgrIfGetBuildGeneratedMetadata()",
        "WLSCPL_GetBuildGeneratedManifest()",
        "WLASC_ReceiptConsume(",
        "WlgrIfProductionContextInit(",
        "WlgrIfProductionOps(",
        "WlgrIfAcquire(",
        "WlgrIpBuild(",
        "WlgrIpValidate(",
        "PRODUCTION_BUNDLE_PASS acquire=1 build=1 live_proc=1",
    )
    forbidden_integration = (
        "const WlscplManifestV2 *WLSCPL_GetBuildGeneratedManifest(",
        "ssize_t getrandom(",
    )
    return (
        all(item in ops_header for item in context_fields) and
        all(item in ops for item in callback_assignments) and
        all(item in facts + ops for item in receipt_binding) and
        all(item in generator for item in generator_fields) and
        all(item in target_build for item in target_wiring) and
        "build_target_in_container.sh" in route_build and
        "run_product_bundle_gate" in host_tests and
        "WLGR_LINUX_BUNDLE_ONLY" in host_tests and
        "/proc/sys/kernel/random/boot_id" in host_tests and
        "-fsanitize=address,undefined" in host_tests and
        all(item in integration_test for item in integration) and
        not any(item in integration_test for item in forbidden_integration) and
        not re.search(r"policy_epoch\s*=\s*(?:UINT64_C\()?1\)?\s*;",
                      ops) and
        "production->build_manifest" in ops and
        "WLSCPL_GetBuildGeneratedManifest()" in ops and
        "policy_provenance_digest" in facts_header and
        "stock_receipt_digest" in facts_header
    )


def build_id_policy_fails_closed(source: str) -> bool:
    start = source.find("static int ManifestShapeValid(")
    end = source.find("static int DigestBytes(", start)
    if start < 0 or end < 0:
        return False
    manifest_shape = source[start:end]
    exact_32_or_40_and_nonzero = re.compile(
        r"\(\(\s*!ExactLowerHex\(\s*artifact->build_id_hex\s*,\s*40U\s*\)"
        r"\s*&&\s*!ExactLowerHex\(\s*artifact->build_id_hex\s*,\s*32U\s*\)"
        r"\s*\)\s*\|\|\s*!HexHasNonzeroDigit\(\s*artifact->build_id_hex\s*,"
        r"\s*BoundedLength\(\s*artifact->build_id_hex\s*,"
        r"\s*WLSCPL_BUILD_ID_HEX_SIZE\s*\)\s*\)\s*\)",
        re.DOTALL,
    )
    return exact_32_or_40_and_nonzero.search(manifest_shape) is not None


def sealed_child_loader_fails_closed(source: str, header: str) -> bool:
    required_source = (
        "WLSCPL_ERROR_NOT_SPECIALIZED_CHILD",
        "request->specialization_complete != UINT32_C(1)",
        "request->parent_pid == request->generation_identity->child_pid",
        "ops->current_pid(ops->context) !=",
        "WLSCPL_ERROR_HOOK_TABLE_NOT_READY",
        "request->hook_table_ready != UINT32_C(1)",
        "WLSCPL_ERROR_SEAL_NOT_VERIFIED",
        "ManifestShapeValid(request->manifest)",
        "wlgr_v2_identity_valid(request->generation_identity)",
        "request->generation_identity->artifact_manifest_digest",
        "request->manifest->manifest_digest",
        "ComputeManifestDigest(request->manifest",
        "computed_manifest_digest",
        "AbsoluteCanonicalForm(artifact->absolute_path)",
        "ExactLowerHex(artifact->sha256_hex, 64U)",
        "HexHasNonzeroDigit(artifact->sha256_hex, 64U)",
        "VisitClosure(request->manifest",
        "order_count != request->manifest->artifact_count",
        "ops->verify_identity(ops->context, artifact",
        "WLSCPL_ARTIFACT_OH_SYSTEM_ROOT",
        "ops->mapping_state(ops->context, artifact",
        "require_bound_inode == 0 && !basename_matches",
        "inode_value == (unsigned long long)verified->inode",
        "RTLD_NOW | RTLD_LOCAL",
        "ops->open_verified_local_now(",
        "PrepareSealedNamespace(",
        "WLSCPL_SEALED_NAMESPACE",
        "CREATE_INHERIT_DEFAULT",
        "WLSCPL_OpenPreparedNamespace(",
        "dlopen(absolute_path, flags)",
        "if (ops->mapped_identity_matches(",
        "WLSCPL_MUTANT_SKIP_MAPPED_INODE_BIND",
        "WLSCPL_ERROR_DLOPEN",
        "WLSCPL_ERROR_MAPPED_IDENTITY",
        "WLSCPL_STATE_FAILED_AFTER_CONSTRUCTORS",
        "WLSCPL_CONSTRUCTORS_COMPLETE_BEFORE_DLOPEN_RETURN",
        "__atomic_compare_exchange_n(&loader->state",
    )
    required_header = (
        "WLSCPL_PROVIDER_SONAME",
        "WLSCPL_MAX_ARTIFACTS",
        "WLSCPL_MAX_NEEDED",
        "WLSCPL_LoadSealedProvider(",
        "generation_seal_verified",
        "hook_table_ready",
        "specialization_complete",
        "westlake_generation_identity_v2",
        "manifest_digest",
        "constructor_completed_count",
    )
    forbidden = (
        "RTLD_NOW | RTLD_GLOBAL",
        "RTLD_DEFAULT",
        "RTLD_NEXT",
        "LD_LIBRARY_PATH",
        "dlmopen(",
        "dlopen(descriptor_path",
        "LOCAL_NS_PREFERED",
        "system(",
        "popen(",
        "dlclose(",
    )
    return (all(item in source for item in required_source) and
            all(item in header for item in required_header) and
            build_id_policy_fails_closed(source) and
            not any(item in source for item in forbidden))


def child_hook_table_fails_closed(source: str, header: str) -> bool:
    required_source = (
        "WESTLAKE_CHILD_HOOK_MANDATORY_BITMAP",
        "WESTLAKE_CHILD_HOOK_INSTALL_RACE",
        "WESTLAKE_CHILD_HOOK_GENERATION_STALE",
        "WESTLAKE_CHILD_HOOK_CAPACITY_EXHAUSTED",
        "WESTLAKE_CHILD_HOOK_DRAIN_TIMEOUT",
        "WESTLAKE_CHILD_HOOK_INVALIDATE_TIMEOUT",
        "__atomic_compare_exchange_n",
        "__atomic_store_n",
        "WESTLAKE_CHILD_HOOK_REVOKING",
        "WESTLAKE_CHILD_HOOK_DRAINING",
        "WESTLAKE_CHILD_HOOK_INVALID",
    )
    required_header = (
        "WESTLAKE_CHILD_HOOK_TABLE_V1_CAPABILITY_COUNT UINT32_C(10)",
        "WESTLAKE_CHILD_HOOK_TABLE_V1_GENERATION_DIGEST_SIZE UINT32_C(32)",
        "westlake_child_hook_table_v1_begin_install(",
        "westlake_child_hook_table_v1_publish(",
        "westlake_child_hook_table_v1_admit(",
        "westlake_child_hook_table_v1_release(",
        "westlake_child_hook_table_v1_revoke(",
        "westlake_child_hook_table_v1_drain(",
        "westlake_child_hook_table_v1_invalidate(",
    )
    return (all(item in source for item in required_source) and
            all(item in header for item in required_header))


def route_a_zlib_fails_closed(build: str) -> bool:
    return (
        "OH_ZLIB=$ROOT/upstream/openharmony-6.1.0.31/third_party/zlib"
        in build and
        "build_route_a_zlib pass1" in build and
        "build_route_a_zlib pass2" in build and
        'cmp "$OUT/pass1/zlib/libshared_libz.z.so"' in build and
        "verify_route_a_zlib_abi" in build and
        "-Wl,--build-id=sha1" in build and
        'cp "$OUT/libshared_libz.z.so" "$OUT/providers/"' in build and
        'cp "$V12_DEPS/libshared_libz.z.so" "$OUT/providers/"' not in build and
        'cmp "$OUT/logs/$prefix.reference.exports.txt"' in build and
        'cmp "$OUT/logs/$prefix.reference.dynamic.txt"' in build
    )


def route_a_container_mounts_fail_closed(run_all: str) -> bool:
    return (
        '[[ -n ${WESTLAKE_GENERATION_ROOT:-} ]]' in run_all and
        "HOST_GENERATION_ROOT=$(cd "
        '"$WESTLAKE_GENERATION_ROOT" && pwd -P)' in run_all and
        "HOST_LOGICAL_GENERATION_ROOT="
        "$PROJECT_ROOT/.work/product-tls-generation" in run_all and
        "CONTAINER_LOGICAL_GENERATION_ROOT="
        "/.work/product-tls-generation" in run_all and
        '-v "$PROJECT_ROOT:/project:ro" \\\n'
        '    "${DOCKER_INPUT_ARGS[@]}" \\\n' in run_all and
        '-v "$PROJECT_ROOT:/project:rw" \\\n'
        '    "${DOCKER_INPUT_ARGS[@]}" \\\n' in run_all and
        'test -x "$WESTLAKE_GENERATION_ROOT/frozen/toolchain/bin/clang-15"'
        in run_all and
        "test -f /project/upstream/openharmony-6.1.0.31/"
        "third_party/zlib/BUILD.gn" in run_all and
        "cmp \\\n"
        "            /project/adapter/framework/appspawn-x/security_specialization/"
        "stock_child_plugin/frozen/runtime_provider/libraries/oh/libhilog.so "
        "\\\n"
        "            /.work/product-tls-generation/frozen/libraries/oh/"
        "libhilog.so" in run_all
    )


def dynamic_root_admission_fails_closed(runtime: str, child: str,
                                        identity: str) -> bool:
    runtime_preload = runtime[runtime.index("int AppSpawnXRuntime::preload()"):
                              runtime.index("int AppSpawnXRuntime::verifyApk")]
    child_reinject = child[child.index("bool ReinjectAdapterClassLoader"):]
    required_identity = (
        "WLAR_ADAPTER_BRIDGE_PATH",
        "WLAR_ADAPTER_BRIDGE_SHA256_HEX",
        "WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX",
        "WLAR_ANDROID_RUNTIME_PATH",
        "WLAR_ANDROID_RUNTIME_SHA256_HEX",
        "WLAR_ANDROID_RUNTIME_BUILD_ID_HEX",
        "WLEI_VerifyFileHex(",
        "dlopen(resolvedPath, RTLD_NOW | RTLD_LOCAL)",
        "WLEI_VerifyLoadedSymbolHex(",
        '"adapter_bridge_set_class_loader"',
        '"_ZN7android14AndroidRuntime8startRegEP7_JNIEnv"',
    )
    if ("LoadVerifiedAdapterBridge(&adapterBridgeHandle_)" not in runtime or
            "LoadVerifiedAndroidRuntime(&androidRuntimeHandle_)" not in runtime or
            "VerifyLoadedAdapterBridge(adapterBridgeHandle_)" not in
            runtime_preload or
            "dlsym(bridge" not in runtime_preload or
            "VerifyLoadedAdapterBridge(bridge)" not in child_reinject or
            "dlsym(bridge" not in child_reinject):
        return False
    bridge_admit = runtime.index(
        "LoadVerifiedAdapterBridge(&adapterBridgeHandle_)")
    runtime_admit = runtime.index(
        "LoadVerifiedAndroidRuntime(&androidRuntimeHandle_)")
    start_reg = runtime.index("int rc = startReg(env_)")
    preload_verify = runtime_preload.index(
        "VerifyLoadedAdapterBridge(adapterBridgeHandle_)")
    preload_call = runtime_preload.index("CallStaticVoidMethod")
    return (bridge_admit < runtime_admit < start_reg and
            preload_verify < preload_call and
            'dlopen("liboh_android_runtime.so"' not in runtime and
            'dlopen("liboh_adapter_bridge.so", RTLD_NOW)' not in runtime and
            'dlopen("liboh_adapter_bridge.so", RTLD_NOW)' not in
            child_reinject and
            child_reinject.index("VerifyLoadedAdapterBridge(bridge)") <
            child_reinject.index("dlsym(bridge") and
            all(item in identity for item in required_identity))


def stock_child_reply_precedes_android_runtime(plugin: str) -> bool:
    try:
        helper = plugin[plugin.index("static int CompleteStockChildReply("):
                        plugin.index("static int WestlakeRunAndroidChild(")]
        entry = plugin[plugin.index("static int WestlakeRunAndroidChild("):
                       plugin.index("static int WestlakeServerPrepareInert(")]
        reply_order = (
            entry.index("WLCGATE:RAC:PASS_HOOK_PUBLICATION") <
            entry.index("CompleteStockChildReply(content, client)") <
            entry.index("LoadSealedProviderAfterHooks(&request, &receipt)"))
    except ValueError:
        return False
    required_helper = (
        "property->forkCtx.fd[1] = -1;",
        "g_stock_host_services.clear_child_environment(content, client);",
        "write(reply_fd, &result, sizeof(result))",
        "close(reply_fd)",
        "WLCGATE:RAC:PASS_STOCK_REPLY",
        "_exit(124);",
    )
    return (all(item in helper for item in required_helper) and reply_order and
            "_exit(WlascP0ChildExitFromFailure(load_status));" in entry and
            "_exit(122);" in entry and
            "WLASC_P0_EXIT_PRODUCTION_CONTEXT = 133" in plugin and
            "WLASC_P0_EXIT_ACQUIRE_BASE = 140" in plugin and
            "WLASC_P0_EXIT_LOADER_BASE = 190" in plugin and
            "WLASC_P0_EXIT_PROVIDER_ENTRY = 210" in plugin and
            "WLCGATE:RAC:PASS_SEALED_PROVIDER" not in entry)


def child_identity_producer_starts_empty(plugin: str) -> bool:
    try:
        load = plugin[plugin.index("static int LoadSealedProviderAfterHooks("):
                      plugin.index("static int CompleteStockChildReply(")]
        declaration = load.index("WlgrIpProducer producer;")
        initialize = load.index("ZeroBytes(&producer, sizeof(producer));")
        acquire = load.index("acquire_error = WlgrIfAcquire(")
        build = load.index("build_error = WlgrIpBuild(&producer, &facts, &ip_ops);")
    except ValueError:
        return False
    return declaration < initialize < acquire < build


def live_target_boot_rebind_fails_closed(plugin: str,
                                         target_build: str) -> bool:
    try:
        load = plugin[plugin.index("static int LoadSealedProviderAfterHooks("):
                      plugin.index("static int CompleteStockChildReply(")]
        metadata_copy = load.index(
            "metadata = *WlgrIfGetBuildGeneratedMetadata();")
        read_boot = load.index("WlgrIfProductionReadBootId(")
        parse_boot = load.index("WlgrIfParseBootId(")
        copy_boot = load.index("memcpy(metadata.boot_id, live_boot_id")
        digest = load.index("WlgrIfDigestMetadata(&metadata,")
        validate = load.index("WlgrIfValidateMetadata(&metadata)")
        context = load.index("WlgrIfProductionContextInit(")
    except ValueError:
        return False
    return (
        "BUILD_BOOT_ID=00000000-0000-0000-0000-000000000001" in
        target_build and
        "BUILD_BOOT_ID=$(tr -d" not in target_build and
        "WLCGATE:LSP:PASS_BOOT_REBIND" in load and
        metadata_copy < read_boot < parse_boot < copy_boot < digest <
        validate < context
    )


def full_launch_generation_fails_closed(target_build: str) -> bool:
    return (
        'LAUNCH_GENERATION=$(python3 - "$GENERATION_SHA"' in target_build and
        "print(int(sys.argv[1][:16], 16))" in target_build and
        "$LAUNCH_GENERATION =~ ^[0-9]+$" in target_build and
        "16#${GENERATION_SHA:0:15}" not in target_build
    )


def main() -> int:
    generation_bundle_only = sys.argv[1:] == ["--generation-bundle-only"]
    require(not sys.argv[1:] or generation_bundle_only,
            "unsupported source-gate argument")
    provider = (PLUGIN / "src/westlake_android_runtime_provider.cpp").read_text()
    child = (ROOT / "adapter/framework/appspawn-x/src/child_main_after_stock.cpp").read_text()
    legacy_child = (
        ROOT / "adapter/framework/appspawn-x/src/child_main.cpp"
    ).read_text()
    plugin = (PLUGIN / "src/westlake_android_child_plugin.c").read_text()
    sealed_loader = (
        PLUGIN / "src/sealed_child_provider_loader.c"
    ).read_text()
    sealed_loader_header = (
        PLUGIN / "include/sealed_child_provider_loader.h"
    ).read_text()
    sealed_loader_tests = (
        PLUGIN / "tests/test_sealed_child_provider_loader.c"
    ).read_text()
    child_hook = (PLUGIN / "src/child_hook_table_v1.c").read_text()
    child_hook_header = (
        PLUGIN / "include/westlake_child_hook_table_v1.h"
    ).read_text()
    generation_identity_producer = (
        PLUGIN / "src/westlake_generation_identity_producer.c"
    ).read_text()
    generation_identity_producer_header = (
        PLUGIN / "include/westlake_generation_identity_producer.h"
    ).read_text()
    generation_identity_facts = (
        PLUGIN / "src/westlake_generation_identity_facts.c"
    ).read_text()
    generation_identity_facts_header = (
        PLUGIN / "include/westlake_generation_identity_facts.h"
    ).read_text()
    generation_identity_ops = (
        PLUGIN / "src/westlake_generation_identity_ops.c"
    ).read_text()
    generation_identity_ops_header = (
        PLUGIN / "include/westlake_generation_identity_ops.h"
    ).read_text()
    generation_metadata_generator = (
        PLUGIN / "generate_generation_metadata.py"
    ).read_text()
    route_inputs_generator = (
        PLUGIN / "generate_route_a_inputs.py"
    ).read_text()
    production_bundle_test = (
        PLUGIN / "tests/test_production_bundle.c"
    ).read_text()
    host = (PLUGIN / "src/westlake_stock_host_main.c").read_text()
    host_services = (PLUGIN / "src/host_runtime_services.c").read_text()
    elf_identity = (PLUGIN / "src/westlake_elf_identity.c").read_text()
    bridge_identity = (
        ROOT / "adapter/framework/appspawn-x/src/adapter_bridge_identity.cpp"
    ).read_text()
    runtime = (
        ROOT / "adapter/framework/appspawn-x/src/appspawnx_runtime.cpp"
    ).read_text()
    build = (PLUGIN / "build_route_a_generation_in_container.sh").read_text()
    run_all = (PLUGIN / "run_all.sh").read_text()
    target_build = (PLUGIN / "build_target_in_container.sh").read_text()
    host_tests = (PLUGIN / "run_host_tests.sh").read_text()
    host_map = (PLUGIN / "westlake_stock_host.map").read_text()
    provider_map = (
        PLUGIN / "westlake_android_runtime_provider.map"
    ).read_text()
    app_loader = (
        ROOT / "adapter/framework/app-native-loader/src/app_native_loader.c"
    ).read_text()
    native_system_loader = (
        ROOT / "adapter/framework/native-loader-oh/src/system_loader.cpp"
    ).read_text()
    service = (
        PLUGIN /
        "stock_host_patched/base/startup/appspawn/standard/appspawn_service.c"
    ).read_text()
    legacy_build_gn = (
        ROOT / "adapter/framework/appspawn-x/BUILD.gn"
    ).read_text()
    legacy_parent_main = (
        ROOT / "adapter/framework/appspawn-x/src/main.cpp"
    ).read_text()

    forbidden_calls = re.compile(
        r"\b(?:applySandbox|applySELinux|applyDac|applyAccessToken|"
        r"SetSelfTokenID|HapDomainSetcontext|setprocattrcon_raw|setcon|"
        r"setresuid|setresgid|setgroups|mount|umount2|unshare)\s*\("
    )
    require(not forbidden_calls.search(provider),
            "runtime provider contains a security operation call")
    require(legacy_parent_art_target_disabled(
                legacy_build_gn, legacy_parent_main),
            "competing installable legacy parent-ART topology remains admitted")
    require(not legacy_parent_art_target_disabled(
                legacy_build_gn.replace(
                'group("appspawn_x_legacy_parent_art_disabled")',
                'ohos_executable("appspawn-x")', 1),
                legacy_parent_main),
            "legacy parent-ART build-target mutant survived")
    require(not legacy_parent_art_target_disabled(
                legacy_build_gn,
                legacy_parent_main.replace(
                    'WESTLAKE_LEGACY_PARENT_ART_TEST_ONLY', "mutated", 1)),
            "legacy parent-ART main admission mutant survived")
    require(not forbidden_calls.search(child),
            "post-stock child path contains a security operation call")
    require("ChildMain::runAfterStockSpecialization" in child,
            "post-stock child implementation missing")

    require(generation_identity_producer_fails_closed(
                generation_identity_producer,
                generation_identity_producer_header),
            "generation identity producer V2 source/header is incomplete")
    require("WlgrIfAcquire" in generation_identity_facts and
            "WlgrIfParseBootId" in generation_identity_facts_header and
            "WLGR_IF_NONCE_REPLAY" in generation_identity_facts_header and
            "WlgrIfValidateMetadata" in generation_identity_facts,
            "generation identity facts acquisition source/header is incomplete")
    target_input_block = target_build[
        target_build.index("for input in \\\n"):
        target_build.index("do\n    [[ -f \"$input\" ]]")
    ]
    target_build_pass = target_build[
        target_build.index("build_pass()"):
        target_build.index("build_pass pass1")
    ]
    producer_input_edge = (
        '"$PLUGIN/src/westlake_generation_identity_producer.c" \\'
    )
    producer_compile_edge = (
        'compile "$PLUGIN/src/westlake_generation_identity_producer.c" '
        '"$dir/westlake_generation_identity_producer.o"'
    )
    producer_link_edge = (
        '"$dir/westlake_generation_identity_ops.o" \\\n'
        '        "$dir/westlake_generation_identity_producer.o" \\'
    )
    producer_edges = (
        ("immutable input", target_input_block, producer_input_edge),
        ("compile", target_build_pass, producer_compile_edge),
        ("link", target_build_pass, producer_link_edge),
    )
    def producer_edge_ok(block: str, edge: str) -> bool:
        return block.count(edge) == 1
    for label, block, producer_edge in producer_edges:
        require(producer_edge_ok(block, producer_edge),
                f"generation identity producer {label} edge is absent or ambiguous")
        mutated = block.replace(producer_edge, "removed", 1)
        require(not producer_edge_ok(mutated, producer_edge),
                f"producer {label} edge mutant survived")
    require(production_generation_bundle_fails_closed(
                generation_identity_facts,
                generation_identity_facts_header,
                generation_identity_ops,
                generation_identity_ops_header,
                generation_metadata_generator,
                target_build,
                build,
                host_tests,
                production_bundle_test),
            "production generation facts bundle is hollow or mixed-generation")
    for route_input in (
        'PLUGIN / "generate_generation_metadata.py"',
        'PLUGIN / "include/westlake_generation_identity_facts.h"',
        'PLUGIN / "include/westlake_generation_identity_ops.h"',
        'PLUGIN / "include/westlake_generation_identity_producer.h"',
        'PLUGIN / "src/westlake_generation_identity_facts.c"',
        'PLUGIN / "src/westlake_generation_identity_ops.c"',
        'PLUGIN / "src/westlake_generation_identity_producer.c"',
    ):
        require(route_input in route_inputs_generator,
                f"Route-A input ledger omits target input: {route_input}")
    for bundle_mutant, target in (
        ("ops->read_boot_id = WlgrIfProductionReadBootId", "ops"),
        ("ops->read_process = WlgrIfProductionReadProcess", "ops"),
        ("ops->read_metadata = WlgrIfProductionReadMetadata", "ops"),
        ("ops->read_receipt = WlgrIfProductionReadReceipt", "ops"),
        ("ops->read_manifest = WlgrIfProductionReadManifest", "ops"),
        ("ops->read_hook = WlgrIfProductionReadHook", "ops"),
        ("ops->random_bytes = WlgrIfProductionRandom", "ops"),
        ("out->stock_receipt_digest", "ops"),
        ("receipt.stock_receipt_digest", "facts"),
        ("--artifact-generation-digest \"$GENERATION_SHA\"", "target"),
        ("--policy-provenance-digest \"$POLICY_PROVENANCE_DIGEST\"", "target"),
        ("WlgrIfAcquire(", "test"),
        ("WlgrIpBuild(", "test"),
    ):
        mutated_facts = (generation_identity_facts.replace(
            bundle_mutant, "mutated")
            if target == "facts" else generation_identity_facts)
        mutated_ops = (generation_identity_ops.replace(
            bundle_mutant, "mutated")
            if target == "ops" else generation_identity_ops)
        mutated_target = (target_build.replace(
            bundle_mutant, "mutated")
            if target == "target" else target_build)
        mutated_test = (production_bundle_test.replace(
            bundle_mutant, "mutated")
            if target == "test" else production_bundle_test)
        require(not production_generation_bundle_fails_closed(
                    mutated_facts, generation_identity_facts_header,
                    mutated_ops, generation_identity_ops_header,
                    generation_metadata_generator, mutated_target, build,
                    host_tests, mutated_test),
                f"production facts bundle mutant survived: {bundle_mutant}")
    require(not re.search(
                r"policy_epoch\s*=\s*(?:UINT64_C\()?1\)?\s*;",
                generation_identity_ops),
            "production identity facts retained hardcoded policy epoch")
    require("const WlscplManifestV2 *WLSCPL_GetBuildGeneratedManifest(" not in
            production_bundle_test and
            "ssize_t getrandom(" not in production_bundle_test,
            "production bundle test overrides a production symbol or syscall")
    if generation_bundle_only:
        print("PASS production generation facts bundle source/mutant gate")
        return 0
    for production_anchor in ("/proc/sys/kernel/random/boot_id",
                              "/proc/self/stat", "getrandom", "WLSCPL_GetBuildGeneratedManifest",
                              "WlascStockStageReceiptV1", "WlgrIfParentSeal"):
        require(production_anchor in generation_identity_ops,
                f"production identity ops missing anchor: {production_anchor}")
    for facts_mutant in ("WlgrIfParseBootId", "WlgrIfValidateMetadata",
                         "WLGR_IF_NONCE_REPLAY"):
        require(facts_mutant in generation_identity_facts or
                facts_mutant in generation_identity_facts_header,
                f"generation identity facts mutant survived: {facts_mutant}")
    for producer_mutant in (
        "wlgr_v2_runtime_key_valid",
        "ReadCurrentProcess(ops, &pid, &start) != 0",
        "InputDigest(&candidate, digest) != 0",
        "DigestEqual(producer)",
        "wlgr_v2_identity_equal(&producer->identity, &candidate)",
    ):
        require(not generation_identity_producer_fails_closed(
                    generation_identity_producer.replace(
                        producer_mutant, "mutated"),
                    generation_identity_producer_header),
                f"generation identity producer mutant survived: {producer_mutant}")
    require("ChildMain::run(" not in child,
            "legacy security-bearing child entry entered Route A source")
    require("westlake_native_compat_prepare_main_thread" not in child,
            "post-stock child path must not own a second MAIN admission")
    require(legacy_child_fails_closed(legacy_child),
            "legacy security-owning child path is not compile-safe fail-closed")
    require(not legacy_child_fails_closed(
                legacy_child.replace("_exit(125);", "(void)0;", 1)),
            "legacy fail-closed mutation survived")
    require(class_loader_reinjection_fails_closed(child),
            "mandatory adapter class-loader reinjection is not fail-closed")
    require(not class_loader_reinjection_fails_closed(
                child.replace("_exit(21);", "(void)0;", 1)),
            "class-loader fail-closed mutation survived")
    require(fresh_child_vm_avoids_unpaired_zygote_hooks(child),
            "fresh specialized-child VM retained unpaired zygote post-fork hooks")
    require(not fresh_child_vm_avoids_unpaired_zygote_hooks(
                child.replace(
                    "runtime->onChildInit();",
                    "runtime->zygotePostForkChild(); runtime->onChildInit();",
                    1)),
            "unpaired zygote post-fork mutation survived")
    require(specialized_child_vm_uses_non_zygote_mode(runtime, provider),
            "fresh specialized-child VM retained legacy zygote mode")
    require(not specialized_child_vm_uses_non_zygote_mode(
                runtime, provider.replace("startVm(false)", "startVm(true)", 1)),
            "specialized-child zygote-mode mutation survived")
    require(graphics_child_marker_uses_exact_loaded_group(child),
            "graphics child marker is not bound to the exact loaded libhwui group")
    require(typeface_warmup_override_is_narrow_and_ordered(child),
            "Typeface warmup compatibility override is absent, broad, or misordered")
    require(dynamic_root_admission_fails_closed(
                runtime, child, bridge_identity),
            "runtime/bridge roots are not admitted before load side effects")
    require(not dynamic_root_admission_fails_closed(
                runtime.replace("LoadVerifiedAndroidRuntime", "dlopen", 1),
                child, bridge_identity),
            "runtime exact-admission mutant survived")
    require(not dynamic_root_admission_fails_closed(
                runtime,
                child.replace("VerifyLoadedAdapterBridge(bridge)", "true", 1),
                bridge_identity),
            "child bridge identity mutant survived")
    require(stock_child_reply_precedes_android_runtime(plugin),
            "stock child reply is absent, incomplete, or ordered after Android runtime entry")
    require(not stock_child_reply_precedes_android_runtime(
                plugin.replace(
                    "CompleteStockChildReply(content, client)",
                    "mutated(content, client)", 1)),
            "stock child reply call-order mutation survived")
    require(child_identity_producer_starts_empty(plugin),
            "child identity producer does not start from explicit EMPTY state")
    require(not child_identity_producer_starts_empty(
                plugin.replace(
                    "ZeroBytes(&producer, sizeof(producer));",
                    "mutated(&producer);", 1)),
            "child identity producer initialization mutant survived")
    require(live_target_boot_rebind_fails_closed(plugin, target_build),
            "target boot identity is builder-bound or not rebound before admission")
    require(not live_target_boot_rebind_fails_closed(
                plugin.replace("WlgrIfDigestMetadata(&metadata,",
                               "mutated(", 1),
                target_build),
            "target boot metadata digest mutation survived")
    require(full_launch_generation_fails_closed(target_build),
            "target metadata truncates the 64-bit launch generation")
    require(not full_launch_generation_fails_closed(
                target_build.replace("[:16]", "[:15]", 1)),
            "launch-generation truncation mutant survived")
    require("MODULE_CONSTRUCTOR" not in plugin and
            "WLASC_InstallStockHostServicesV1" in plugin,
            "plugin must remain inert until MAIN installs typed services")
    require(stock_host_table_fails_closed(plugin),
            "plugin stock-host table is not identity-bound/fail-closed")
    for stock_table_mutant in (
        "StockServicesValid(services)",
        "services->plugin_elf_sha256",
        "services->plugin_build_id",
        "services->add_server_stage_hook != 0",
        "services->clear_child_environment != 0",
        "g_stock_host_services = *services",
        "WLASC_STOCK_SERVICES_INSTALLED",
    ):
        require(not stock_host_table_fails_closed(
                    plugin.replace(stock_table_mutant, "mutated")),
                f"stock-host table mutant survived: {stock_table_mutant}")
    for forbidden_plugin_import in (
        "AddServerStageHook(", "AddAppSpawnHook(",
        "GetAppSpawnMsgInfo(", "CheckAppSpawnMsgFlag(",
        "RegChildLooper(",
        "westlake_native_compat_prepare_main_thread",
        "westlake_native_compat_prepare_parent_runtime",
        "westlake_native_compat_verify_parent_preload_thread_ready",
        "westlake_native_compat_verify_current_thread_ready",
        "westlake_native_compat_get_audit_snapshot",
    ):
        require(forbidden_plugin_import not in plugin,
                f"plugin retained direct MAIN edge: {forbidden_plugin_import}")

    legacy_entry = provider[provider.index(
        "int WLAR_EnterAndroidAfterStockSpecialization("):
        provider.index("int WLAR_PrepareA02PrerequisiteBundleV2(")]
    require("return WLGR_V2_ERROR_MISSING_PREREQUISITE;" in legacy_entry,
            "legacy provider entry is not deterministic fail-closed")
    entry = provider[provider.index(
        "int WLAR_PrepareA02PrerequisiteBundleV2("):]
    validate = entry.index("RequestValid(request, stock)")
    loader_admission = entry.index(
        "LoaderAdmissionValid(sealed_manifest, sealed_load_result)")
    identity_validate = entry.index("wlgr_v2_identity_valid(identity)")
    translate = entry.index("Translate(*request)")
    enter_android = entry.index("wlar_child_sequence::Run(")
    require(validate < loader_admission < identity_validate < translate <
            enter_android,
            "receipt-bound composite generation/loader admission order drift")
    constructors = provider[provider.index("int Constructors(void *p)"):
                            provider.index("int Vm(void *p)")]
    for identity_field in (
        "process.abi_version = WLNC_ABI_VERSION",
        "process.struct_size = sizeof(process)",
        "process.runtime_generation = c->request.runtime_generation",
        "process.message_id = c->request.message_id",
        "process.uid = c->request.uid",
        "process.gid = c->request.gid",
        "process.parent_stage_tail_reached",
        "process.child_stage_tail_reached",
        "process.bypass_guard_passed",
        "process.security_owner_stock_appspawn",
        "process.parent_tail_priority",
        "process.child_tail_priority",
        "std::memcpy(process.runtime_provider_sha256",
    ):
        require(identity_field in constructors,
                f"receipt-bound process identity lost: {identity_field}")
    sequence = provider[provider.index("int32_t Run(Ledger *ledger"):
                                provider.index("} // namespace wlar_child_sequence")]
    require(sequence.index("ops.constructors(ops.context)") <
            sequence.index("ops.vm(ops.context)") <
            sequence.index("ops.jni(ops.context)") and
            "WLGR_V2_ERROR_CONSTRUCTOR_FAILED" in sequence and
            "WLGR_V2_ERROR_VM_CREATE_FAILED" in sequence and
            "WLGR_V2_ERROR_JNI_REGISTER_FAILED" in sequence and
            "wlgr_v2_a02_bundle_valid(&bundle)" in sequence,
            "specialized child T09/T10/T11 constructors/VM/JNI sequence drift")
    for forbidden_parent_provider_entry in (
        "WLAR_ServerPreload",
        "WLAR_ZygotePreFork",
        "WLAR_ZygotePostForkParent",
    ):
        require(forbidden_parent_provider_entry not in provider and
                forbidden_parent_provider_entry not in provider_map,
                f"provider retained parent entry: {forbidden_parent_provider_entry}")
    require("snapshot.accepted_event_count != "
            "snapshot.registry_audit_sequence" in provider and
            "snapshot.registry_audit_drop_count != UINT64_C(0)" in provider and
            "typeCount == snapshot.accepted_event_count" in provider,
            "lossless audit snapshot receipt is not checked before guest entry")
    require("westlake_native_compat_prepare_main_thread;" not in host_map and
            "westlake_native_compat_prepare_parent_runtime;" not in host_map and
            "westlake_native_compat_verify_parent_preload_thread_ready;" not in host_map and
            "westlake_native_compat_verify_current_thread_ready;" not in host_map and
            "westlake_native_compat_get_audit_snapshot;" not in host_map and
            "services.prepare_main_thread =" in host and
            "services.prepare_parent_runtime =" in host and
            "services.verify_parent_preload_thread_ready =" in host and
            "services.verify_current_thread_ready =" in host and
            "services.get_audit_snapshot =" in host,
            "MAIN callbacks did not move behind the private typed table")
    require("WLAR_InstallHostRuntimeServices;" in provider_map,
            "runtime provider lost versioned host-services install export")
    require("WLAR_GetRuntimeIdentity;" in provider_map,
            "runtime provider lost pre-preload identity export")
    loader_create = app_loader[app_loader.index("int ANL_CreateDomain("):
                               app_loader.index("void* ANL_Dlopen(")]
    loader_open = app_loader[app_loader.index("void* ANL_Dlopen("):]
    loader_close = app_loader[app_loader.index("int ANL_Dlclose("):]
    require(loader_create.index("verify_runtime_ready(") <
            loader_create.index(
                "namespace_host_ops.create_configured_namespaces(") and
            loader_open.index("verify_runtime_ready(") <
            loader_open.index("namespace_host_ops.open_namespace(") and
            loader_close.index("verify_runtime_ready(") <
            loader_close.index("dlclose(handle)"),
            "guest open/close READY gate order drift")
    stock_namespace_create = host[
        host.index("static WLASC_NOINLINE int StockCreateConfiguredNamespaces("):
        host.index("static WLASC_NOINLINE void *StockOpenNamespace(")]
    stock_namespace_open = host[
        host.index("static WLASC_NOINLINE void *StockOpenNamespace("):
        host.index("static uint8_t HexNibble(")]
    require("dlns_create2(" not in loader_create and
            "dlopen_ns(" not in loader_open and
            stock_namespace_create.index(
                "dlns_create2(bridge_namespace") <
            stock_namespace_create.index("dlopen_ns(") <
            stock_namespace_create.index("dlsym(") <
            stock_namespace_create.index("install(pthread_bridge_ops)") <
            stock_namespace_create.index("dlns_create2(app_namespace") and
            "dlns_inherit(app_namespace, bridge_namespace" in
                stock_namespace_create and
            "dlopen_ns(app_namespace, path, mode | RTLD_LOCAL)" in
                stock_namespace_open and
            "NamespaceResultFence(result)" in stock_namespace_create and
            "NamespaceHandleFence(handle)" in stock_namespace_open,
            "default-owner namespace/bootstrap cohort drift")
    require("services.create_configured_namespaces =" in host and
            "services.open_namespace =" in host and
            "child_services.create_configured_namespaces =" in plugin and
            "child_services.open_namespace =" in plugin and
            "WLAR_HostServicesGetNamespaceCallbacks(" in provider and
            "gate.namespace_host_ops.create_configured_namespaces =" in
                provider and
            "gate.namespace_host_ops.open_namespace =" in provider,
            "default-owner namespace callback plumbing drift")

    child_entry = plugin[plugin.index("static int WestlakeRunAndroidChild("):
                         plugin.index("static int WestlakeServerPrepareInert(")]
    consume = child_entry.index("WLASC_ReceiptConsume")
    publish = child_entry.index("PublishChildHookTable(&request)")
    sealed_load = child_entry.index("LoadSealedProviderAfterHooks(&request, &receipt)")
    require(consume < publish < sealed_load and
            "WLSCPL_GetBuildGeneratedManifest()" in plugin and
            "WlscplLoadRequestV2" in plugin and
            "WlscplLoadResultV2" in plugin and
            "generation_identity" in plugin and
            "load_request.specialization_complete = UINT32_C(1)" in plugin and
            "load_request.hook_table_ready = UINT32_C(1)" in plugin and
            "load_request.generation_seal_verified = UINT32_C(1)" in plugin and
            "WLSCPL_LoadSealedProvider(" in plugin,
            "sealed provider became reachable before receipt/hook publication")
    for forbidden_provider_edge in (
        "WLAR_GetRuntimeIdentity(",
        "WLAR_InstallHostRuntimeServices(",
        "WLAR_ServerPreload(",
        "WLAR_ZygotePreFork(",
        "WLAR_ZygotePostForkParent(",
        "WLAR_EnterAndroidAfterStockSpecialization(",
    ):
        require(forbidden_provider_edge not in plugin,
                f"plugin retained provider ABI edge: {forbidden_provider_edge}")
    require(exact_plugin_install_fails_closed(host, elf_identity),
            "MAIN does not identity-bind the inert plugin before service start")
    for mutate_identity, plugin_install_mutant in (
        (False, "WLASC_PLUGIN_ELF_SHA256_HEX"),
        (True, "VerifyBuildId(descriptor, &status, expected_machine"),
        (True, "strcmp(resolved_path, expected_absolute_path) != 0"),
        (False, "dlopen(plugin_path, RTLD_NOW | RTLD_NOLOAD)"),
        (True, "dladdr(symbol, &information)"),
        (False, "services.plugin_build_id"),
    ):
        require(not exact_plugin_install_fails_closed(
                    (host if mutate_identity else
                     host.replace(plugin_install_mutant, "mutated")),
                    (elf_identity.replace(plugin_install_mutant, "mutated")
                     if mutate_identity else elf_identity)),
                f"exact-plugin install mutant survived: {plugin_install_mutant}")
    require("WLASC_GUARD_PRIORITY (HOOK_PRIO_SANDBOX - 1)" in plugin and
            "WLASC_TAIL_PRIORITY" in plugin,
            "stock child guard/tail ordering drift")
    require("HOOK_STOP_WHEN_ERROR" in service and
            "STAGE_PARENT_PRE_FORK" in service,
            "parent pre-fork fail-closed patch absent")

    require("src/child_main.cpp" not in build,
            "legacy security-bearing child source compiled into final Route A")
    require('external_contract = {' in target_build and
            '"libc.so"' in target_build and
            '"libc++.so"' in target_build and
            '"libhilog.so"' in target_build and
            '"libbegetutil.z.so"' in target_build and
            '"libconfigpolicy_util.z.so"' in target_build and
            '"libsec_shared.z.so"' in target_build and
            '"libutils.z.so"' in target_build and
            '"libclang_rt.ubsan_minimal.so"' in target_build and
            'frozen/target_external/openharmony-6.1.0.31-d600' in
                target_build and
            'target_external / "libc.so"' in target_build and
            '"/system/lib/ld-musl-aarch64.so.1"' in target_build and
            'target_external / "libc++.so"' in target_build and
            'target_external / "libhilog.so"' in target_build and
            'target_external / "libbegetutil.z.so"' in target_build and
            'target_external / "libconfigpolicy_util.z.so"' in target_build and
            'target_external / "libsec_shared.z.so"' in target_build and
            'target_external / "libutils.z.so"' in target_build and
            '"libsystemparam.z.so": (' in target_build and
            'target_external / "libsystemparam.z.so"' in target_build and
            '"/system/lib64/chipset-sdk-sp/libsystemparam.z.so"' in target_build and
            'target_external / "libclang_rt.ubsan_minimal.so"' in target_build and
            '"/system/lib64/chipset-sdk-sp/libclang_rt.ubsan_minimal.so"' in target_build and
            '"$SYSTEMPARAM_ORIGIN"' in target_build and
            'uncontracted recursive DT_NEEDED' in target_build and
            'uncontracted recursive system-root DT_NEEDED' in target_build and
            'pending.extend(system_needed)' in target_build and
            'WLSCPL_ARTIFACT_OH_SYSTEM_ROOT' in target_build and
            'manifest_encoding = bytearray(b"WLSCPL-MANIFEST-V2")' in
                target_build and
            'manifest_digest = hashlib.sha256' in target_build and
            'const WlscplManifestV2 *WLSCPL_GetBuildGeneratedManifest' in
                target_build,
            "sealed manifest does not close internal and explicit OH external roots")
    for stale_target_path in (
        '"/system/lib64/libc.so"',
        '"/system/lib64/libc++.so"',
        '"/system/lib64/libhilog.so"',
        '"/system/lib64/libsystemparam.z.so"',
        '"/system/lib64/libclang_rt.ubsan_minimal.so"',
    ):
        require(stale_target_path not in target_build,
                f"sealed manifest retained non-D600 root path: {stale_target_path}")
    require('sealed_needed = [dependency for dependency in needed' not in
                target_build,
            "manifest generator still silently drops DT_NEEDED edges")
    require('candidates[systemparam.name] = systemparam' not in target_build,
            "libsystemparam is still admitted as a late sealed-load candidate")
    for required_source in (
        "appspawn_server.c",
        "appspawn_modulemgr.c",
        "appspawn_appmgr.c",
        "appspawn_msgmgr.c",
        "appspawn_service.c",
        "adapter_bridge_identity.cpp",
        "host_runtime_services.c",
        "runtime_loader_phase.c",
        "sealed_child_provider_loader.c",
        "child_hook_table_v1.c",
        "westlake_elf_identity.c",
        "westlake_sha256.c",
        "westlake_android_runtime_provider.cpp",
        "child_main_after_stock.cpp",
        "thread_guard_registry.c",
        "jni_attach_admission.cpp",
        "guard_store_aarch64.S",
        "bionic_pthread_bridge.c",
        "westlake_bionic_pthread_bridge.map",
        "native_compat_prepare_owner_aarch64.S",
        "thread_template_publisher.c",
        "system_properties.cpp",
        "malloc_compat.cpp",
        "fdsan_stubs.cpp",
        "misc_compat.cpp",
        "abort_message_compat.cpp",
        "liblog_android_supplement.cpp",
        "sync_builtins.c",
        "app_native_loader.c",
        "native_loader.cpp",
        "native_loader_registry.cpp",
        "system_loader.cpp",
        "native_loader.map",
        "native_bridge_policy.v1.json",
        "palette_oh.c",
        "art_palette_oh.map",
        "palette_oh.c",
    ):
        require(required_source in build,
                f"final Route A build lost source: {required_source}")
    for forbidden_product_source in (
        "bionic_tls_abi.c",
        "unity_pthread_box.c",
        "unity_signal_box.c",
        "art_runtime_stubs.cpp",
    ):
        require(forbidden_product_source not in build,
                f"competing/broad compatibility owner entered Route A: "
                f"{forbidden_product_source}")
    require("provider-v12" in build and
            "BASE_PROVIDER_ROOT" in build and
            "base-providers.sha256" in build,
            "certified frozen v12 provider closure is not a final-link input")
    require(build.index("build_provider pass2") <
            build.rindex('"$PLUGIN/build_target_in_container.sh"') <
            build.index("build_stock_host pass1"),
            "Route A must build provider, then identity-bound plugin, then host")
    for identity_define in (
        "WLAR_ADAPTER_BRIDGE_PATH",
        "WLAR_ADAPTER_BRIDGE_SHA256_HEX",
        "WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX",
        "WLAR_ANDROID_RUNTIME_PATH",
        "WLAR_ANDROID_RUNTIME_SHA256_HEX",
        "WLAR_ANDROID_RUNTIME_BUILD_ID_HEX",
        "WLASC_PLUGIN_GENERATION_SHA_HEX",
        "WLASC_PLUGIN_ELF_SHA256_HEX",
        "WLASC_PLUGIN_BUILD_ID_HEX",
    ):
        require(identity_define in build,
                f"final Route A build lost identity binding: {identity_define}")
    target_plugin_link = target_build[
        target_build.index("build_pass()"):
        target_build.index("build_pass pass1")
    ]
    require("-lwestlake_android_runtime_provider" not in target_plugin_link and
            '"$dir/sealed_child_provider_loader.o"' in target_plugin_link and
            '"$dir/child_hook_table_v1.o"' in target_plugin_link and
            '"$dir/westlake_elf_identity.o"' in target_plugin_link and
            '"$dir/westlake_sha256.o"' in target_plugin_link and
            "-Wl,--build-id=0x$PLUGIN_BUILD_ID_HEX" in target_build and
            "-Wl,--no-allow-shlib-undefined" in target_build,
            "child plugin retained implicit provider activation or lost loader identity checks")
    host_link = build[
        build.index("build_stock_host()"):build.index("build_stock_host pass1")
    ]
    require("-lwestlake_android_runtime_provider" not in host_link,
            "stock host retained the exact old -lwestlake_android_runtime_provider edge")
    require("-lwestlake_android_runtime_provider" not in target_plugin_link,
            "child plugin retained the exact old -lwestlake_android_runtime_provider edge")
    require("test_child_hook_table_v1.c" in target_build and
            "test_westlake_child_hook_table_v1_layout.c" in target_build and
            "test_sealed_child_provider_loader.c" in target_build and
            "test_westlake_generation_receipt_v2.c" in host_tests and
            "test_westlake_generation_receipt_v2.cpp" in host_tests and
            "build_child_hook_table" in host_tests and
            "build_child_hook_layout" in host_tests and
            "build_sealed_child_loader" in host_tests,
            "deterministic child hook/loader host PNF wiring is absent")
    require("test_sealed_child_loader_swap_mutant" in host_tests and
            "WLSCPL_MUTANT_SKIP_MAPPED_INODE_BIND" in host_tests and
            "-fsanitize=address,undefined" in host_tests and
            "generation_receipt_v2_c_semantics=10" in host_tests and
            "generation_receipt_v2_cpp_layout=pass" in host_tests,
            "official loader swap-mutant/sanitizer/generation-v2 gates are absent")
    require(child_hook_table_fails_closed(child_hook, child_hook_header),
            "frozen child hook table implementation is not fail-closed")
    require(sealed_child_loader_fails_closed(
                sealed_loader, sealed_loader_header),
            "sealed specialized-child provider loader is not fail-closed")
    for build_id_negative in (
        "BuildId32AllZeroRejected",
        "BuildId40AllZeroRejected",
        "BuildId31Rejected",
        "BuildId33Rejected",
        "BuildId39Rejected",
        "BuildId41Rejected",
        "BuildIdUppercaseRejected",
    ):
        require(build_id_negative in sealed_loader_tests,
                f"sealed loader lost Build-ID P/N/F: {build_id_negative}")
    require("sealed_child_provider_loader_pnf=28" in host_tests,
            "sealed loader Build-ID P/N/F is not wired into host runner")
    for mutation in (
        "request->parent_pid == request->generation_identity->child_pid",
        "request->hook_table_ready != UINT32_C(1)",
        "ExactLowerHex(artifact->build_id_hex, 40U)",
        "ExactLowerHex(artifact->build_id_hex, 32U)",
        "HexHasNonzeroDigit(artifact->build_id_hex,\n"
        "                 BoundedLength",
        "BoundedLength(artifact->build_id_hex,\n"
        "                               WLSCPL_BUILD_ID_HEX_SIZE)",
        "ExactLowerHex(artifact->sha256_hex, 64U)",
        "HexHasNonzeroDigit(artifact->sha256_hex, 64U)",
        "ComputeManifestDigest(request->manifest",
        "order_count != request->manifest->artifact_count",
        "if (ops->mapped_identity_matches(",
        "request->generation_identity->artifact_manifest_digest",
        "RTLD_NOW | RTLD_LOCAL",
    ):
        require(not sealed_child_loader_fails_closed(
                    sealed_loader.replace(mutation, "mutated", 1),
                    sealed_loader_header),
                f"sealed child loader mutant survived: {mutation}")
    require("$FROZEN/libraries/aosp" not in build and
            "runtime_provider/libraries/aosp" not in build,
            "deprecated pre-v12 AOSP provider directory entered Route A")
    require("libartpalette-system.so" in build and
            "art-palette-oh" in build,
            "real OH ART Palette replacement is absent from Route A")
    require("-lapp_native_loader" in build and
            'build_native_loader pass1' in build and
            'build_native_loader pass2' in build and
            '-L"$OUT/$pass/native-loader"' in build and
            'cp "$OUT/libnativeloader.so" "$OUT/providers/"' in build and
            "-lwestlake_thread_guard_registry" in build and
            "-Wl,-z,defs" in build and "-Wl,-z,now" in build and
            "-Wl,--no-allow-shlib-undefined" in build,
            "full final-link fail-closed flags are missing")
    require('-c "$JNI_ATTACH/src/jni_attach_admission.cpp"' in build and
            '"$dir/jni_attach_admission.o"' in build and
            '-L"$OUT/$pass/registry"' in build,
            "central JNI admission is not a real Route-A compile/link input")
    require("-Wl,--allow-shlib-undefined" not in build,
            "runtime provider retained allow-shlib-undefined")
    require("build_pthread_bridge pass1" in build and
            "build_pthread_bridge pass2" in build and
            "libwestlake_bionic_pthread_bridge.so\" \"$OUT/providers/" in
            build and
            'EXPECTED_FINAL_PROVIDER_COUNT' in build and
            "--pthread-bridge" in build and
            "--second-pthread-bridge" in build,
            "namespace pthread bridge is not a deterministic Route-A provider")
    require(route_a_zlib_fails_closed(build),
            "Route-A zlib remediation lost source provenance, SHA-1 identity, or ABI guards")
    for zlib_mutant in (
        build.replace(
            "OH_ZLIB=$ROOT/upstream/openharmony-6.1.0.31/third_party/zlib",
            "OH_ZLIB=$ROOT/src/upstream/openharmony-6.1.0.31/third_party/zlib",
            1),
        build.replace(
            'cp "$OUT/libshared_libz.z.so" "$OUT/providers/"',
            'cp "$V12_DEPS/libshared_libz.z.so" "$OUT/providers/"',
            1),
    ):
        require(not route_a_zlib_fails_closed(zlib_mutant),
                "Route-A zlib source/frozen-fallback mutant survived")
    require(route_a_container_mounts_fail_closed(run_all),
            "Route-A container root, nested mount order, or preflight guard is incomplete")
    for mount_mutant in (
        run_all.replace(
            '-v "$PROJECT_ROOT:/project:rw" \\\n'
            '    "${DOCKER_INPUT_ARGS[@]}" \\\n',
            '"${DOCKER_INPUT_ARGS[@]}" \\\n'
            '    -v "$PROJECT_ROOT:/project:rw" \\\n',
            1),
        run_all.replace(
            "HOST_LOGICAL_GENERATION_ROOT="
            "$PROJECT_ROOT/.work/product-tls-generation",
            "HOST_LOGICAL_GENERATION_ROOT=$HOST_GENERATION_ROOT",
            1),
        run_all.replace(
            "CONTAINER_LOGICAL_GENERATION_ROOT="
            "/.work/product-tls-generation",
            "CONTAINER_LOGICAL_GENERATION_ROOT="
            "/project/.work/product-tls-generation",
            1),
        run_all.replace(
            "test -f /project/upstream/openharmony-6.1.0.31/"
            "third_party/zlib/BUILD.gn",
            "test -f /project/src/upstream/openharmony-6.1.0.31/"
            "third_party/zlib/BUILD.gn",
            1),
    ):
        require(not route_a_container_mounts_fail_closed(mount_mutant),
                "Route-A container mount/path mutant survived")

    print("PASS Route A source ownership and call-order gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
