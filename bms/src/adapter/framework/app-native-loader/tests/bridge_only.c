static int g_initialized;

__attribute__((constructor)) static void anl_bridge_only_init(void) {
    g_initialized = 1;
}

__attribute__((visibility("default"))) int anl_bridge_only_value(void) {
    return 0x3000 + g_initialized;
}
