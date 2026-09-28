extern int anl_bridge_denied_value(void);

__attribute__((visibility("default"))) int anl_denied_root_value(void) {
    return anl_bridge_denied_value();
}
