extern int anl_peer_value(void);

__attribute__((visibility("default"))) int anl_root_value(void) {
    return anl_peer_value() + 1;
}
