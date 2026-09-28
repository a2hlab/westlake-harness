#include "apk_verifier_client.h"
#include "apk_verified_session_c_api.h"
#include "../../appspawn-x/src/apk_verify_protocol.h"

#include <array>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <openssl/sha.h>
#include <string>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>
#include <vector>

namespace {

constexpr int kRequiredSeals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;

void PutU16(std::vector<uint8_t>& output, uint16_t value)
{
    output.push_back(static_cast<uint8_t>(value >> 8));
    output.push_back(static_cast<uint8_t>(value));
}

void PutU32(std::vector<uint8_t>& output, uint32_t value)
{
    output.push_back(static_cast<uint8_t>(value >> 24));
    output.push_back(static_cast<uint8_t>(value >> 16));
    output.push_back(static_cast<uint8_t>(value >> 8));
    output.push_back(static_cast<uint8_t>(value));
}

void PutBlob(std::vector<uint8_t>& output, const uint8_t* data, size_t size)
{
    PutU32(output, static_cast<uint32_t>(size));
    output.insert(output.end(), data, data + size);
}

bool SendAll(int fd, const void* data, size_t size)
{
    const auto* cursor = static_cast<const uint8_t*>(data);
    size_t offset = 0;
    while (offset < size) {
        ssize_t count = send(fd, cursor + offset, size - offset, MSG_NOSIGNAL);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return false;
        offset += static_cast<size_t>(count);
    }
    return true;
}

std::vector<uint8_t> ReadFd(int fd)
{
    struct stat st{};
    if (fstat(fd, &st) != 0 || st.st_size <= 0) return {};
    std::vector<uint8_t> result(static_cast<size_t>(st.st_size));
    size_t offset = 0;
    while (offset < result.size()) {
        ssize_t count = pread(fd, result.data() + offset, result.size() - offset,
                              static_cast<off_t>(offset));
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return {};
        offset += static_cast<size_t>(count);
    }
    return result;
}

int CreateListener(const std::string& socketPath)
{
    unlink(socketPath.c_str());
    int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (fd < 0) return -1;
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, socketPath.c_str(), socketPath.size() + 1);
    socklen_t length = static_cast<socklen_t>(
        offsetof(sockaddr_un, sun_path) + socketPath.size() + 1);
    if (bind(fd, reinterpret_cast<sockaddr*>(&address), length) != 0 ||
        listen(fd, 1) != 0) {
        close(fd);
        return -1;
    }
    return fd;
}

void ServeOnce(int listener, const std::string& ingressPath, bool corruptDigest,
               bool* observedSealedFd)
{
    int client = accept4(listener, nullptr, nullptr, SOCK_CLOEXEC);
    if (client < 0) return;

    appspawnx::apkverify::ApkVerifyRequestHeader request{};
    iovec iov{&request, sizeof(request)};
    std::array<uint8_t, CMSG_SPACE(sizeof(int) * 2)> control{};
    msghdr message{};
    message.msg_iov = &iov;
    message.msg_iovlen = 1;
    message.msg_control = control.data();
    message.msg_controllen = control.size();
    ssize_t count = recvmsg(client, &message, MSG_WAITALL | MSG_CMSG_CLOEXEC);

    int receivedFd = -1;
    size_t fdCount = 0;
    for (cmsghdr* cmsg = CMSG_FIRSTHDR(&message); cmsg != nullptr;
         cmsg = CMSG_NXTHDR(&message, cmsg)) {
        if (cmsg->cmsg_level != SOL_SOCKET || cmsg->cmsg_type != SCM_RIGHTS) continue;
        const size_t payloadSize = cmsg->cmsg_len - CMSG_LEN(0);
        const int* fds = reinterpret_cast<const int*>(CMSG_DATA(cmsg));
        for (size_t i = 0; i < payloadSize / sizeof(int); ++i) {
            if (fdCount == 0) receivedFd = fds[i];
            else close(fds[i]);
            ++fdCount;
        }
    }
    if (count != static_cast<ssize_t>(sizeof(request)) ||
        request.magic != appspawnx::apkverify::kVerifyRequestMagic ||
        request.minScheme != 2 || fdCount != 1 || receivedFd < 0) {
        if (receivedFd >= 0) close(receivedFd);
        close(client);
        return;
    }

    const int seals = fcntl(receivedFd, F_GET_SEALS);
    errno = 0;
    const char mutation = 'x';
    const bool writeRejected = pwrite(receivedFd, &mutation, 1, 0) < 0 && errno == EPERM;
    *observedSealedFd = (seals & kRequiredSeals) == kRequiredSeals && writeRejected;

    const std::vector<uint8_t> snapshot = ReadFd(receivedFd);
    std::array<uint8_t, SHA256_DIGEST_LENGTH> digest{};
    SHA256(snapshot.data(), snapshot.size(), digest.data());
    if (corruptDigest) digest[0] ^= 0xff;

    // Swap the ingress pathname after receipt. The response still describes the
    // already sealed object, so the caller must not fall back to this pathname.
    const std::string oldPath = ingressPath + ".old";
    unlink(oldPath.c_str());
    rename(ingressPath.c_str(), oldPath.c_str());
    std::ofstream replacement(ingressPath, std::ios::binary | std::ios::trunc);
    replacement << "attacker replacement";
    replacement.close();

    const std::array<uint8_t, 5> certificate{0x30, 0x03, 0x01, 0x02, 0x03};
    std::vector<uint8_t> payload;
    PutU32(payload, 0x41535631u);
    PutU16(payload, 1);
    PutU16(payload, 2);
    PutU32(payload, 0);
    PutBlob(payload, digest.data(), digest.size());
    PutU32(payload, 1);
    PutU32(payload, 1);
    PutBlob(payload, certificate.data(), certificate.size());
    PutU32(payload, 0);

    appspawnx::apkverify::ApkVerifyResponseHeader response{};
    response.magic = appspawnx::apkverify::kVerifyResponseMagic;
    response.payloadLen = static_cast<uint32_t>(payload.size());
    SendAll(client, &response, sizeof(response));
    SendAll(client, payload.data(), payload.size());
    close(receivedFd);
    close(client);
}

