extern int anl_shadow_value(void);
extern int anl_bridge_only_value(void);

__attribute__((visibility("default"))) int anl_dual_root_value(void) {
    return anl_shadow_value() + anl_bridge_only_value();
}
