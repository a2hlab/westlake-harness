extern unsigned long dynamic_tls_anchor(void);

unsigned long dynamic_parent_anchor(void)
{
    return dynamic_tls_anchor();
}
