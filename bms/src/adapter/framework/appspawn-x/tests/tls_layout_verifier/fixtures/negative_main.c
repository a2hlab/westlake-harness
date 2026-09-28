extern int host_tiny_anchor(void);
extern int selinux_fixture_anchor(void);

void _start(void)
{
    volatile int keep_needed_order = host_tiny_anchor() + selinux_fixture_anchor();
    (void)keep_needed_order;
}
