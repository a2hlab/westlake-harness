#include "install_prepass_materializer.h"
#include "prepass_bundle.h"
#include <cerrno>

#if defined(__linux__) || defined(__OHOS__)
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#endif

namespace oh_adapter {
#if defined(__linux__) || defined(__OHOS__)
namespace {
class OwnedFd {
public:
    explicit OwnedFd(int value) noexcept : value_(value) {}
    ~OwnedFd()
    {
        // close must not replace the failure that prevented publication. Do
        // not retry close on EINTR: Linux has already released the descriptor.
        const int saved = errno;
        if (value_ >= 0) close(value_);
        errno = saved;
    }
    OwnedFd(const OwnedFd&) = delete;
    OwnedFd& operator=(const OwnedFd&) = delete;
    int Get() const noexcept { return value_; }
private:
    int value_;
};
}
#endif

bool WriteCanonicalPrepassFd(const std::string& payload, int* output) noexcept
{
    if (!output) { errno = EINVAL; return false; }
    *output = -1;
    if (payload.empty()) { errno = EINVAL; return false; }
    if (payload.size() > package_transaction::PrepassBundleCodec::MAX_PAYLOAD_BYTES) {
        errno = EFBIG; return false;
    }
#if defined(__linux__) || defined(__OHOS__)
    const OwnedFd fd(memfd_create("adapter-prepass", MFD_CLOEXEC | MFD_ALLOW_SEALING));
    if (fd.Get() < 0) return false;
    size_t offset = 0;
    while (offset < payload.size()) {
        const ssize_t count = write(fd.Get(), payload.data() + offset, payload.size() - offset);
        if (count < 0) { if (errno == EINTR) continue; return false; }
        if (count == 0) { errno = EIO; return false; }
        offset += static_cast<size_t>(count);
    }
    constexpr int seals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;
    if (fcntl(fd.Get(), F_ADD_SEALS, seals) < 0) return false;
    if (lseek(fd.Get(), 0, SEEK_SET) < 0) return false;
    const int result = fcntl(fd.Get(), F_DUPFD_CLOEXEC, 0);
    if (result < 0) return false;
    // Publish only after every fallible step; the temporary reference closes
    // on return, leaving exactly one immutable caller-owned descriptor.
    *output = result;
    return true;
#else
    errno = ENOTSUP;
    return false;
#endif
}
}
