# Toutiao reopen white screen: window re-association review (static, zero device operations)

Scope: independent review of how the existing Toutiao child window could re-associate with a re-created host HAP through normal window APIs. No device command, REA, controller/executor/config read or stopped action was used. Line numbers refer to the exact files listed; full SHA-256, git blobs, verbatim snippets and the persisted SSH receipts are in [`source-evidence/`](source-evidence/) (`SHA256SUMS.txt`, `local-snippets.txt`, `ssh/`), landing list in [`landing-paths.txt`](landing-paths.txt); the deployed bridge object binding is being closed separately, so bridge lines are "source snapshot" claims, not "deployed object" claims.

## Limitations of this audit
- My first, interactive hw248 reads were not persisted. The `ssh/` receipts are a later read-only re-read; their file SHA-256 values are identical to the ones quoted earlier (`d315e38c…`, `d008356…`).
- E1 (`parentId=32 -> session53`) is taken from outer evidence; I did not read the raw log.

## Evidence taken as input (operator/outer runs, same boot `61aa5791…`)
| # | Observation | Raw location |
|---|---|---|
| E1 | Before close: child 22035 (birth 6535369) logged `parentId=32 -> session53` (outer) | outer evidence |
| E2 | Recents swipe-up of the Toutiao card: host 4958 gone; child 22035 and parent 5129 (birth 11126) still alive | `$HOME/.local/share/westlake/recents-close-reopen-20261024/raw/04/post.ident.json` |
| E3 | One desktop click (board uptime 70394.33 -> 70394.69): new host 10486 (birth 7039472); t10/t30/t60/t90 screenshots all blank `#f4f6f8`; child 22035 unchanged | `$HOME/.local/share/westlake/desktop-reopen-02-20261024/raw/06/` |
| E4 | WMS `-a "-a"` at 12:33:30: only visible app window is `imehost0` pid 10486 WinId 62 (focus) | `.../desktop-reopen-02-20261024/raw/08/wms.stdout` |
| E5 | Uptime 71218.63-71219.00: `-w 53` and `-w 32` -> "The arguments are illegal"; `-w 62` -> body (pid 10486, ParentWindowId 0, IsVisible false, taken after Home, so not the white-screen state) | `$HOME/.local/share/westlake/wms-session-20261024/collection-01/` |

## Source facts
- **Host HAP b18978b8** = baseline `EntryAbility.js` (`9dc302d9…`) + candidate `Index.js` (`af91e594…`), both under `benchmark/2026-10-20-toutiao-launcher-page/sources/` (README line 7).
  - `EntryAbility.js:24-28` loads `pages/Index` and sets the main window background to `#fff4f6f8`.
  - `Index.js:12-15` is an empty `Column` with background `#fff4f6f8`.
  - So the E3 screen is the host's own main window with nothing composited above it.
  - The HAP has no code that tells the child about its window. It only records `getWindowProperties()` to its own `filesDir/window-state.json` (`EntryAbility.js:11-13, 28`).
- **Bridge parent id is fixed per child process.** `oh_window_manager_client.cpp` (base `f5ae0990…`, ability38 `1844e81b…`; the function is identical in both):
  - `wl_query_ability_main_window_id` (base `:171-224`) keeps a function-local `static int32_t wl_cached` (`:173`).
  - It takes `WL_PARENT_ID` from the environment once (`:178-186`). Otherwise it uses SSM code 56, which the §340b comment (`:175-177`) says returns count=0 for this ability.
  - The only call site is at session creation: base `:1706-1709`, ability38 `:1787-1790`, which do `SetParentId` / `SetParentPersistentId`.
