from pathlib import Path
P=Path('bms/src/.work/b6-real-work/adapter/framework/appspawn-x/security_specialization/stock_child_plugin')
p=P/'src/westlake_android_child_plugin.c';s=p.read_text();s=s.replace('    if (CompleteStockChildReply(content, client) != 0) return -1;', '''    if (CompleteStockChildReply(content, client) != 0) {
        WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_STOCK_REPLY_PRECONDITION");
        RevokeChildHookTable(WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
        return -1;
    }''');a=s.index('    if (LoadSealedProviderAfterHooks(&request, &receipt) != 0)');z=s.index('\n}\n',a);s=s[:a]+'''    if (LoadSealedProviderAfterHooks(&request, &receipt) != 0) {
        WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_SEALED_PROVIDER");
        RevokeChildHookTable(WESTLAKE_CHILD_HOOK_TABLE_REJECTED);
        _exit(123);
    }
    WLASC_GATE_MARKER("WLCGATE:RAC:FAIL_PROVIDER_RETURNED");
    _exit(122);'''+s[z:];p.write_text(s)
p=P/'src/westlake_android_runtime_provider.cpp';s=p.read_text();a=s.index('bool InstallLoaderReadyGate()');s=s[:a]+'''WlascCreateConfiguredNamespacesV1 gCreateConfiguredNamespaces = nullptr;
WlascOpenNamespaceV1 gOpenNamespace = nullptr;
int CreateConfiguredNamespacesFromStock(
    Dl_namespace *bridge, const char *name, const char *search, const char *permitted,
    const char *shared, const char *bootstrap, const WlpbHostOpsV1 *ops,
    void **handle, Dl_namespace *app, const char *appName, const char *appSearch,
    const char *appPermitted)
{
    return gCreateConfiguredNamespaces == nullptr ? -1 :
        gCreateConfiguredNamespaces(bridge, name, search, permitted, shared,
                                   bootstrap, ops, handle, app, appName, appSearch, appPermitted);
}
void *OpenNamespaceFromStock(Dl_namespace *app, const char *path, int mode)
{
    return gOpenNamespace == nullptr ? nullptr : gOpenNamespace(app, path, mode);
}

'''+s[a:];s=s.replace('    WlascCreateConfiguredNamespacesV1 createNamespaces = nullptr;\n    WlascOpenNamespaceV1 openNamespace = nullptr;\n','');s=s.replace('&createNamespaces, &openNamespace','&gCreateConfiguredNamespaces, &gOpenNamespace').replace('reinterpret_cast<AnlCreateConfiguredNamespacesV1>(createNamespaces)','CreateConfiguredNamespacesFromStock').replace('reinterpret_cast<AnlOpenNamespaceV1>(openNamespace)','OpenNamespaceFromStock');p.write_text(s)
