// sha256.h — self-contained minimal SHA-256 (no OpenSSL/libcrypto dependency).
//
// HP-2 host-only install-plan oracle (specs/001-hp2-apk-install). Provides
// just enough of SHA-256 to compute an apkSha256 identity for ApkFixture
// content in the install-plan model (research.md R3). This is NOT a
// general-purpose crypto library; it is scoped to this feature's needs.
//
// STUB: none — this is a real, complete SHA-256 implementation (FIPS 180-4),
// not a stub. It has no external dependency by design (plan.md Technical
// Context: "避免引入 OpenSSL/libcrypto 依赖，保持 host-only 自包含").

#ifndef HP2_INSTALL_PLAN_SHA256_H
#define HP2_INSTALL_PLAN_SHA256_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Computes the SHA-256 digest of `data[0..len)` into `out[0..32)`.
// `out` MUST point to at least 32 bytes. `data` may be NULL only if `len==0`.
void sha256(const unsigned char* data, size_t len, unsigned char out[32]);

#ifdef __cplusplus
}
#endif

#endif // HP2_INSTALL_PLAN_SHA256_H
