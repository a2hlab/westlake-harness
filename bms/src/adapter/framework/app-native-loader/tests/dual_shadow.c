#ifndef ANL_SHADOW_BASE
#error "ANL_SHADOW_BASE must identify the app or bridge provider"
#endif

static int g_initialized;

__attribute__((constructor)) static void anl_shadow_init(void) {
    g_initialized = 1;
}

__attribute__((visibility("default"))) int anl_shadow_value(void) {
    return ANL_SHADOW_BASE + g_initialized;
}
