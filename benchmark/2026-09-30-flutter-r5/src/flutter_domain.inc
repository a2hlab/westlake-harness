/* Westlake link_stubs_arm64.cc exact-target selection / owner inheritance,
 * adapted to ANL per-domain ownership. Only these six package path components. */
static bool flutter_package_path(const char* text) {
    static const char* const packages[] = {
        "chat.fluffy.fluffychat", "app.alextran.immich", "com.tombursch.kitchenowl",
        "deckers.thibault.aves.libre", "com.adilhanney.saber", "org.localsend.localsend_app"
    };
    for (size_t i = 0; i < sizeof(packages)/sizeof(packages[0]); ++i) {
        const char* p = text;
        while ((p = strstr(p, packages[i])) != NULL) {
            size_t n = strlen(packages[i]);
            if ((p == text || p[-1] == '/') && (p[n] == '/' || p[n] == '\0')) return true;
            p += n;
        }
    }
    return false;
}
static int flutter_prepare(AnlDomain* domain) {
    if (domain->flutter_state != 0) return domain->flutter_state == 1 ? 0 : -1;
    domain->flutter_state = -1;
    if (!domain->has_bridge) return failf("Flutter pthread bridge configuration missing");
    const char* private_root = "/system/android/lib64/westlake_flutter";
    char app_name[NS_NAME_MAX + 1], bridge_name[NS_NAME_MAX + 1];
    char search[2 * PATH_MAX], permitted[3 * PATH_MAX];
    unsigned long id = atomic_fetch_add_explicit(&g_domain_id, 1, memory_order_relaxed);
    /* Exact owned-name grammar required by the existing stock-host callbacks. */
    snprintf(app_name, sizeof(app_name), "westlake.anl.app.%ld.%lu", (long)getpid(), id);
    snprintf(bridge_name, sizeof(bridge_name), "westlake.anl.bridge.%ld.%lu", (long)getpid(), id);
    if (snprintf(search, sizeof(search), "%s:%s", private_root, domain->app_paths) >= (int)sizeof(search) ||
        snprintf(permitted, sizeof(permitted), "%s:%s:%s", private_root,
                 domain->app_paths, domain->app_permitted_paths) >= (int)sizeof(permitted))
        return failf("Flutter namespace paths exceed limits");

    /* Host owns all namespace operations in default. Its existing bridge has
     * CREATE_INHERIT_DEFAULT; the app gets only this explicit shared-name list.
     * Do not call dlns_* directly from the sealed ANL DSO. */
    const char* shared =
        "libc.so:libdl.so:libm.so:libEGL.so:libGLESv3.so:libsurface.z.so:"
        "liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so:"
        "libwestlake_bionic_pthread_bridge.so";
    int rc = domain->runtime_gate.namespace_host_ops.create_configured_namespaces(
        &domain->flutter_bridge, bridge_name,
        domain->flutter_bridge_search, domain->flutter_bridge_permitted, shared,
        "libwestlake_bionic_pthread_bridge.so", &domain->runtime_gate.pthread_bridge_ops,
        &domain->flutter_bootstrap_handle, &domain->flutter, app_name, search, permitted);
    if (rc != 0) return failf("Flutter default-owner namespace configuration failed: %d", rc);
    const char* preload[] = {"libandroid.so", "libGLESv2.so", "libjnigraphics.so"};
    for (size_t i = 0; i < sizeof(preload)/sizeof(preload[0]); ++i) {
        domain->flutter_handles[i] = domain->runtime_gate.namespace_host_ops.open_namespace(
            &domain->flutter, preload[i], RTLD_NOW | RTLD_LOCAL);
        if (domain->flutter_handles[i] == NULL)
            return failf("Flutter private preload %s: %s", preload[i], dlerror());
    }
    domain->flutter_state = 1;
    fprintf(stderr, "[ANL-FLUTTER] default-owner configured %s; private providers ready\n", app_name);
    return 0;
}
