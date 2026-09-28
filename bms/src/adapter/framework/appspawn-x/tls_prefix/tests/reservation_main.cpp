#include <stdint.h>

extern "C" uint64_t westlake_tls_fixture_dso_value();

int main() { return westlake_tls_fixture_dso_value() == 0x5a17c0deULL ? 0 : 1; }