void WriteIngress(const std::string& path, const std::string& contents)
{
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output << contents;
}

}  // namespace

int main()
{
    const char* tempRoot = getenv("TMPDIR");
    if (tempRoot == nullptr || tempRoot[0] == '\0') {
        std::cerr << "TMPDIR must identify a project-local test output root" << std::endl;
        return 2;
    }
    const std::string base = std::string(tempRoot) +
        "/oh_adapter_verify_client_" + std::to_string(getpid());
    const std::string socketPath = base + ".sock";
    const std::string ingressPath = base + ".apk";
    const std::string original = "signed snapshot bytes used by the verifier";

    WriteIngress(ingressPath, original);
    int listener = CreateListener(socketPath);
    if (listener < 0) return 1;
    bool observedSealedFd = false;
    std::thread server(ServeOnce, listener, ingressPath, false, &observedSealedFd);

    oh_adapter::VerifiedApkSession session;
    std::string error;
    int result = oh_adapter::ApkVerifierClient::OpenAndVerifyForTesting(
        ingressPath, 2, socketPath, &session, &error);
    server.join();
    close(listener);
    unlink(socketPath.c_str());
    const std::vector<uint8_t> installedSnapshot = ReadFd(session.sealedFd);
    if (result != OH_ADAPTER_APK_VERIFY_OK || !observedSealedFd || session.sealedFd < 0 ||
        std::string(installedSnapshot.begin(), installedSnapshot.end()) != original) {
        std::cerr << "sealed snapshot success case failed: rc=" << result
                  << " error=" << error << std::endl;
        return 1;
    }
    oh_adapter::ApkVerifierClient::Close(&session);

    WriteIngress(ingressPath, original);
    listener = CreateListener(socketPath);
    if (listener < 0) return 1;
    observedSealedFd = false;
    std::thread corruptServer(ServeOnce, listener, ingressPath, true, &observedSealedFd);
    result = oh_adapter::ApkVerifierClient::OpenAndVerifyForTesting(
        ingressPath, 2, socketPath, &session, &error);
    corruptServer.join();
    close(listener);
    unlink(socketPath.c_str());
    unlink(ingressPath.c_str());
    unlink((ingressPath + ".old").c_str());
    if (result != OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED || session.sealedFd >= 0 ||
        !observedSealedFd) {
        std::cerr << "wrong digest was not rejected: rc=" << result
                  << " error=" << error << std::endl;
        return 1;
    }

    std::cout << "PASS apk_verifier_client_linux" << std::endl;
    return 0;
}
