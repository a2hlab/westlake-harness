/*
 * Fn01 E1/E2/E3 topology probe.
 *
 * Experiment-only: this does not implement PackageManagementService and never
 * publishes a canonical package generation.
 */

#include <cerrno>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unistd.h>

#include "errors.h"
#include "fn01_secure_store.h"
#include "fn01_topology_policy.h"
#include "ipc_object_stub.h"
#include "ipc_skeleton.h"
#include "ipc_types.h"
#include "iservice_registry.h"
#include "message_option.h"
#include "message_parcel.h"

namespace {

using bridge::fn01::topology::ClaimVerdict;
using bridge::fn01::topology::EvaluateClaim;
using bridge::fn01::topology::SecureStoreLease;
using bridge::fn01::topology::StoreOpenStatus;
using bridge::fn01::topology::kProbeSaId;

constexpr int32_t kBundleMgrSaId = 401;
constexpr uint32_t kProbeTransaction = 1;
constexpr uint32_t kBmsGetNameForUidTransaction = 9;
constexpr char kStoreParent[] = "/data/local/tmp";
constexpr char kStoreName[] = "fn01_topology_probe_store";
constexpr char16_t kProbeDescriptor[] = u"org.bridge.fn01.ITopologyProbe";
constexpr char16_t kBmsDescriptor[] = u"ohos.appexecfwk.BundleMgr";

struct BmsProbeResult {
    int32_t lookupStatus = -1;
    int32_t transportStatus = -1;
    int32_t serviceStatus = -1;
    std::string name;
};

BmsProbeResult ProbeBmsReadOnly(int32_t uid)
{
    BmsProbeResult result;
    auto samgr = OHOS::SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
    if (samgr == nullptr) {
        result.lookupStatus = -2;
        return result;
    }
    auto bms = samgr->CheckSystemAbility(kBundleMgrSaId);
    if (bms == nullptr) {
        result.lookupStatus = -3;
        return result;
    }
    result.lookupStatus = 0;

    OHOS::MessageParcel data;
    OHOS::MessageParcel reply;
    OHOS::MessageOption option(OHOS::MessageOption::TF_SYNC);
    if (!data.WriteInterfaceToken(kBmsDescriptor) || !data.WriteInt32(uid)) {
        result.transportStatus = -4;
        return result;
    }
    result.transportStatus =
        bms->SendRequest(kBmsGetNameForUidTransaction, data, reply, option);
    if (result.transportStatus != OHOS::ERR_NONE) {
        return result;
    }
    result.serviceStatus = reply.ReadInt32();
    if (result.serviceStatus == OHOS::ERR_OK) {
        result.name = reply.ReadString();
    }
    return result;
}

class TopologyProbeStub final : public OHOS::IPCObjectStub {
public:
    TopologyProbeStub() : IPCObjectStub(kProbeDescriptor) {}

