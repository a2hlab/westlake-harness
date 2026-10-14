/**
 * BMS-side package-boundary native verifier client.
 *
 * Ingress is opened once and the same caller-owned fd is then verified
 * in-process by ApkSignatureVerifier (no AppSpawnX socket, no ART/Java
 * bridge). Linux host tests may use a sealed memfd snapshot; OHOS package
 * install keeps the BMS stream_install regular fd because foundation policy
 * rejects fstat() on the sealed memfd path.
 */
#pragma once

#include "apk_verify_result.h"

#include <string>

namespace oh_adapter {

struct VerifiedApkSession {
    int sealedFd = -1;
    ApkVerifiedIdentity identity;
};

class ApkVerifierClient {
public:
    static int OpenAndVerify(const std::string& apkPath, uint32_t minSchemeVersion,
                             VerifiedApkSession* out, std::string* error);
    static void Close(VerifiedApkSession* session);
};

}  // namespace oh_adapter
