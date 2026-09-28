/*
 * Host transport tests for the verify-slice router.
 *
 * These tests pin the important stream invariant: protocol detection peeks
 * ordinary bytes only, and exactly one later recvmsg owns the SCM_RIGHTS FD.
 */

#include "apk_verify_protocol.h"

#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <sys/socket.h>
#include <sys/uio.h>
#include <unistd.h>

namespace {

using appspawnx::apkverify::ApkVerifyRequestHeader;

int countOpenFds() {
    int count = 0;
    const int maxFd = getdtablesize();
    for (int fd = 0; fd < maxFd; ++fd) {
        if (fcntl(fd, F_GETFD) >= 0) ++count;
    }
    return count;
}

int makeFileFd() {
    char path[] = "/tmp/apkverify_transport_XXXXXX";
    int fd = mkstemp(path);
    assert(fd >= 0);
    assert(unlink(path) == 0);
    constexpr char kPayload[] = "immutable-test-payload";
    assert(write(fd, kPayload, sizeof(kPayload)) ==
           static_cast<ssize_t>(sizeof(kPayload)));
    assert(lseek(fd, 0, SEEK_SET) == 0);
    return fd;
}

void sendFrame(int sock, const ApkVerifyRequestHeader& frame,
               const int* fds, size_t fdCount) {
    std::array<uint8_t, CMSG_SPACE(sizeof(int) * 4)> control{};
    iovec iov{const_cast<ApkVerifyRequestHeader*>(&frame), sizeof(frame)};
    msghdr msg{};
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    if (fdCount > 0) {
        assert(fdCount <= 4);
        msg.msg_control = control.data();
        msg.msg_controllen = CMSG_SPACE(sizeof(int) * fdCount);
        cmsghdr* cmsg = CMSG_FIRSTHDR(&msg);
        assert(cmsg != nullptr);
        cmsg->cmsg_level = SOL_SOCKET;
        cmsg->cmsg_type = SCM_RIGHTS;
        cmsg->cmsg_len = CMSG_LEN(sizeof(int) * fdCount);
        memcpy(CMSG_DATA(cmsg), fds, sizeof(int) * fdCount);
    }
    assert(sendmsg(sock, &msg, 0) == static_cast<ssize_t>(sizeof(frame)));
}

struct ReceivedFrame {
    ApkVerifyRequestHeader header{};
    std::array<int, 4> fds{};
    size_t fdCount{0};
};

ReceivedFrame receiveFrame(int sock) {
    ReceivedFrame result{};
    std::array<uint8_t, CMSG_SPACE(sizeof(int) * 4)> control{};
    iovec iov{&result.header, sizeof(result.header)};
    msghdr msg{};
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    msg.msg_control = control.data();
    msg.msg_controllen = control.size();
    assert(recvmsg(sock, &msg, MSG_WAITALL) ==
           static_cast<ssize_t>(sizeof(result.header)));
    assert((msg.msg_flags & (MSG_CTRUNC | MSG_TRUNC)) == 0);
    for (cmsghdr* cmsg = CMSG_FIRSTHDR(&msg); cmsg;
         cmsg = CMSG_NXTHDR(&msg, cmsg)) {
        assert(cmsg->cmsg_level == SOL_SOCKET);
        assert(cmsg->cmsg_type == SCM_RIGHTS);
        assert(cmsg->cmsg_len >= CMSG_LEN(0));
        const size_t bytes = cmsg->cmsg_len - CMSG_LEN(0);
        assert(bytes % sizeof(int) == 0);
        const int* fds = reinterpret_cast<const int*>(CMSG_DATA(cmsg));
        for (size_t i = 0; i < bytes / sizeof(int); ++i) {
            assert(result.fdCount < result.fds.size());
            result.fds[result.fdCount++] = fds[i];
        }
    }
    return result;
}

void closeReceived(ReceivedFrame* frame) {
    for (size_t i = 0; i < frame->fdCount; ++i) close(frame->fds[i]);
    frame->fdCount = 0;
}

void testBytePeekPreservesRights() {
    int pair[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) == 0);
    int source = makeFileFd();
    ApkVerifyRequestHeader request{
        appspawnx::apkverify::kVerifyRequestMagic, 2, 0, 0};
    sendFrame(pair[0], request, &source, 1);

