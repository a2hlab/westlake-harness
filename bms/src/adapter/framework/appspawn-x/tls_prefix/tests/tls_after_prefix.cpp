#include <stdint.h>

namespace {

alignas(8) thread_local uint64_t g_tls_after_prefix = 0x5a17c0deULL;

} // namespace

extern "C" uint64_t westlake_tls_fixture_dso_value() {
  return g_tls_after_prefix;
}
