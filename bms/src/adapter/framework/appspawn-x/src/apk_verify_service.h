/**
 * Dedicated APK verifier service handler for appspawn-x.
 *
 * Responsibilities:
 * - Validate peer identity (SO_PEERCRED + SO_PEERCRED UID and SO_PEERCRED sec label).
 * - Receive immutable APK FD through SCM_RIGHTS via recvmsg.
 * - Require the BMS-owned immutable sealed snapshot.
 * - Execute signature verification through AppSpawnXRuntime callback.
 * - Return fail-closed response payload.
 */
#pragma once

#include <cstdint>
#include <string>

namespace appspawnx {
class AppSpawnXRuntime;

namespace apkverify {
class ApkVerifyService {
public:
    explicit ApkVerifyService(AppSpawnXRuntime* runtime);

    bool handleClient(int clientFd);
private:
    AppSpawnXRuntime* runtime_;

    bool hasFoundationPeer(int clientFd);
    bool hasFoundationSecurityContext(int clientFd);
    bool readHeaderAndFd(int clientFd, uint32_t* outMinScheme, int* outFd);
    bool sendError(int clientFd, int status);
    bool sendResult(int clientFd, const std::string& payload);
};
} // namespace apkverify
} // namespace appspawnx
