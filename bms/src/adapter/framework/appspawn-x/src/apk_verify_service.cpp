/**
 * APK verifier service implementation.
 *
 * The verifier service validates request identity and request frame first, then
 * calls ApkSignatureBridge on the immutable sealed memfd passed via SCM_RIGHTS.
 */

#include "apk_verify_service.h"
#include "apk_verify_protocol.h"
#include "appspawnx_runtime.h"
#include "spawn_msg.h"

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <errno.h>
#include <fcntl.h>
#include <string>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/uio.h>
#include <unistd.h>

namespace appspawnx {
namespace apkverify {

namespace {
constexpr uint32_t kExpectedFoundationUid = 5523;
constexpr char kExpectedPeerSec[] = "u:r:foundation:s0";
constexpr size_t kCmsgBufferBytes = 1024;
constexpr size_t kMaxApkSize = 1024ull * 1024ull * 1024ull;
constexpr int kRequiredSeals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;

bool writeAll(int fd, const void* data, size_t len) {
    const uint8_t* p = static_cast<const uint8_t*>(data);
    size_t left = len;
    while (left > 0) {
        ssize_t n = send(fd, p, left, MSG_NOSIGNAL);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;
        p += static_cast<size_t>(n);
        left -= static_cast<size_t>(n);
    }
    return true;
}

bool validateSourceFd(int fd) {
    struct stat st{};
    if (fstat(fd, &st) != 0) {
        LOGE("APK verify: fstat failed: %s", strerror(errno));
        return false;
    }
    if (!S_ISREG(st.st_mode)) {
        LOGE("APK verify: source fd is not regular file");
        return false;
    }
    if (st.st_size <= 0 || static_cast<size_t>(st.st_size) > kMaxApkSize) {
        LOGE("APK verify: invalid file size=%lld", (long long)st.st_size);
        return false;
    }
    int seals = fcntl(fd, F_GET_SEALS);
    if (seals < 0) {
        LOGE("APK verify: F_GET_SEALS failed: %s", strerror(errno));
        return false;
    }
    if ((seals & kRequiredSeals) != kRequiredSeals) {
        LOGE("APK verify: incomplete seals=0x%x (need mask 0x%x)", seals, kRequiredSeals);
        return false;
    }
    return true;
}
} // namespace

ApkVerifyService::ApkVerifyService(AppSpawnXRuntime* runtime)
    : runtime_(runtime) {
}

bool ApkVerifyService::hasFoundationPeer(int clientFd) {
    ucred cred{};
    socklen_t credLen = sizeof(cred);
    if (getsockopt(clientFd, SOL_SOCKET, SO_PEERCRED, &cred, &credLen) != 0) {
        LOGE("APK verify: SO_PEERCRED failed: errno=%s", strerror(errno));
        return false;
    }
    if (cred.uid != kExpectedFoundationUid) {
        LOGE("APK verify: peer uid=%d rejected (expected %u)", cred.uid, kExpectedFoundationUid);
        return false;
    }
    return true;
}

bool ApkVerifyService::hasFoundationSecurityContext(int clientFd) {
    char secCtx[128]{};
    socklen_t secLen = sizeof(secCtx);
    if (getsockopt(clientFd, SOL_SOCKET, SO_PEERSEC, secCtx, &secLen) != 0) {
        LOGE("APK verify: SO_PEERSEC failed: errno=%s", strerror(errno));
        return false;
    }
    const size_t expectedLen = sizeof(kExpectedPeerSec) - 1;
    const size_t actualLen = strnlen(secCtx, secLen);
    if (actualLen != expectedLen || memcmp(secCtx, kExpectedPeerSec, expectedLen) != 0) {
        LOGE("APK verify: peer security context '%s' rejected", secCtx);
        return false;
    }
    return true;
}

bool ApkVerifyService::readHeaderAndFd(int clientFd, uint32_t* outMinScheme, int* outFd) {
    ApkVerifyRequestHeader req{};
    std::array<uint8_t, kCmsgBufferBytes> cmsgBuf{};
    iovec iov{&req, sizeof(req)};
    msghdr msg{};
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    msg.msg_control = cmsgBuf.data();
    msg.msg_controllen = cmsgBuf.size();

    int recvFlags = MSG_WAITALL;
#ifdef MSG_CMSG_CLOEXEC
    recvFlags |= MSG_CMSG_CLOEXEC;
#endif
    ssize_t n = recvmsg(clientFd, &msg, recvFlags);

    std::array<int, 8> receivedFds{};
    size_t fdCount = 0;
    bool controlValid = true;
    for (cmsghdr* cmsg = CMSG_FIRSTHDR(&msg); cmsg; cmsg = CMSG_NXTHDR(&msg, cmsg)) {
        if (cmsg->cmsg_level != SOL_SOCKET || cmsg->cmsg_type != SCM_RIGHTS) {
            LOGE("APK verify: unexpected cmsg (%d,%d)", cmsg->cmsg_level, cmsg->cmsg_type);
            controlValid = false;
            continue;
        }
        if (cmsg->cmsg_len < CMSG_LEN(0)) {
            LOGE("APK verify: malformed cmsg length=%zu", static_cast<size_t>(cmsg->cmsg_len));
            controlValid = false;
            continue;
        }
        size_t payloadLen = cmsg->cmsg_len - CMSG_LEN(0);
        if (payloadLen == 0 || payloadLen % sizeof(int) != 0) {
            LOGE("APK verify: invalid cmsg fd payload len=%zu", payloadLen);
            controlValid = false;
            continue;
        }
        const int* fds = reinterpret_cast<const int*>(CMSG_DATA(cmsg));
        for (size_t i = 0; i < payloadLen / sizeof(int); ++i) {
            if (fdCount < receivedFds.size()) {
                receivedFds[fdCount] = fds[i];
            } else {
                close(fds[i]);
                controlValid = false;
            }
            ++fdCount;
        }
    }

    const size_t retainedCount = fdCount < receivedFds.size() ? fdCount : receivedFds.size();
    if (n != static_cast<ssize_t>(sizeof(req))) {
        LOGE("APK verify: request read failed n=%zd", n);
        controlValid = false;
    }
    if (msg.msg_flags & (MSG_CTRUNC | MSG_TRUNC)) {
        LOGE("APK verify: request/control truncated");
        controlValid = false;
    }
    if (req.magic != kVerifyRequestMagic) {
        LOGE("APK verify: invalid magic=0x%08x", req.magic);
        controlValid = false;
    }
    if (req.reserved1 != 0 || req.reserved2 != 0) {
        LOGE("APK verify: reserved must be 0");
        controlValid = false;
    }
    if (req.minScheme != 2 && req.minScheme != 3) {
        LOGE("APK verify: invalid minScheme=%u", req.minScheme);
        controlValid = false;
    }
    if (!controlValid || fdCount != 1) {
        LOGE("APK verify: expected exactly one FD, got %zu", fdCount);
        for (size_t i = 0; i < retainedCount; ++i) close(receivedFds[i]);
        return false;
    }
    int receivedFd = receivedFds[0];
#ifndef MSG_CMSG_CLOEXEC
    if (fcntl(receivedFd, F_SETFD, FD_CLOEXEC) != 0) {
        LOGE("APK verify: FD_CLOEXEC failed: %s", strerror(errno));
        close(receivedFd);
        return false;
    }
#endif
    if (!validateSourceFd(receivedFd)) {
        close(receivedFd);
        return false;
    }

    *outMinScheme = req.minScheme;
    *outFd = receivedFd;
    return true;
}

bool ApkVerifyService::sendError(int clientFd, int status) {
    ApkVerifyResponseHeader hdr{};
    hdr.magic = kVerifyResponseMagic;
    hdr.status = status;
    hdr.payloadLen = 0;
    hdr.reserved = 0;
    return writeAll(clientFd, &hdr, sizeof(hdr));
}

bool ApkVerifyService::sendResult(int clientFd, const std::string& payload) {
    if (payload.size() > kVerifyMaxResponse ||
        payload.size() > static_cast<size_t>(UINT32_MAX)) {
        LOGE("APK verify: payload too large: %zu", payload.size());
        return false;
    }
    ApkVerifyResponseHeader hdr{};
    hdr.magic = kVerifyResponseMagic;
    hdr.status = 0;
    hdr.payloadLen = static_cast<uint32_t>(payload.size());
    hdr.reserved = 0;
    if (!writeAll(clientFd, &hdr, sizeof(hdr))) return false;
    if (hdr.payloadLen == 0) return true;
    return writeAll(clientFd, payload.data(), payload.size());
}

bool ApkVerifyService::handleClient(int clientFd) {
    if (!hasFoundationPeer(clientFd) || !hasFoundationSecurityContext(clientFd)) {
        return sendError(clientFd, -1001);
    }
    uint32_t minScheme = 0;
    int receivedFd = -1;
    if (!readHeaderAndFd(clientFd, &minScheme, &receivedFd)) {
        return sendError(clientFd, -1002);
    }
    if (!runtime_) {
        close(receivedFd);
        return sendError(clientFd, -1005);
    }

    char path[64];
    std::snprintf(path, sizeof(path), "/proc/self/fd/%d", receivedFd);
    std::string payload;
    int rc = runtime_->verifyApk(path, static_cast<int>(minScheme), payload);
    close(receivedFd);
    if (rc != 0) return sendError(clientFd, rc);
    if (payload.empty()) return sendError(clientFd, -1006);
    return sendResult(clientFd, payload);
}

} // namespace apkverify
} // namespace appspawnx
