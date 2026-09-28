#include "fn01_secure_store.h"
#include "fn01_topology_policy.h"

#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

namespace {

using bridge::fn01::topology::ClaimVerdict;
using bridge::fn01::topology::SecureStoreLease;
using bridge::fn01::topology::StoreOpenStatus;

void RemoveStoreFiles(const std::string &parent)
{
    const std::string store = parent + "/store";
    unlink((store + "/recovery.complete").c_str());
    unlink((store + "/lease.lock").c_str());
    rmdir((store + "/lease.lock").c_str());
    rmdir(store.c_str());
}

void TestClaimPolicy()
{
    using bridge::fn01::topology::EvaluateClaim;
    assert(EvaluateClaim(1000, 1000, 0) == ClaimVerdict::kAllow);
    assert(EvaluateClaim(1000, 1001, 0) ==
        ClaimVerdict::kClaimedUidMismatch);
    assert(EvaluateClaim(1000, 1000, 1) ==
        ClaimVerdict::kUnsupportedUser);
    assert(bridge::fn01::topology::kProbeSaId == 127233);
    assert(bridge::fn01::topology::kProbeSaId != 5502);
}

void TestSecureStoreHappyPathAndLease()
{
    char parentTemplate[] = "/tmp/fn01-secure-store.XXXXXX";
    char *parent = mkdtemp(parentTemplate);
    assert(parent != nullptr);

    SecureStoreLease first;
    std::string error;
    assert(bridge::fn01::topology::AcquireRecoveredStoreLease(
        parent, "store", &first, &error) == StoreOpenStatus::kOk);
    assert(first.fd >= 0);

    struct stat marker {};
    assert(lstat(first.recoveryMarkerPath.c_str(), &marker) == 0);
    assert(S_ISREG(marker.st_mode));
    assert(marker.st_uid == geteuid());
    assert((marker.st_mode & 077) == 0);

    SecureStoreLease second;
    error.clear();
    assert(bridge::fn01::topology::AcquireRecoveredStoreLease(
        parent, "store", &second, &error) == StoreOpenStatus::kLeaseBusy);
    assert(second.fd == -1);

    bridge::fn01::topology::ReleaseStoreLease(&first);
    error.clear();
    assert(bridge::fn01::topology::AcquireRecoveredStoreLease(
        parent, "store", &second, &error) == StoreOpenStatus::kOk);
    bridge::fn01::topology::ReleaseStoreLease(&second);

    RemoveStoreFiles(parent);
    assert(rmdir(parent) == 0);
}

void TestStoreSymlinkRejected()
{
    char parentTemplate[] = "/tmp/fn01-store-symlink.XXXXXX";
    char targetTemplate[] = "/tmp/fn01-store-target.XXXXXX";
    char *parent = mkdtemp(parentTemplate);
    char *target = mkdtemp(targetTemplate);
    assert(parent != nullptr && target != nullptr);
    const std::string store = std::string(parent) + "/store";
    assert(symlink(target, store.c_str()) == 0);

    SecureStoreLease lease;
    std::string error;
    assert(bridge::fn01::topology::AcquireRecoveredStoreLease(
        parent, "store", &lease, &error) == StoreOpenStatus::kStoreUnsafe);
    assert(lease.fd == -1);

    assert(unlink(store.c_str()) == 0);
    assert(rmdir(parent) == 0);
    assert(rmdir(target) == 0);
}

void TestLeaseSymlinkAndWrongTypeRejected()
{
    char parentTemplate[] = "/tmp/fn01-file-symlink.XXXXXX";
    char targetTemplate[] = "/tmp/fn01-file-target.XXXXXX";
    char *parent = mkdtemp(parentTemplate);
    int targetFd = mkstemp(targetTemplate);
    assert(parent != nullptr && targetFd >= 0);
    close(targetFd);

    const std::string store = std::string(parent) + "/store";
    assert(mkdir(store.c_str(), 0700) == 0);
    const std::string leasePath = store + "/lease.lock";
    assert(symlink(targetTemplate, leasePath.c_str()) == 0);

    SecureStoreLease lease;
    std::string error;
    assert(bridge::fn01::topology::AcquireRecoveredStoreLease(
        parent, "store", &lease, &error) == StoreOpenStatus::kLeaseUnsafe);
    assert(unlink(leasePath.c_str()) == 0);
    assert(mkdir(leasePath.c_str(), 0700) == 0);
    error.clear();
    assert(bridge::fn01::topology::AcquireRecoveredStoreLease(
        parent, "store", &lease, &error) == StoreOpenStatus::kLeaseUnsafe);

    assert(rmdir(leasePath.c_str()) == 0);
    assert(rmdir(store.c_str()) == 0);
    assert(rmdir(parent) == 0);
    assert(unlink(targetTemplate) == 0);
}

void TestUnsafeStorePermissionsRejected()
{
    char parentTemplate[] = "/tmp/fn01-store-mode.XXXXXX";
    char *parent = mkdtemp(parentTemplate);
    assert(parent != nullptr);
    const std::string store = std::string(parent) + "/store";
    assert(mkdir(store.c_str(), 0770) == 0);
    assert(chmod(store.c_str(), 0770) == 0);

    SecureStoreLease lease;
    std::string error;
    assert(bridge::fn01::topology::AcquireRecoveredStoreLease(
        parent, "store", &lease, &error) == StoreOpenStatus::kStoreUnsafe);

    assert(rmdir(store.c_str()) == 0);
    assert(rmdir(parent) == 0);
}

}  // namespace

int main()
{
    TestClaimPolicy();
    TestSecureStoreHappyPathAndLease();
    TestStoreSymlinkRejected();
    TestLeaseSymlinkAndWrongTypeRejected();
    TestUnsafeStorePermissionsRejected();
    std::puts("PASS fn01_topology_host_tests");
    return 0;
}