    int OnRemoteRequest(uint32_t code, OHOS::MessageParcel &data,
        OHOS::MessageParcel &reply, OHOS::MessageOption &option) override
    {
        if (code != kProbeTransaction) {
            return IPCObjectStub::OnRemoteRequest(code, data, reply, option);
        }
        const std::u16string token = data.ReadInterfaceToken();
        if (token != kProbeDescriptor) {
            return OHOS::ERR_INVALID_STATE;
        }

        const int32_t claimedUid = data.ReadInt32();
        const int32_t claimedUser = data.ReadInt32();
        const int32_t peerPid = OHOS::IPCSkeleton::GetCallingPid();
        const int32_t peerUid = OHOS::IPCSkeleton::GetCallingUid();
        const uint32_t peerToken = OHOS::IPCSkeleton::GetCallingTokenID();
        const std::string peerSid = OHOS::IPCSkeleton::GetCallingSid();
        const ClaimVerdict claimVerdict =
            EvaluateClaim(peerUid, claimedUid, claimedUser);
        if (claimVerdict != ClaimVerdict::kAllow) {
            std::printf(
                "SERVER_REJECT peer_pid=%d peer_uid=%d peer_token=%u "
                "peer_sid=%s claimed_uid=%d claimed_user=%d reason=%s\n",
                peerPid, peerUid, peerToken, peerSid.c_str(), claimedUid,
                claimedUser,
                bridge::fn01::topology::ClaimVerdictName(claimVerdict));
            std::fflush(stdout);
            return OHOS::ERR_PERMISSION_DENIED;
        }
        const BmsProbeResult bms = ProbeBmsReadOnly(peerUid);

        std::printf(
            "SERVER_REQUEST peer_pid=%d peer_uid=%d peer_token=%u peer_sid=%s "
            "claimed_uid=%d claimed_user=%d claim_matches_peer=%d "
            "bms_lookup=%d bms_transport=%d bms_service=%d bms_name=%s\n",
            peerPid, peerUid, peerToken, peerSid.c_str(), claimedUid, claimedUser,
            1, bms.lookupStatus, bms.transportStatus,
            bms.serviceStatus, bms.name.c_str());
        std::fflush(stdout);

        if (!reply.WriteInt32(peerPid) || !reply.WriteInt32(peerUid) ||
            !reply.WriteUint32(peerToken) || !reply.WriteString(peerSid) ||
            !reply.WriteBool(true) ||
            !reply.WriteInt32(bms.lookupStatus) ||
            !reply.WriteInt32(bms.transportStatus) ||
            !reply.WriteInt32(bms.serviceStatus) ||
            !reply.WriteString(bms.name)) {
            return OHOS::ERR_FLATTEN_OBJECT;
        }
        return OHOS::ERR_NONE;
    }
};

int RunServer()
{
    SecureStoreLease lease;
    std::string storeError;
    const StoreOpenStatus storeStatus =
        bridge::fn01::topology::AcquireRecoveredStoreLease(
            kStoreParent, kStoreName, &lease, &storeError);
    if (storeStatus != StoreOpenStatus::kOk) {
        const char *label = storeStatus == StoreOpenStatus::kLeaseBusy
            ? "STORE_LEASE_BUSY"
            : "STORE_OPEN_RESULT";
        std::fprintf(stderr, "%s status=%d detail=%s\n", label,
            static_cast<int>(storeStatus), storeError.c_str());
        return static_cast<int>(storeStatus);
    }
    std::printf("RECOVERY_COMPLETE marker=%s lease=%s\n",
        lease.recoveryMarkerPath.c_str(), lease.leasePath.c_str());
    std::fflush(stdout);

    auto samgr = OHOS::SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
    if (samgr == nullptr) {
        std::fprintf(stderr, "SAMGR_LOOKUP_FAIL\n");
        bridge::fn01::topology::ReleaseStoreLease(&lease);
        return 30;
    }
    OHOS::sptr<TopologyProbeStub> stub = new TopologyProbeStub();
    const int32_t addStatus = samgr->AddSystemAbility(kProbeSaId, stub);
    std::printf(
        "SA_ADD_RESULT sa_id=%d status=%d pid=%d uid=%d token=%" PRIu64
        " sid=%s\n",
        kProbeSaId, addStatus, getpid(), getuid(),
        OHOS::IPCSkeleton::GetSelfTokenID(),
        OHOS::IPCSkeleton::GetCallingSid().c_str());
    std::fflush(stdout);
    if (addStatus != OHOS::ERR_OK) {
        bridge::fn01::topology::ReleaseStoreLease(&lease);
        return 31;
    }

    const BmsProbeResult bms = ProbeBmsReadOnly(getuid());
    std::printf(
        "BMS_READ_ONLY lookup=%d transport=%d service=%d uid=%d name=%s\n",
        bms.lookupStatus, bms.transportStatus, bms.serviceStatus, getuid(),
        bms.name.c_str());
    std::printf("SERVER_READY recovery_precedes_registration=1\n");
    std::fflush(stdout);
    OHOS::IPCSkeleton::SetMaxWorkThreadNum(4);
    OHOS::IPCSkeleton::JoinWorkThread();
    bridge::fn01::topology::ReleaseStoreLease(&lease);
    return 0;
}

int RunClient(int32_t claimedUid, int32_t claimedUser)
{
    auto samgr = OHOS::SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
    if (samgr == nullptr) {
        std::fprintf(stderr, "CLIENT_SAMGR_LOOKUP_FAIL\n");
        return 40;
    }
    auto remote = samgr->CheckSystemAbility(kProbeSaId);
    if (remote == nullptr) {
        std::fprintf(stderr, "CLIENT_SA_LOOKUP_FAIL sa_id=%d\n", kProbeSaId);
        return 41;
    }

    OHOS::MessageParcel data;
    OHOS::MessageParcel reply;
    OHOS::MessageOption option(OHOS::MessageOption::TF_SYNC);
    if (!data.WriteInterfaceToken(kProbeDescriptor) ||
        !data.WriteInt32(claimedUid) || !data.WriteInt32(claimedUser)) {
        std::fprintf(stderr, "CLIENT_PARCEL_WRITE_FAIL\n");
        return 42;
    }
    const int32_t sendStatus =
        remote->SendRequest(kProbeTransaction, data, reply, option);
    if (sendStatus != OHOS::ERR_NONE) {
        if (sendStatus == OHOS::ERR_PERMISSION_DENIED) {
            std::fprintf(stderr,
                "CLIENT_CLAIM_REJECTED status=%d claimed_uid=%d "
                "claimed_user=%d\n",
                sendStatus, claimedUid, claimedUser);
            return 44;
        }
        std::fprintf(stderr, "CLIENT_SEND_FAIL status=%d\n", sendStatus);
        return 43;
    }

    const int32_t peerPid = reply.ReadInt32();
    const int32_t peerUid = reply.ReadInt32();
    const uint32_t peerToken = reply.ReadUint32();
    const std::string peerSid = reply.ReadString();
    const bool claimMatchesPeer = reply.ReadBool();
    const int32_t bmsLookup = reply.ReadInt32();
    const int32_t bmsTransport = reply.ReadInt32();
    const int32_t bmsService = reply.ReadInt32();
    const std::string bmsName = reply.ReadString();
    std::printf(
        "CLIENT_REPLY local_pid=%d local_uid=%d local_token=%" PRIu64 " "
        "server_peer_pid=%d server_peer_uid=%d server_peer_token=%u "
        "server_peer_sid=%s claimed_uid=%d claimed_user=%d "
        "claim_matches_peer=%d bms_lookup=%d bms_transport=%d "
        "bms_service=%d bms_name=%s\n",
        getpid(), getuid(), OHOS::IPCSkeleton::GetSelfTokenID(), peerPid,
        peerUid, peerToken, peerSid.c_str(), claimedUid, claimedUser,
        claimMatchesPeer ? 1 : 0, bmsLookup, bmsTransport, bmsService,
        bmsName.c_str());
    return claimMatchesPeer ? 0 : 44;
}

void PrintUsage(const char *argv0)
{
    std::fprintf(stderr,
        "usage: %s server | client <claimed_uid> <claimed_user>\n", argv0);
}

}  // namespace

int main(int argc, char **argv)
{
    if (argc == 2 && std::strcmp(argv[1], "server") == 0) {
        return RunServer();
    }
    if (argc == 4 && std::strcmp(argv[1], "client") == 0) {
        char *uidEnd = nullptr;
        char *userEnd = nullptr;
        const long uid = std::strtol(argv[2], &uidEnd, 10);
        const long user = std::strtol(argv[3], &userEnd, 10);
        if (uidEnd == nullptr || *uidEnd != '\0' || userEnd == nullptr ||
            *userEnd != '\0') {
            PrintUsage(argv[0]);
            return 2;
        }
        return RunClient(static_cast<int32_t>(uid), static_cast<int32_t>(user));
    }
    PrintUsage(argv[0]);
    return 2;
}
