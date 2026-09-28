#include "fn01_secure_store.h"

#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <sstream>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace bridge::fn01::topology {
namespace {

constexpr mode_t kPrivateDirectoryMode = 0700;
constexpr mode_t kPrivateFileMode = 0600;

void SetError(std::string *error, const char *operation, int errorNumber)
{
    if (error == nullptr) {
        return;
    }
    std::ostringstream stream;
    stream << operation << " errno=" << errorNumber
           << " message=" << std::strerror(errorNumber);
    *error = stream.str();
}

bool SameObject(const struct stat &left, const struct stat &right)
{
    return left.st_dev == right.st_dev && left.st_ino == right.st_ino;
}

bool IsPrivateOwnedDirectory(const struct stat &value, uid_t owner)
{
    return S_ISDIR(value.st_mode) && value.st_uid == owner &&
        (value.st_mode & 077) == 0;
}

bool IsPrivateOwnedRegularFile(const struct stat &value, uid_t owner)
{
    return S_ISREG(value.st_mode) && value.st_uid == owner &&
        value.st_nlink == 1 && (value.st_mode & 077) == 0;
}

int OpenPrivateRegularAt(int directoryFd, const char *name, uid_t owner,
    int accessFlags, struct stat *openedStat, std::string *error)
{
    struct stat before {};
    bool existed = true;
    if (fstatat(directoryFd, name, &before, AT_SYMLINK_NOFOLLOW) != 0) {
        if (errno != ENOENT) {
            SetError(error, "fstatat", errno);
            return -1;
        }
        existed = false;
    } else if (!IsPrivateOwnedRegularFile(before, owner)) {
        SetError(error, "unsafe-existing-file", EINVAL);
        return -1;
    }

    int flags = accessFlags | O_CLOEXEC | O_NOFOLLOW;
    if (existed) {
        flags |= O_NOCTTY;
    } else {
        flags |= O_CREAT | O_EXCL | O_NOCTTY;
    }
    const int fd = openat(directoryFd, name, flags, kPrivateFileMode);
    if (fd < 0) {
        SetError(error, "openat", errno);
        return -1;
    }

    struct stat after {};
    if (fstat(fd, &after) != 0 ||
        !IsPrivateOwnedRegularFile(after, owner) ||
        (existed && !SameObject(before, after))) {
        const int saved = errno == 0 ? EINVAL : errno;
        close(fd);
        SetError(error, "unsafe-opened-file", saved);
        return -1;
    }
    *openedStat = after;
    return fd;
}

}  // namespace

