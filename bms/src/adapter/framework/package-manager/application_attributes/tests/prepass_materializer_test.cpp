#include "install_prepass_materializer.h"
#include "prepass_bundle.h"
#include "sha256.h"
#include <gtest/gtest.h>
#include <algorithm>
#include <cerrno>
#include <cstdarg>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {
enum class Fault { NONE, SHORT_EINTR, CREATE, ZERO_WRITE, NO_SPACE, DUP, SEAL, SEEK };
struct FaultState { Fault mode = Fault::NONE; int fd = -1, duplicate = -1, writes = 0; };
thread_local FaultState fault;
struct FaultScope {
    explicit FaultScope(Fault mode) { fault = {}; fault.mode = mode; }
    ~FaultScope() { fault = {}; }
};
struct OwnedFd { int fd = -1; ~OwnedFd() { if (fd >= 0) close(fd); } };
size_t FdCount()
{
    DIR* dir = opendir("/proc/self/fd");
    if (!dir) throw std::runtime_error("fixture FD count unavailable");
    size_t count = 0;
    while (const auto* entry = readdir(dir)) if (entry->d_name[0] != '.') ++count;
    closedir(dir); return count;
}
std::string Hash(const std::string& bytes)
{
    unsigned char digest[32]; sha256(reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size(), digest);
    constexpr char hex[] = "0123456789abcdef"; std::string result;
    for (auto byte : digest) { result += hex[byte >> 4]; result += hex[byte & 15]; }
    return result;
}
using namespace oh_adapter::package_transaction;
wire::PrepassBundleRecord Record(bool native)
{
    PrepassBundle b;
    b.requestId = "fd-request"; b.packageName = "org.example.fd"; b.userId = 17; b.packageGeneration = "generation-3";
    b.apkDigest = std::string(64, 'a'); b.contractDigest = std::string(64, 'b'); b.policyDigest = std::string(64, 'c');
    b.toolDigest = std::string(64, 'd'); b.topologyDigest = std::string(64, 'e'); b.runtimeGenerationSealDigest = std::string(64, 'f');
    if (native) {
        std::ifstream stream(std::string(ELF_FIXTURE_DIRECTORY) + "/consumer64.elf", std::ios::binary);
        if (!stream) throw std::runtime_error("real ELF fixture missing");
        std::string bytes(std::istreambuf_iterator<char>(stream), {});
        ElfPrepassInput input; input.apkSha256 = b.apkDigest; input.entryName = "lib/x86_64/libconsumer.so";
        input.abi = "x86_64"; input.expectedElfSha256 = Hash(bytes); input.bytes.assign(bytes.begin(), bytes.end());
        auto result = InspectElf(input);
        if (result.verdict != ElfPrepassVerdict::ANALYZED) throw std::runtime_error(result.reason);
        b.disposition = PrepassDisposition::HAS_NATIVE_ELF; b.nativeEntryCount = 1; b.elfFacts.push_back(result.facts.value());
    }
    wire::PrepassBundleRecord record; std::string error;
    if (!PrepassBundleCodec::Encode(b, &record, &error)) throw std::runtime_error(error);
    return record;
}
}

// Link-time substitution at the OS syscall edge only. Successful writes,
// copies and seals always reach the real kernel; no business result is mocked.
extern "C" int __real_memfd_create(const char*, unsigned int);
extern "C" ssize_t __real_write(int, const void*, size_t);
extern "C" int __real_fcntl(int, int, ...);
extern "C" off_t __real_lseek(int, off_t, int);
extern "C" int __wrap_memfd_create(const char* name, unsigned int flags)
{
    if (fault.mode == Fault::CREATE) { errno = EMFILE; return -1; }
    fault.fd = __real_memfd_create(name, flags); return fault.fd;
}
extern "C" ssize_t __wrap_write(int fd, const void* bytes, size_t size)
{
    if (fd != fault.fd) return __real_write(fd, bytes, size);
    const int call = fault.writes++;
    if (fault.mode == Fault::ZERO_WRITE) return 0;
    if (fault.mode == Fault::NO_SPACE && call > 0) { errno = ENOSPC; return -1; }
    if (fault.mode == Fault::SHORT_EINTR && call == 0) { errno = EINTR; return -1; }
    if (fault.mode == Fault::SHORT_EINTR || fault.mode == Fault::NO_SPACE) size = std::min(size, size_t{7});
    return __real_write(fd, bytes, size);
}
extern "C" int __wrap_fcntl(int fd, int command, ...)
{
    // Only these fcntl commands occur in the linked production target/tests.
    if (command == F_GETFD || command == F_GETFL || command == F_GET_SEALS) return __real_fcntl(fd, command);
    if (command != F_DUPFD_CLOEXEC && command != F_ADD_SEALS) std::abort();
    va_list ap; va_start(ap, command); int value = va_arg(ap, int); va_end(ap);
    if (fd == fault.fd && command == F_DUPFD_CLOEXEC && fault.mode == Fault::DUP) { errno = EMFILE; return -1; }
    if (fd == fault.fd && command == F_ADD_SEALS && fault.mode == Fault::SEAL) { errno = EPERM; return -1; }
    int result = __real_fcntl(fd, command, value);
    if (fd == fault.fd && command == F_DUPFD_CLOEXEC) fault.duplicate = result;
    return result;
}
extern "C" off_t __wrap_lseek(int fd, off_t offset, int whence)
{
    if (fd == fault.fd && fault.mode == Fault::SEEK) { errno = EIO; return -1; }
    return __real_lseek(fd, offset, whence);
}