- **Destroy notification is a no-op (snapshot candidate).** `SessionStageBridge.java:105-109` (`0757e594…`, source-build-host snapshot; **not bound to the deployed JAR** in this review): `onNotifyDestroy` only removes insets and logs PARTIAL. There is no view-root teardown and no session re-creation.
- **OH 6.1 LTS SceneSessionManager** (hw248 `/opt/build-trees/oh610_lts_source/.../scene_session_manager.cpp`, `d315e38c…`; `window_manager` git HEAD `ca6f12d1…`, OpenHarmony-6.1-LTS, 2026-06-29; exact correspondence to the board's 6.1.0.31 build is not verified here):
  - Destroying a main session calls `DestroySubSession` (`:4234` -> `:4081-4094`), which runs `DestroyAndDisconnectSpecificSessionInner` (`:5539`) for every sub-session.
  - `SetParentWindow` (`:18975-19016`) returns `WM_ERROR_INVALID_PARENT` in three cases: the **old** parent session is gone, either parent is not main/float/sub, or the old and new parents have different `callingPid`.
- **What the dump error text means** (`mock_session_manager_service.cpp` `d0083568…` and SSM above):
  - `Dump` (`:176-205`) prints `ShowIllegalArgsInfo` (`:688-691`) whenever `DumpSessionInfo` (`:717-745`) is non-zero.
  - For `-w <digits>`, SSM `GetSessionDumpInfo` (`:7932-7948`) checks permission, then digits (`IsValidDigitString` `:7386-7399`), then calls `GetSpecifiedSessionDumpInfo` (`:7840-7845`). That returns `WS_ERROR_INVALID_PARAM` when `GetSceneSession` (`:1932-1940`, a `sceneSessionMap_` lookup) misses.
  - E5 used the same argument form in the same batch and `-w 62` passed permission, proxy and digit checks. So for 53 and 32 the only distinct branch is "id not in the SSM session map at that instant".
  - Residual: a transient IPC failure on exactly those two calls would print the same text. The text alone does not separate "erased" from "never existed"; E1 supplies "existed".

## Destroy chain: is `NotifyDestroy` sent to the sub-window? (OH 6.1 LTS, receipts `ssh/notify_*`, `ssh/uisvc_callers`, `ssh/disconnect_decl`)
- `DestroyAndDisconnectSpecificSessionInner` (`scene_session_manager.cpp:5539`) calls `sceneSession->Disconnect()` at `:5568` with no arguments.
  - The defaults are `isFromClient = false` (`scene_session.h:234`, `9d6ca286…`).
- That goes `SceneSession::Disconnect` (`scene_session.cpp:740-750`, `d31ad31b…`) → `DisconnectTask` (`:752-797`) → `Session::Disconnect` (`:786`; `session.cpp:1776-1808`, `8eb3b54d…`).
  - It resets the surface nodes, sets the state to BACKGROUND then DISCONNECT, and calls `NotifyDisconnect()` (`:1800`).
  - `NotifyDisconnect` (`session.cpp:627-635`) only notifies server-side `ILifecycleListener::OnDisconnect`. **None of these lines calls `sessionStage_->NotifyDestroy()`.**
- `Session::NotifyDestroy` (`session.cpp:2488-2494`) is the only path that forwards to the client stage. Its only non-test callers are three:
  - `scene_session_manager.cpp:4061`, in `DestroyDialogWithMainWindow`, which applies to dialogs;
  - `:5654`, in `DestroyUIServiceExtensionSubWindow`, reached from `:5580`. It fires only if `GetIsUIExtFirstSubWindow() && !GetIsUIExtensionAbilityProcess()` (`:5652-5653`);
  - `:11516`, in `BindDialogSessionTarget` on failure, which also applies to dialogs.
- The bridge snapshot never sets those UIExtension flags (0 hits in `bridge-d4fa-source-snapshot/`). So for this ordinary sub-window, the source predicts **no `NotifyDestroy` to the child stage** when the parent session is destroyed.
- This matches the outer filtered scan, which found 0 `NotifyDestroy` hits. Two caveats apply:
  - That scan read a growing file (29180290 → 29185906 B), so it is not a stable whole-file read.
  - An absent log line is consistent with the source but does not prove the call never happened.
- **Native stage boundary (unknown):** the `[WESTLAKE-STAGE] NotifyDestroy` fprintf exists in `base/.../session_stage_adapter.cpp:145`. The `ability38` layer has only the header. Which compiled stage object is deployed is not closed here, so whether that log string would even be emitted is unknown.
- **Consequence for the fix direction:** the child cannot rely on `NotifyDestroy` to detect parent loss. Detection must come from a different signal, which is open: for example the session/remote-object death, a disconnect seen on its next session call, or an explicit signal from the host.

## Reusing the old RSSurfaceNode for a new sub-session (OH 6.1 LTS, receipts `ssh/node_locate`, `ssh/node_snippets`)
Question: after the old session is destroyed, may the client pass its existing `RSSurfaceNode` (and keep the EGL producer behind it) to a new `CreateAndConnectSpecificSession`?
- **No server-side rejection found.**
  - `CreateAndConnectSpecificSession` (`scene_session_manager.cpp:4392-4513`, `d315e38c…`) touches `surfaceNode` in only three places: the parameter (`:4393`), the task capture (`:4461`), and the hand-off to `newSession->ConnectInner(...)` (`:4492-4493`). There is no check of node id, previous owner, or uniqueness. Its checks concern the parent, level, type, and UIExt/PiP/float rules.
  - `Session::ConnectInner` (`session.cpp:1465-1500`, `8eb3b54d…`) checks only the **new** session's own state (`:1478`), then calls `SetSurfaceNode` (`:1492`). That function (`:192-198`) simply stores the node.
- **The old session's teardown does not destroy the render node.**
  - `Session::Disconnect` swaps out `surfaceNode_` and drops it on the main handler (`session.cpp:1785-1796`).
  - The server-side object came from `RSSurfaceNode::Unmarshalling` (`rs_surface_node.cpp:481-505`, `6e40e271…`). That function sets `skipDestroyCommandInDestructor_ = true` (`:502-503`), with the comment "for nodes constructed by unmarshalling, we should not destroy the corresponding render node on destruction".
  - `RSNode::~RSNode` (`rs_node.cpp:220-275`, `4064c353…`) then only unregisters the node from the map. It returns before queuing `RSBaseNodeDestroy` (`:244-254`, `:263-270`).
  - So the WMS sub-session teardown path does not issue a render-node destroy for the client-created node, and nothing on that path touches the client's producer.
- **Reuse within the server process:** `Unmarshalling` returns the existing object if the id is still in `RSNodeMap` (`:493-496`), so repeating an id is not an error.
- **Verdict:** the OH 6.1 WMS/RS-client source **does not forbid** connecting a new sub-session with the old client node, and its destroy path **does not** destroy that node. This is "no rejection found in the read code", not "verified to work".
- **Not read / not closed:**
  - the SceneBoard (ArkTS) side that mounts and unmounts the node in its tree;
  - render-service server handling of a node whose old parent was removed;
  - whether our bridge actually keeps the `RSSurfaceNode` and producer alive after the session loss (Codex is checking the bridge session-id usage);
  - any live test.

## Conclusions
1. **E5 supports "sessions 53 and 32 had been destroyed" over "53 still attached to its old parent"**, but does not prove it unconditionally. The likeliest reading of the `-w` text is an SSM map miss, consistent with the OH teardown path (main session destroyed, then its sub-sessions). The same text is also produced by a transient IPC or service failure on those calls (`DumpSessionInfo` returning -1 from the proxy/IPC branches), and that branch is not excluded.
2. **`SetParentWindow` cannot re-associate here.** It needs the old parent (32) alive and the same pid for both parents (4958 vs 10486), and the sub-session itself (53) is gone.
3. **The normal path is to create a new sub-session**, using the same `CreateAndConnectSpecificSession` path that produced 53, with parent = the *current* host main window (62). Two gaps in the snapshot prevent this today:
   - (a) the parent id is resolved once per process (`static wl_cached` plus a spawn-time env value);
   - (b) nothing reacts to `NotifyDestroy`, or to the parent being gone, by re-creating a session and re-binding the existing view root/surface.
4. **Alternative: couple the lifecycles.** The child's UI would end with the host session, so a normal reopen spawns a fresh child with a fresh parent id. The spawn path was not read in this review.

## Fix direction (not a complete minimal fix)
- **Bridge only**, in two files:
  - `oh_window_manager_client.cpp`: resolve the parent per creation instead of through the process-static cache, and add a re-attach entry that creates a sub-session for an existing Android window under a given parent;
  - `SessionStageBridge.onNotifyDestroy`: mark the window detached.
- **Parent-id channel:** the first attach keeps `WL_PARENT_ID`. A re-attach needs an explicit current-host window id, for example from the host's existing window-ready record.
- **Not changed:** HAP UI, ART runtime, SSM, and spawn/guardian.
- **Not closed by this review**, so the two files above are a direction only:
  - the current-parent channel (how the child learns window 62);
  - re-creating the Android view root on a new session;
  - re-wiring the EGL/ANativeWindow producer to the new surface node;
  - which bridge source and JAR are actually deployed (handled separately).

## Falsifiers of the "parent lost, never re-attached" hypothesis
- **F1 (withdrawn, wrong premise):** the earlier F1 assumed the server sends `NotifyDestroy` to the sub-window's stage when the parent dies. The OH 6.1 source below shows that this path normally does **not** do so. A missing `NotifyDestroy` line therefore does not falsify anything; see "Destroy chain".
- **F2:** after reopen, the child logs a new create (`§340b`/`§340` parentId = 62), and the new id dumps with `Pid 22035 ParentWindowId 62`, yet the screen stays white. Then the parent is not the cause; look at rendering/visibility.
- **F3:** control run where the host is kept alive (Home, then the icon, with no Recents close) is also white. Then parent loss is not necessary for the white screen.
- **F4:** `-w 53` returns a body at any time after 4958 is gone. Then the sub-session was not destroyed with its parent.
- **F5:** a freshly spawned child with `WL_PARENT_ID` set to the current host window is still white. Then the hypothesis is insufficient.

## Minimal verification criteria (read-only on the next window, before any fix)
- **V1:** before the close, `-w 32` and `-w 53` both return bodies (53: Pid 22035, ParentWindowId 32). After the close, both are illegal while a known-good `-w <live id>` in the same batch returns a body.
- **V2:** between the reopen click and t90, the child stderr has no new session-create line. NotifyDestroy count is **not** a criterion; see "Destroy chain".
- **V3 (after a fix):** `-w <new sub id>` shows Pid 22035, ParentWindowId = current host window, and IsVisible true. The t10 screenshot shows the feed.
