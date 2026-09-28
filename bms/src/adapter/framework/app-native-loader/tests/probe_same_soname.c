#ifndef ANL_PROBE_SAME_MARKER
#error "ANL_PROBE_SAME_MARKER must identify the domain provider"
#endif

__attribute__((visibility("default"))) int anl_probe_same_soname_value(void) {
    return ANL_PROBE_SAME_MARKER;
}
