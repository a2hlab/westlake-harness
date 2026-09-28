#ifndef ANL_PROBE_NESTED_MARKER
#error "ANL_PROBE_NESTED_MARKER must identify the provider"
#endif

__attribute__((visibility("default"))) int anl_probe_nested_leaf_value(void) {
    return ANL_PROBE_NESTED_MARKER;
}