StoreOpenStatus AcquireRecoveredStoreLease(const char *parentPath,
    const char *storeName, SecureStoreLease *lease, std::string *error)
{
    if (parentPath == nullptr || storeName == nullptr || lease == nullptr ||
        storeName[0] == '\0' || std::strchr(storeName, '/') != nullptr) {
        SetError(error, "invalid-arguments", EINVAL);
        return StoreOpenStatus::kParentUnsafe;
    }
    lease->fd = -1;
    lease->leasePath.clear();
    lease->recoveryMarkerPath.clear();

    struct stat parentBefore {};
    if (lstat(parentPath, &parentBefore) != 0 ||
        !S_ISDIR(parentBefore.st_mode)) {
        const int saved = errno == 0 ? EINVAL : errno;
        SetError(error, "unsafe-parent-lstat", saved);
        return StoreOpenStatus::kParentUnsafe;
    }
    const int parentFd =
        open(parentPath, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (parentFd < 0) {
        SetError(error, "parent-open", errno);
        return StoreOpenStatus::kParentUnsafe;
    }
    struct stat parentAfter {};
    if (fstat(parentFd, &parentAfter) != 0 ||
        !S_ISDIR(parentAfter.st_mode) ||
        !SameObject(parentBefore, parentAfter)) {
        const int saved = errno == 0 ? EINVAL : errno;
        close(parentFd);
        SetError(error, "unsafe-parent-fstat", saved);
        return StoreOpenStatus::kParentUnsafe;
    }

    struct stat storeBefore {};
    if (fstatat(parentFd, storeName, &storeBefore, AT_SYMLINK_NOFOLLOW) != 0) {
        if (errno != ENOENT ||
            mkdirat(parentFd, storeName, kPrivateDirectoryMode) != 0) {
            const int saved = errno;
            close(parentFd);
            SetError(error, "store-mkdirat", saved);
            return StoreOpenStatus::kStoreUnsafe;
        }
    }

    const std::string storePath =
        std::string(parentPath) + "/" + std::string(storeName);
    if (lstat(storePath.c_str(), &storeBefore) != 0 ||
        !IsPrivateOwnedDirectory(storeBefore, geteuid())) {
        const int saved = errno == 0 ? EINVAL : errno;
        close(parentFd);
        SetError(error, "unsafe-store-lstat", saved);
        return StoreOpenStatus::kStoreUnsafe;
    }
    const int storeFd = openat(parentFd, storeName,
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (storeFd < 0) {
        const int saved = errno;
        close(parentFd);
        SetError(error, "store-openat", saved);
        return StoreOpenStatus::kStoreUnsafe;
    }
    struct stat storeAfter {};
    if (fstat(storeFd, &storeAfter) != 0 ||
        !IsPrivateOwnedDirectory(storeAfter, geteuid()) ||
        !SameObject(storeBefore, storeAfter)) {
        const int saved = errno == 0 ? EINVAL : errno;
        close(storeFd);
        close(parentFd);
        SetError(error, "unsafe-store-fstat", saved);
        return StoreOpenStatus::kStoreUnsafe;
    }

    struct stat leaseStat {};
    const int leaseFd = OpenPrivateRegularAt(
        storeFd, "lease.lock", geteuid(), O_RDWR, &leaseStat, error);
    if (leaseFd < 0) {
        close(storeFd);
        close(parentFd);
        return StoreOpenStatus::kLeaseUnsafe;
    }
    if (flock(leaseFd, LOCK_EX | LOCK_NB) != 0) {
        const int saved = errno;
        close(leaseFd);
        close(storeFd);
        close(parentFd);
        SetError(error, "lease-flock", saved);
        return StoreOpenStatus::kLeaseBusy;
    }

    struct stat markerStat {};
    const int markerFd = OpenPrivateRegularAt(storeFd, "recovery.complete",
        geteuid(), O_WRONLY, &markerStat, error);
    if (markerFd < 0) {
        close(leaseFd);
        close(storeFd);
        close(parentFd);
        return StoreOpenStatus::kMarkerUnsafe;
    }
    if (ftruncate(markerFd, 0) != 0) {
        const int saved = errno;
        close(markerFd);
        close(leaseFd);
        close(storeFd);
        close(parentFd);
        SetError(error, "marker-ftruncate", saved);
        return StoreOpenStatus::kMarkerWriteFailed;
    }
    constexpr char record[] =
        "recovery_complete_before_sa_registration=v1\n";
    const ssize_t written = write(markerFd, record, sizeof(record) - 1);
    if (written != static_cast<ssize_t>(sizeof(record) - 1) ||
        fsync(markerFd) != 0 || fsync(storeFd) != 0) {
        const int saved = errno;
        close(markerFd);
        close(leaseFd);
        close(storeFd);
        close(parentFd);
        SetError(error, "marker-write-or-fsync", saved);
        return StoreOpenStatus::kMarkerWriteFailed;
    }

    close(markerFd);
    close(storeFd);
    close(parentFd);
    lease->fd = leaseFd;
    lease->leasePath = storePath + "/lease.lock";
    lease->recoveryMarkerPath = storePath + "/recovery.complete";
    return StoreOpenStatus::kOk;
}

void ReleaseStoreLease(SecureStoreLease *lease)
{
    if (lease == nullptr) {
        return;
    }
    if (lease->fd >= 0) {
        close(lease->fd);
    }
    lease->fd = -1;
}

}  // namespace bridge::fn01::topology
