#include <stdint.h>

/* With OH musl GAP_ABOVE_TP=16 this object owns TP+0x10..TP+0x3f. */
__attribute__((used, visibility("default"), aligned(16)))
__thread unsigned char __westlake_bionic_tls_aperture[48];

extern int host_tiny_anchor(void);
extern int selinux_fixture_anchor(void);

void _start(void)
{
    volatile int keep_needed_order = host_tiny_anchor() + selinux_fixture_anchor();
    (void)keep_needed_order;
}
