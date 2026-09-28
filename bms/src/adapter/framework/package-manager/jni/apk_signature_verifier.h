/*
 * apk_signature_verifier.h
 *
 * Package-boundary, in-process APK Signature Scheme v2/v3 verifier.
 *
 * Operates only on an already-open, caller-owned file descriptor (the same
 * sealed snapshot fd that installs eventually publishes from). It never
 * reopens the APK by pathname, so verification, manifest parsing and
 * managed publication all observe identical bytes (open-once identity).
 *
 * V1 (JAR signing) is not accepted: L02.A01 requires at least APK Signature
 * Scheme v2, so an APK with only a v1 signature is treated as unsigned.
 *
 * This replaces the former Phase-1 stub that accepted any well-formed v2
 * signer block without verifying a cryptographic signature or content
 * digest. Every accepted result here has a real RSA/ECDSA signature checked
 * against the certificate embedded in the signing block, and the content
 * digest is recomputed from the actual file bytes and compared byte-for-byte
 * against the signed value.
 */
#ifndef APK_SIGNATURE_VERIFIER_H
#define APK_SIGNATURE_VERIFIER_H

#include <cstdint>
#include <string>

#include "apk_verify_result.h"

namespace oh_adapter {

class ApkSignatureVerifier {
public:
    /**
     * Verify APK Signature Scheme v2/v3 directly against `fd`.
     *
     * @param fd caller-owned, seekable, readable fd for the whole APK.
     *           Ownership/lifetime stays with the caller; this call never
     *           closes it.
     * @param minSchemeVersion 2 or 3. If 3, a v2-only APK is rejected.
     * @param out on success, populated with scheme version, whole-APK
     *            SHA-256, current signer certificate SHA-256(es) and (for
     *            v3) any parsed proof-of-rotation lineage.
     * @param error human-readable rejection reason on failure.
     * @return true only if a supported signature algorithm's cryptographic
     *         signature and content digest both verified successfully.
     */
    static bool VerifyFd(int fd, uint32_t minSchemeVersion,
                          ApkVerifiedIdentity* out, std::string* error);
    static bool VerifyFd(int fd, uint32_t minSchemeVersion,
                          uint32_t targetPlatformSdk,
                          ApkVerifiedIdentity* out, std::string* error);
};

}  // namespace oh_adapter

#endif  // APK_SIGNATURE_VERIFIER_H
