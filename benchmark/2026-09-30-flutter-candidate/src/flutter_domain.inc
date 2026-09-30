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
static int flutter_inherit(Dl_namespace* target, const char* owner, const char* names) {
    Dl_namespace parent;
    if (dlns_get(owner, &parent) != 0 || dlns_inherit(target, &parent, names) != 0)
        return failf("Flutter owner unavailable: %s", owner);
    fprintf(stderr, "[ANL-FLUTTER] owner=%s names=%s\n", owner, names);
    return 0;
}
static int flutter_prepare(AnlDomain* domain) {
    if (domain->flutter_state != 0) return domain->flutter_state == 1 ? 0 : -1;
    domain->flutter_state = -1;
    char name[NS_NAME_MAX + 1], permitted[3 * PATH_MAX];
    snprintf(name, sizeof(name), "westlake.flutter.%ld.%lu", (long)getpid(),
             atomic_fetch_add_explicit(&g_domain_id, 1, memory_order_relaxed));
    snprintf(permitted, sizeof(permitted), "%s:%s:/system/android/lib64",
             domain->app_paths, domain->app_permitted_paths);
    dlns_init(&domain->flutter, name);
    if (dlns_create2(&domain->flutter, domain->app_paths, 0) != 0 ||
        dlns_set_namespace_separated(name, true) != 0 ||
        dlns_set_namespace_permitted_paths(name, permitted) != 0)
        return failf("Flutter namespace configuration failed");
    /* One-hop edges: never copy OH libraries into an app-local search root. */
    if (flutter_inherit(&domain->flutter, "default",
            "libc.so:libdl.so:libm.so:libEGL.so:libGLESv3.so:libnative_window.so:libnative_buffer.so") != 0 ||
        flutter_inherit(&domain->flutter, "westlake.sealed.child",
            "liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so") != 0)
        return -1;
    if (!domain->has_bridge || dlns_inherit(&domain->flutter, &domain->bridge,
            "libwestlake_bionic_pthread_bridge.so") != 0)
        return failf("Flutter pthread bridge owner unavailable");
    const char* preload[] = {
        "/system/android/lib64/libwestlake_flutter_android.so",
        "/system/android/lib64/libwestlake_flutter_gles2.so",
        "/system/android/lib64/libwestlake_flutter_jnigraphics.so"
    };
    for (size_t i = 0; i < sizeof(preload)/sizeof(preload[0]); ++i) {
        domain->flutter_handles[i] = dlopen_ns(&domain->flutter, preload[i], RTLD_NOW|RTLD_LOCAL);
        if (domain->flutter_handles[i] == NULL)
            return failf("Flutter private preload %s: %s", preload[i], dlerror());
    }
    domain->flutter_state = 1;
    fprintf(stderr, "[ANL-FLUTTER] configured %s; private providers ready\n", name);
    return 0;
}
