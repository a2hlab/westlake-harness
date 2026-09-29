from pathlib import Path
P=Path('bms/src/.work/b6-real-work/adapter/framework/appspawn-x/security_specialization/stock_child_plugin')
p=P/'src/sealed_child_provider_loader.c';s=p.read_text();s=s.replace('CREATE_INHERIT_CURRENT | LOCAL_NS_PREFERED','CREATE_INHERIT_CURRENT')
s=s.replace('    uint8_t marks[WLSCPL_MAX_ARTIFACTS] = {0};','    uint8_t marks[WLSCPL_MAX_ARTIFACTS] = {0};\n    uint8_t inherited[WLSCPL_MAX_ARTIFACTS] = {0};')
a=s.index('            if (mapped != 0 &&');z=s.index('\n        }\n    }\n    for (index',a)
s=s[:a]+'''            int allowed = IsPreloadedRegistryUnityArtifact(artifact) ||
                IsPreloadedBionicCompatUnityArtifact(artifact) ||
                (strcmp(artifact->absolute_path, "/system/android/lib64/liblzma.so") == 0 &&
                 strcmp(artifact->soname, "liblzma.so") == 0);
            if ((allowed && mapped != 1) || (!allowed && mapped != 0)) {
                return Fail(loader, request, result,
                            WLSCPL_ERROR_PREMATURE_MAPPING, index + UINT32_C(1), ops);
            }
            inherited[order[index]] = (uint8_t)allowed;'''+s[z:]
s=s.replace('        uint32_t artifact_index = order[index];','        uint32_t artifact_index = order[index];\n        if (inherited[artifact_index]) continue;');p.write_text(s)
p=P/'build_target_in_container.sh';s=p.read_text().replace('    if name == "libbionic_compat.so":','    if name == "liblzma.so":\n        artifact_path = "/system/android/lib64/liblzma.so"\n    if name == "libbionic_compat.so":');p.write_text(s)
p=P/'verify_target_artifacts.py';s=p.read_text().replace('    "WLSCPL_InheritAndroidRuntimeV1",\n','')
s=s.replace('    "dlns_inherit",\n','').replace('    "getrandom",\n','').replace('    "strtoull",\n','')
s=s.replace('    "dlopen_ns",','    "dlopen_ns",\n    "dlopen",\n    "dlclose",\n    "strncmp",')
a=s.index('    required_plugin = (');z=s.index('\n\ndef main()',a)
s=s[:a]+'''    required_plugin = (
        "WLASC_ReceiptConsume", "PublishChildHookTable(&request)",
        "WLSCPL_LoadSealedProvider(", "InvokeProviderChildEntryWithResolver(",
        '"WLAR_InstallHostRuntimeServices"', '"WLAR_EnterAndroidAfterStockSpecialization"',
        "child_services.open_sealed_exact = WLSCPL_OpenPreparedNamespace;",
        "child_services.create_configured_namespaces = g_stock_host_services.create_configured_namespaces;",
        "child_services.open_namespace = g_stock_host_services.open_namespace;",
        "install(services)", "entry(request, receipt)",
    )
    required_loader = (
        "RTLD_NOW | RTLD_LOCAL", "CREATE_INHERIT_CURRENT",
        "return dlopen(absolute_path, flags);", "WLEI_VerifyFileHex(",
        "IsPreloadedRegistryUnityArtifact(artifact)", "IsPreloadedBionicCompatUnityArtifact(artifact)",
        '"/system/android/lib64/liblzma.so"', "if (inherited[artifact_index]) continue;",
        "!AbsoluteCanonicalForm(absolute_path)",
        "(flags & (RTLD_NOW | RTLD_GLOBAL)) != RTLD_NOW",
        'const char prefix[] = "/system/android/lib64/";',
    )
    if (not all(item in plugin for item in required_plugin) or
            not all(item in loader for item in required_loader) or
            any(item in plugin + loader for item in
                ("RTLD_DEFAULT", "RTLD_NEXT", "InvokeProviderA06ThenA02", "WLSCPL_InheritAndroidRuntimeV1"))):
        return False
    child = plugin[plugin.index("static int WestlakeRunAndroidChild("):
                   plugin.index("static int WestlakeServerPrepareInert(")]
    target_link = target_build[target_build.index("build_pass()"):
                               target_build.index("build_pass pass1")]
    host_link = route_build[route_build.index("build_stock_host()"):
                           route_build.index("build_stock_host pass1")]
    return (child.index("WLASC_ReceiptConsume") <
            child.index("PublishChildHookTable(&request)") <
            child.index("LoadSealedProviderAfterHooks(&request, &receipt)") and
            plugin.index("install_result = install(services)") < plugin.index("entry_result = entry(request, receipt)") and
            "-lwestlake_android_runtime_provider" not in target_link and
            "-lwestlake_android_runtime_provider" not in host_link)
'''+s[z:]
a=s.index('    for mutant in (');z=s.index('        # Replace every occurrence',a)
s=s[:a]+'''    for mutant in (
        "WLASC_ReceiptConsume", "PublishChildHookTable(&request)",
        "WLSCPL_LoadSealedProvider(", "InvokeProviderChildEntryWithResolver(",
        "child_services.open_sealed_exact = WLSCPL_OpenPreparedNamespace;",
        "child_services.create_configured_namespaces = g_stock_host_services.create_configured_namespaces;",
        "child_services.open_namespace = g_stock_host_services.open_namespace;",
        "RTLD_NOW | RTLD_LOCAL", "CREATE_INHERIT_CURRENT", "WLEI_VerifyFileHex(",
        "return dlopen(absolute_path, flags);", "!AbsoluteCanonicalForm(absolute_path)",
        "(flags & (RTLD_NOW | RTLD_GLOBAL)) != RTLD_NOW",
        "if (inherited[artifact_index]) continue;",
    ):
'''+s[z:];p.write_text(s)
print('V1 loader parity and matching topology gate restored')
