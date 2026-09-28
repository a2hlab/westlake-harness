#ifndef ANL_PROBE_CONSTRUCTOR_MARKER
#error "ANL_PROBE_CONSTRUCTOR_MARKER must identify the provider"
#endif

static int g_constructor_marker;

__attribute__((constructor)) static void anl_probe_constructor_init(void) {
    g_constructor_marker = ANL_PROBE_CONSTRUCTOR_MARKER;
}

__attribute__((visibility("default"))) int anl_probe_constructor_value(void) {
    return g_constructor_marker;
}
