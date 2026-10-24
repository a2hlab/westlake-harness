// Included inside oh_adapter in the production WMC translation unit.
struct OHWindowManagerClient::RecoveryState {
    std::shared_ptr<westlake::recovery::Coordinator> coordinator;
    std::shared_ptr<OHOS::Rosen::RSSurfaceNode> windowNode;
    OHOS::sptr<OHOS::Rosen::WindowSessionProperty> recipe;
    // Retain ambiguous transaction endpoints. Never publish or repeatedly recreate.
    OHOS::sptr<SessionStageAdapter> pendingStage;
    OHOS::sptr<OHOS::IRemoteObject> pendingRemote;
    OHOS::sptr<OHOS::Rosen::WindowSessionProperty> pendingProperty;
    int32_t pendingActual = 0;
    uint64_t revision = 0; // Side table: preserve SessionEntry ABI for Focus34 policy.
};
static OHOS::sptr<OHOS::Rosen::WindowSessionProperty> recoveryCopyProperty(
    const OHOS::sptr<OHOS::Rosen::WindowSessionProperty>& source)
{
    OHOS::MessageParcel copy;
    if (!source || !copy.WriteStrongParcelable(source)) return nullptr;
    return copy.ReadStrongParcelable<OHOS::Rosen::WindowSessionProperty>();
}

std::map<int32_t, std::shared_ptr<OHWindowManagerClient::RecoveryState>>&
OHWindowManagerClient::recoveryStates()
{
    static auto* table = new std::map<int32_t, std::shared_ptr<RecoveryState>>;
    return *table; // Protected by the existing sessionMutex_; no class layout change.
}
struct RecordObserverLifetime {
    std::atomic<bool> started{false}, stop{false};
    std::thread thread;
};
static RecordObserverLifetime& recordObserverLifetime()
{
    static auto* lifetime = new RecordObserverLifetime;
    return *lifetime; // Explicitly joined by WMC destructor.
}