    const int beforePeek = countOpenFds();
    uint32_t magic = 0;
    assert(recv(pair[1], &magic, sizeof(magic), MSG_PEEK | MSG_WAITALL) ==
           static_cast<ssize_t>(sizeof(magic)));
    assert(magic == appspawnx::apkverify::kVerifyRequestMagic);
    assert(countOpenFds() == beforePeek);

    ReceivedFrame received = receiveFrame(pair[1]);
    assert(memcmp(&received.header, &request, sizeof(request)) == 0);
    assert(received.fdCount == 1);
    assert(countOpenFds() == beforePeek + 1);

    char payload[64]{};
    assert(pread(received.fds[0], payload, sizeof(payload), 0) > 0);
    assert(strncmp(payload, "immutable-test-payload", 22) == 0);
    closeReceived(&received);
    assert(countOpenFds() == beforePeek);

    close(source);
    close(pair[0]);
    close(pair[1]);
}

void testZeroAndTwoRightsAreObservable() {
    ApkVerifyRequestHeader request{
        appspawnx::apkverify::kVerifyRequestMagic, 2, 0, 0};

    int pair[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) == 0);
    sendFrame(pair[0], request, nullptr, 0);
    ReceivedFrame zero = receiveFrame(pair[1]);
    assert(zero.fdCount == 0);
    close(pair[0]);
    close(pair[1]);

    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) == 0);
    int sources[2] = {makeFileFd(), makeFileFd()};
    sendFrame(pair[0], request, sources, 2);
    ReceivedFrame two = receiveFrame(pair[1]);
    assert(two.fdCount == 2);
    closeReceived(&two);
    close(sources[0]);
    close(sources[1]);
    close(pair[0]);
    close(pair[1]);
}

void testLegacyAndBinaryPrefixesRemainInStream() {
    int pair[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) == 0);
    constexpr char kLegacyPayload[] = "legacy-payload";
    const uint32_t payloadLen = sizeof(kLegacyPayload);
    assert(write(pair[0], &payloadLen, sizeof(payloadLen)) == sizeof(payloadLen));
    assert(write(pair[0], kLegacyPayload, sizeof(kLegacyPayload)) ==
           sizeof(kLegacyPayload));

    uint32_t peek = 0;
    assert(recv(pair[1], &peek, sizeof(peek), MSG_PEEK | MSG_WAITALL) ==
           sizeof(peek));
    assert(peek == payloadLen);
    uint32_t consumedLen = 0;
    assert(read(pair[1], &consumedLen, sizeof(consumedLen)) == sizeof(consumedLen));
    std::array<char, sizeof(kLegacyPayload)> consumedPayload{};
    assert(read(pair[1], consumedPayload.data(), consumedPayload.size()) ==
           static_cast<ssize_t>(consumedPayload.size()));
    assert(memcmp(consumedPayload.data(), kLegacyPayload, consumedPayload.size()) == 0);
    close(pair[0]);
    close(pair[1]);

    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, pair) == 0);
    std::array<uint8_t, 64> binary{};
    const uint32_t binaryMagic = 0x1234abcd;
    memcpy(binary.data(), &binaryMagic, sizeof(binaryMagic));
    assert(write(pair[0], binary.data(), binary.size()) ==
           static_cast<ssize_t>(binary.size()));
    peek = 0;
    assert(recv(pair[1], &peek, sizeof(peek), MSG_PEEK | MSG_WAITALL) ==
           sizeof(peek));
    assert(peek == binaryMagic);
    std::array<uint8_t, 64> consumedBinary{};
    assert(read(pair[1], consumedBinary.data(), consumedBinary.size()) ==
           static_cast<ssize_t>(consumedBinary.size()));
    assert(consumedBinary == binary);
    close(pair[0]);
    close(pair[1]);
}

} // namespace

int main() {
    testBytePeekPreservesRights();
    testZeroAndTwoRightsAreObservable();
    testLegacyAndBinaryPrefixesRemainInStream();
    std::cout << "PASS apk_verify_transport\n";
    return 0;
}
