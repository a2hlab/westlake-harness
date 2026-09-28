__attribute__((used)) __thread unsigned long runtime_tls_word;

unsigned long dynamic_tls_anchor(void)
{
    return runtime_tls_word;
}
