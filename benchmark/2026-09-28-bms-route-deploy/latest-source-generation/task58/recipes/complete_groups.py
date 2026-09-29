from pathlib import Path
import re
W=Path('bms/src/.work/b6-real-work');A=W/'adapter/framework/appspawn-x';P=A/'security_specialization/stock_child_plugin'
p=P/'src/westlake_android_runtime_provider.cpp';s=p.read_text();start=s.index('    return WLAR_HostServicesGetNamespaceCallbacks(',s.index('bool InstallLoaderReadyGate()'));end=s.index('\n}',start)
s=s[:start]+'''    WlascCreateConfiguredNamespacesV1 createNamespaces = nullptr;
    WlascOpenNamespaceV1 openNamespace = nullptr;
    if (WLAR_HostServicesGetNamespaceCallbacks(
            &gHostServicesRegistry, &createNamespaces, &openNamespace) != 0) return false;
    gate.namespace_host_ops.abi_version = ANL_NAMESPACE_HOST_OPS_ABI_VERSION;
    gate.namespace_host_ops.struct_size = sizeof(gate.namespace_host_ops);
    gate.namespace_host_ops.runtime_generation = ProviderGeneration();
    gate.namespace_host_ops.create_configured_namespaces =
        reinterpret_cast<AnlCreateConfiguredNamespacesV1>(createNamespaces);
    gate.namespace_host_ops.open_namespace = reinterpret_cast<AnlOpenNamespaceV1>(openNamespace);
    return WLAR_HostServicesGetPthreadBridgeOps(
               &gHostServicesRegistry, &gate.pthread_bridge_ops) == 0 &&
           ANL_InstallRuntimeGate(&gate) == 0;'''+s[end:];p.write_text(s)
p=A/'src/appspawnx_runtime.cpp';s=p.read_text();s=re.sub(r'extern "C" std::size_t westlake_art_copy_fault_message_for_abort_logging\(\n    char\* output, std::size_t capacity\);\n','',s)
a=s.index('static void logArtAbortAndTerminate()');z=s.index('\n}\n',a)+3;s=s[:a]+s[z:]
s=re.sub(r'    JavaVMOption abortOption = makeOption\("abort"\);\n    abortOption.extraInfo = reinterpret_cast<void\*>\(logArtAbortAndTerminate\);\n    options.push_back\(abortOption\);\n','',s)
a=s.index('    int ret = registerNativeMethods();',s.index('int AppSpawnXRuntime::preload()'));z=s.index('    if (!appSpawnXInitClass_',a);jni=s[a:z]
a=s.index('    // Distinct T11 commit boundary:',s.index('int AppSpawnXRuntime::preload()'));s=s[:a]+s[z:]
a=s.index('    // Preserve AOSP ownership for libjavacore bootstrap:');z=s.index('    LOGI("ART VM creation commit complete");',a);s=s[:a]+jni+'\n'+s[z:];p.write_text(s)
p=P/'build_target_in_container.sh';s=p.read_text();s='\n'.join(l for l in s.splitlines() if not any(k in l for k in ['"$PLUGIN/generate_generation_metadata.py" \\', '"$PLUGIN/include/westlake_generation_identity_', '"$PLUGIN/src/westlake_generation_identity_', '"$PLUGIN/include/westlake_generation_receipt_v2.h"', '"$PLUGIN/src/bionic_stdio_broker.c"']))+'\n'
a=s.index('POLICY_PROVENANCE_DIGEST=');z=s.index('\nmkdir -p ',a);s=s[:a]+s[z:]
a=s.index('    local manifest_digest');z=s.index('    compile "$PLUGIN/src/stage_receipt.c"',a);s=s[:a]+'    generate_sealed_manifest "$pass" "$dir/sealed_provider_manifest.c"\n'+s[z:]
s=re.sub(r'    compile "\$dir/generated_generation_metadata.c" \\\n        "\$dir/generated_generation_metadata.o"\n','',s)
s='\n'.join(l for l in s.splitlines() if not any(k in l for k in ['"$dir/westlake_generation_identity_', '"$dir/generated_generation_metadata.o"']))+'\n';p.write_text(s)
for p in [W/'build-retained-generation-inner.sh',P/'build_route_a_generation_in_container.sh']:
 s=p.read_text();s=s.replace('-lbionic_compat -lwestlake_art_abort_bridge -lart -lbase -lnativeloader','-lbionic_compat -lart -lopenjdkjvm -lnativeloader').replace('-lbionic_compat -lart -lbase -lnativeloader','-lbionic_compat -lart -lopenjdkjvm -lnativeloader')
 a=s.index('for generated_input in \\');z=s.index('done\n',a)+5;s=s[:a]+s[z:];p.write_text(s)
print('G1/G2/G3 integration edits applied')
