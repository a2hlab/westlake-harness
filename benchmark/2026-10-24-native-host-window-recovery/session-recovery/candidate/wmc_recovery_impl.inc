// Included inside oh_adapter, after the ordinary WMC definitions.
OHWindowManagerClient::~OHWindowManagerClient()
{
    recordObserverLifetime().stop.store(true);
    if (recordObserverLifetime().thread.joinable()) recordObserverLifetime().thread.join();
}
void OHWindowManagerClient::startRecordObserver()
{
    bool expected = false;
    if (!recordObserverLifetime().started.compare_exchange_strong(expected, true)) return;
    recordObserverLifetime().thread = std::thread([this] {
        while (!recordObserverLifetime().stop.load()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
            if (recordObserverLifetime().stop.load()) break;
            std::vector<int32_t> logical;
            { std::lock_guard<std::recursive_mutex> g(sessionMutex_);
              for (const auto& entry : sessions_) if (recoveryStates().count(entry.first)) logical.push_back(entry.first); }
            for (auto id : logical) observeHostRecord(id);
        }
    });
}
void OHWindowManagerClient::observeHostRecord(int32_t logical)
{
    using namespace westlake::recovery;
    SessionEntry snapshot;
    std::shared_ptr<RecoveryState> state;
    uint64_t revision;
    OHOS::sptr<OHOS::IRemoteObject> scene;
    {
        std::lock_guard<std::recursive_mutex> g(sessionMutex_);
        auto it = sessions_.find(logical);
        auto recovery = recoveryStates().find(logical);
        if (it == sessions_.end() || recovery == recoveryStates().end()) return;
        state = recovery->second; revision = state->revision;
        snapshot = it->second; scene = sceneProxy_;
    }
    if (!scene || getuid() == 0 || getuid() != geteuid() || getgid() != getegid()) return;
    struct SessionPort final : Port {
        OHWindowManagerClient& owner;
        SessionEntry snapshot;
        std::shared_ptr<RecoveryState> state;
        OHOS::sptr<OHOS::IRemoteObject> scene;
        uint64_t revision;
        SessionPort(OHWindowManagerClient& o, SessionEntry s, std::shared_ptr<RecoveryState> recovery,
                    uint64_t version, OHOS::sptr<OHOS::IRemoteObject> remote)
            : owner(o), snapshot(s), state(recovery), scene(remote), revision(version) {}
        bool current() const override {
            std::lock_guard<std::recursive_mutex> g(owner.sessionMutex_);
            auto it = owner.sessions_.find(snapshot.sessionId);
            return it != owner.sessions_.end() && owner.recoveryStates().count(snapshot.sessionId) &&
                owner.recoveryStates().at(snapshot.sessionId) == state &&
                it->second.windowId == snapshot.windowId &&
                state->revision == revision;
        }
        ParentReply parent(int32_t id) override {
            OHOS::MessageParcel d, r;
            OHOS::MessageOption opt(OHOS::MessageOption::TF_SYNC, 1);
            if (!d.WriteInterfaceToken(u"OHOS.ISceneSessionManager") || !d.WriteInt32(id))
                return {Reply::Rejected, -1};
            const auto code = OHOS::Rosen::ISceneSessionManager::SceneSessionManagerMessage::
                TRANS_ID_GET_PARENT_MAIN_WINDOW_ID;
            const auto ipc = scene->SendRequest(static_cast<uint32_t>(code), d, r, opt);
            int32_t main = -1, rc = -1;
            if (ipc || !r.ReadInt32(main) || !r.ReadInt32(rc)) return {Reply::Unknown, -1};
            if (rc == static_cast<int32_t>(OHOS::Rosen::WMError::WM_ERROR_NULLPTR))
                return {Reply::Missing, -1};
            return {rc == 0 ? Reply::Ok : Reply::Rejected, main};
        }
        void quiesceOldCallbacks() override { snapshot.stageAdapter->recoveryGate()->close(); }
        Created create(int32_t parent, uint64_t) override {
            state->pendingProperty = recoveryCopyProperty(state->recipe);
            state->pendingStage = snapshot.stageAdapter->recoveryEndpoint();
            if (!state->pendingProperty || !state->pendingStage->recoveryReady()) return {Reply::Rejected, 0};
            auto property = state->pendingProperty;
            property->SetParentId(parent); property->SetParentPersistentId(parent);
            OHOS::MessageParcel d, r;
            OHOS::MessageOption opt(OHOS::MessageOption::TF_SYNC, 1);
            if (!d.WriteInterfaceToken(u"OHOS.ISceneSessionManager") ||
                !d.WriteRemoteObject(state->pendingStage->AsObject()) ||
                !d.WriteRemoteObject(snapshot.eventChannel->AsObject()) ||
                !state->windowNode->Marshalling(d) || !d.WriteStrongParcelable(property))
                return {Reply::Rejected, 0};
            const auto ipc = scene->SendRequest(static_cast<uint32_t>(
                OHOS::Rosen::ISceneSessionManager::SceneSessionManagerMessage::
                    TRANS_ID_CREATE_AND_CONNECT_SPECIFIC_SESSION), d, r, opt);
            // Failed IPC is ambiguous even if a server may already have created a session.
            if (ipc || !r.ReadInt32(state->pendingActual)) return {Reply::Unknown, 0};
            state->pendingRemote = r.ReadRemoteObject();
            OHOS::sptr<OHOS::Rosen::SystemSessionConfig> config =
                r.ReadParcelable<OHOS::Rosen::SystemSessionConfig>();
            uint32_t level = 0, type = 0; uint64_t display = 0; int32_t rc = -1;
            if (!state->pendingRemote || !config || !r.ReadUint32(level) || !r.ReadUint64(display) ||
                !r.ReadUint32(type) || !r.ReadInt32(rc) || state->pendingActual <= 0)
                return {Reply::Unknown, 0};
            property->SetSubWindowLevel(level); property->SetDisplayId(display);
            if (rc != 0) return {Reply::Unknown, 0};
            return {Reply::Ok, state->pendingActual};
        }
        Reply call(uint32_t code, bool foreground) {
            OHOS::MessageParcel d, r;
            OHOS::MessageOption opt(OHOS::MessageOption::TF_SYNC, 1);
            bool wrote = d.WriteInterfaceToken(u"OHOS.ISession");
            if (foreground) wrote = wrote && d.WriteBool(true) &&
                d.WriteStrongParcelable(state->pendingProperty) && d.WriteBool(true) && d.WriteString("");
            if (!wrote) return Reply::Rejected;
            auto ipc = state->pendingRemote->SendRequest(code, d, r, opt);
            int32_t rc = -1;
            if (ipc || !r.ReadInt32(rc)) return Reply::Unknown;
            return rc == 0 ? Reply::Ok : Reply::Rejected;
        }
        Reply connect(int32_t) override {
            auto result = call(1, true); // ISession Foreground, existing production parcel shape.
            if (result != Reply::Ok) return result;
            return call(102, false); // ISession RaiseToAppTop.
        }
        Reply discard(int32_t actual) override {
            OHOS::MessageParcel d, r;
            OHOS::MessageOption opt(OHOS::MessageOption::TF_SYNC, 1);
            if (!d.WriteInterfaceToken(u"OHOS.ISceneSessionManager") || !d.WriteInt32(actual))
                return Reply::Rejected;
            auto ipc = scene->SendRequest(static_cast<uint32_t>(
                OHOS::Rosen::ISceneSessionManager::SceneSessionManagerMessage::
                    TRANS_ID_DESTROY_AND_DISCONNECT_SPECIFIC_SESSION), d, r, opt);
            int32_t rc = -1;
            if (ipc || !r.ReadInt32(rc)) return Reply::Unknown;
            if (rc != 0) return Reply::Rejected;
            state->pendingRemote = nullptr; state->pendingStage = nullptr; state->pendingProperty = nullptr;
            return Reply::Ok;
        }
        bool publish(const Binding& old, const Binding& next) override {
            auto gate = state->pendingStage->recoveryGate();
            std::lock_guard<std::recursive_mutex> epoch(gate->mutex);
            if (gate->overflow || !gate->buffering) return false;
            std::lock_guard<std::recursive_mutex> g(owner.sessionMutex_);
            auto it = owner.sessions_.find(old.logical);
            if (it == owner.sessions_.end() || !owner.recoveryStates().count(old.logical) ||
                owner.recoveryStates().at(old.logical) != state ||
                it->second.windowId != static_cast<uint32_t>(old.actual) ||
                state->revision != revision) return false;
            if (!Routes::instance().replace(old.logical, old.actual, next.actual)) return false;
            auto& entry = it->second;
            entry.sessionRemote = state->pendingRemote;
            entry.stageAdapter = state->pendingStage;
            entry.windowId = static_cast<uint32_t>(next.actual);
            ++state->revision;
            ParentCache::instance().publish(next.parent); // Subsequent Activity/dialog creates.
            // Other logical children refer to actual parent identities for remote operations.
            for (auto& child : owner.sessions_) {
                if (child.second.parentWindowId == static_cast<uint32_t>(old.actual)) {
                    child.second.parentWindowId = next.actual;
                    if (child.second.windowProperty) child.second.windowProperty->SetParentId(next.actual);
                }
            }
            // Logical session, Java SurfaceControl, both nodes and producer/native window untouched.
            // Keep buffering until the post-publication foreground record check.
            state->pendingRemote = nullptr; state->pendingStage = nullptr; state->pendingProperty = nullptr;
            return true;
        }
    } port(*this, snapshot, state, revision, scene);
    const auto now = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
    const auto read = [] {
        return ReadObservation("/data/app/el2/100/base/org.westlake.imehost/haps/entry/files/window-state.json",
                               getuid(), getgid());
    };
    const auto outcome = state->coordinator->poll(now, read, port);
    if (outcome != Outcome::Idle && outcome != Outcome::Throttled)
        fprintf(stderr, "[HOST-SESSION] logical=%d outcome=%d\n", logical, static_cast<int>(outcome));
    // Replay only observed new-endpoint callbacks, not synthesized visibility.
    // If the record became hidden after commit, keep buffering until a later
    // visible same-parent record; normal same-host polling creates no session.
    auto visible = read();
    OHOS::sptr<SessionStageAdapter> currentStage;
    if (visible && Foreground(visible->candidate) &&
        visible->candidate.window_id == state->coordinator->binding().parent) {
        { std::lock_guard<std::recursive_mutex> g(sessionMutex_);
          auto it = sessions_.find(logical);
          if (it != sessions_.end() && recoveryStates().count(logical) && recoveryStates().at(logical) == state &&
              it->second.windowId == static_cast<uint32_t>(state->coordinator->binding().actual))
              currentStage = it->second.stageAdapter; }
        if (currentStage) {
            bool wasBuffering;
            { auto gate = currentStage->recoveryGate();
              std::lock_guard<std::recursive_mutex> epoch(gate->mutex); wasBuffering = gate->buffering; }
            if (wasBuffering && currentStage->activateRecoveryCallbacks()) requestFocusForSession(logical);
        }
    }
}
