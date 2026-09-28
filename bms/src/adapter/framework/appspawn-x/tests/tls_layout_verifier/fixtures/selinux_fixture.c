#include <stdint.h>

/* Keep prev_current at STT_TLS st_value 0x20, as in the target libselinux. */
__attribute__((used, aligned(8))) __thread unsigned char selinux_tls_prefix[0x20];
__attribute__((used)) static __thread void *prev_current;

int selinux_fixture_anchor(void)
{
    return selinux_tls_prefix[0] + (prev_current != (void *)0);
}
