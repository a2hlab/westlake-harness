/* Mirrors the one-byte, align-one TLS module that precedes libselinux. */
__attribute__((used, aligned(1))) __thread unsigned char host_tiny_tls;

int host_tiny_anchor(void)
{
    return host_tiny_tls;
}
