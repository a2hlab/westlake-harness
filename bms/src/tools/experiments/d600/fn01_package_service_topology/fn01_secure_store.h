#ifndef BRIDGE_FN01_SECURE_STORE_H
#define BRIDGE_FN01_SECURE_STORE_H

#include <string>

namespace bridge::fn01::topology {

enum class StoreOpenStatus {
    kOk = 0,
    kParentUnsafe = 20,
    kStoreUnsafe = 21,
    kLeaseUnsafe = 22,
    kLeaseBusy = 23,
    kMarkerUnsafe = 24,
    kMarkerWriteFailed = 25,
};

struct SecureStoreLease {
    int fd = -1;
    std::string leasePath;
    std::string recoveryMarkerPath;
};

StoreOpenStatus AcquireRecoveredStoreLease(const char *parentPath,
    const char *storeName, SecureStoreLease *lease, std::string *error);

void ReleaseStoreLease(SecureStoreLease *lease);

}  // namespace bridge::fn01::topology

#endif  // BRIDGE_FN01_SECURE_STORE_H