namespace {
void CheckMaterialization(const wire::PrepassBundleRecord& record, Fault mode)
{
    const auto before = FdCount();
    {
        FaultScope faults(mode); OwnedFd owned;
        ASSERT_TRUE(oh_adapter::WriteCanonicalPrepassFd(record.canonicalPayload, &owned.fd)) << "SPC51_SEALED_FD_EXPECTED errno=" << errno;
        ASSERT_GE(owned.fd, 0); EXPECT_EQ(FdCount(), before + 1);
        EXPECT_EQ(fcntl(owned.fd, F_GETFD) & FD_CLOEXEC, FD_CLOEXEC);
        constexpr int seals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;
        EXPECT_EQ(fcntl(owned.fd, F_GET_SEALS) & seals, seals);
        EXPECT_EQ(lseek(owned.fd, 0, SEEK_CUR), 0);
        struct stat st{}; ASSERT_EQ(fstat(owned.fd, &st), 0);
        EXPECT_EQ(static_cast<uint64_t>(st.st_size), record.canonicalPayload.size());
        std::string readback(record.canonicalPayload.size(), '\0');
        ASSERT_EQ(read(owned.fd, readback.data(), readback.size()), static_cast<ssize_t>(readback.size()));
        EXPECT_EQ(readback, record.canonicalPayload); EXPECT_EQ(Hash(readback), record.payloadSha256);
        PrepassBundle decoded; std::string error;
        EXPECT_TRUE(PrepassBundleCodec::DecodePayload(readback, record.payloadSha256, record.binding, &decoded, &error)) << error;
        errno = 0; EXPECT_EQ(pwrite(owned.fd, "x", 1, 0), -1); EXPECT_EQ(errno, EPERM);
        errno = 0; EXPECT_EQ(ftruncate(owned.fd, 0), -1); EXPECT_EQ(errno, EPERM);
        errno = 0; EXPECT_EQ(ftruncate(owned.fd, st.st_size + 1), -1); EXPECT_EQ(errno, EPERM);
        errno = 0; void* view = mmap(nullptr, readback.size(), PROT_READ | PROT_WRITE, MAP_SHARED, owned.fd, 0);
        EXPECT_EQ(view, MAP_FAILED); EXPECT_EQ(errno, EPERM); if (view != MAP_FAILED) munmap(view, readback.size());
        if (mode == Fault::SHORT_EINTR) EXPECT_GT(fault.writes, 2);
        ASSERT_GE(fault.duplicate, 0); EXPECT_EQ(fault.duplicate, owned.fd);
        errno = 0; EXPECT_EQ(fcntl(fault.fd, F_GETFD), -1); EXPECT_EQ(errno, EBADF);
    }
    EXPECT_EQ(FdCount(), before);
}
TEST(SPC_51_Contract, Valid)
{
    for (bool native : {false, true}) {
        const auto record = Record(native);
        CheckMaterialization(record, Fault::NONE);
        CheckMaterialization(record, Fault::SHORT_EINTR);
    }
}
TEST(SPC_51_Contract, Rejected)
{
    const auto record = Record(false);
    for (const auto item : {std::pair{Fault::CREATE, EMFILE}, {Fault::ZERO_WRITE, EIO}, {Fault::NO_SPACE, ENOSPC},
            {Fault::DUP, EMFILE}, {Fault::SEAL, EPERM}, {Fault::SEEK, EIO}}) {
        SCOPED_TRACE(static_cast<int>(item.first)); const auto before = FdCount();
        FaultScope faults(item.first); int result = 12345; errno = 0;
        EXPECT_FALSE(oh_adapter::WriteCanonicalPrepassFd(record.canonicalPayload, &result));
        EXPECT_EQ(result, -1); EXPECT_EQ(errno, item.second);
        if (fault.fd >= 0) { errno = 0; EXPECT_EQ(fcntl(fault.fd, F_GETFD), -1); EXPECT_EQ(errno, EBADF); }
        if (fault.duplicate >= 0) { errno = 0; EXPECT_EQ(fcntl(fault.duplicate, F_GETFD), -1); EXPECT_EQ(errno, EBADF); }
        EXPECT_EQ(FdCount(), before);
    }
    const auto before = FdCount();
    int result = 12345; errno = 0;
    EXPECT_FALSE(oh_adapter::WriteCanonicalPrepassFd({}, &result)); EXPECT_EQ(result, -1); EXPECT_EQ(errno, EINVAL);
    EXPECT_FALSE(oh_adapter::WriteCanonicalPrepassFd(record.canonicalPayload, nullptr)); EXPECT_EQ(errno, EINVAL);
    EXPECT_FALSE(oh_adapter::WriteCanonicalPrepassFd(std::string(PrepassBundleCodec::MAX_PAYLOAD_BYTES + 1, 'x'), &result));
    EXPECT_EQ(result, -1); EXPECT_EQ(errno, EFBIG); EXPECT_EQ(FdCount(), before);
}
}
