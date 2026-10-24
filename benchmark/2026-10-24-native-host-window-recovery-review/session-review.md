# t2 session-recovery candidate: interim review (blocking points only)

Read-only review of `$WORKSPACES/westlake-harness-t37-peer/benchmark/2026-10-24-native-host-window-recovery/session-recovery/candidate/` at the SHAs below. **If any file changes, this review is stale for that file.** Nothing was compiled; no device, REA or peer modification. Diffs are against `bridge-d4fa-source-snapshot` ability38 WMC `1844e81b`, input `54057ec9`, stage header `54301267`, and base stage `54660865`. The Java line references are to the source-build-host snapshot `SessionStageBridge.java` `0757e594`, which is **not bound to the deployed JAR**.

| File | SHA-256 |
|---|---|
| `session_recovery.h` | `4889f6797c333ecb1c0da0a4624af5f73f142ed788c66c746df6221afe4bd715` |
| `session_recovery.cpp` | `c72ec08d968c80c9d2acbe4d58379e714c65caef52218c3b1257948c03619123` |
| `wmc_recovery_state.inc` | `2552947fb2c74a8e0e3f8fc226c8202b76f114dc170854684ed548cf8a53e4e1` |
| `wmc_recovery_impl.inc` | `cb48820ab03a1c6f3a014952c0d406f5ec43da34182454a4ed8d4bd10ec464d8` |
| `oh_window_manager_client.cpp` | `6b2eb9f8a79e4d945c33166b8039018c03a788b0ba6b97658671b7a8062b3646` |
| `oh_window_manager_client.h` | `ba44ead946a35639c9686bb00399770e9154ee657aba2312b319c84f938648f9` |
| `oh_input_bridge.cpp` | `5e814a7d8c5118b855843f070094351df020a8cb9a3b2c0606658fc5e0b2ed97` |
| `session_stage_adapter.h` | `9b97f47ee45dbfcc8b2e7d47b891737ef3efaf45b3c15603ba73fe2232e2602a` |
| `session_stage_adapter.cpp` | `6ddefda01c248e58998a79351d01f28d605b3748bbfab8195cd8b091b81d38e9` |

## Blocking risk (needs a decision before the device window)
**B1. The Android view root may stay "app invisible" after a committed recovery, so the screen stays white.**
- Trigger chain:
  1. Recents/Home puts the host in the background. If the server then sends `NotifySessionBackground` or `NotifyWindowVisibility(false)` to the **old** sub-window stage, the Java bridge calls `dispatchAppVisibility(false)` (`SessionStageBridge.java:69-73`, `:114-118`) and ViewRootImpl hides the DecorView and stops drawing.
  2. The host is killed and the old session is destroyed (OH destroy chain, no NotifyDestroy).
  3. Recovery creates a **new** stage endpoint with its gate closed (`session_stage_adapter.cpp:91-96`).
  4. `connect()` sends `Foreground` and `RaiseToAppTop` (`wmc_recovery_impl.inc:105-108`). Every server callback that comes back while the gate is closed (`NotifySessionForeground`, `NotifyWindowVisibility(true)`, `UpdateRect`, `SetActive`, `UpdateFocus`) is dropped (`session_stage_adapter.cpp:741-742`).
  5. `publish()` opens the gate (`wmc_recovery_impl.inc:146`) but nothing replays the dropped state. The `requestFocusForSession` at `:161-165` restores focus, not app visibility.
  6. Result: SSM shows a new sub-window attached to window 62, but Java never receives `dispatchAppVisibility(true)`, so no frame is produced.
- Unverified link: whether OH 6.1 actually delivers a background or visibility-false callback to the old sub-window stage before the parent dies.
  - **Check, read-only:** grep the existing child stderr between the Recents close and the reopen click for `[WESTLAKE-STAGE] NotifySessionBackground` / `NotifyWindowVisibility`. The earlier outer filter did not include these patterns.
- **Minimal fix options (choose one):**
  - (a) after a successful `publish`, deliver one explicit foreground/visibility-true call to Java on the new endpoint, for example by invoking `onNotifySessionForeground` once under the now-open gate;
  - (b) record the last visibility/foreground/rect callbacks received while the gate is closed and replay them at publish.

## Checked and OK at these SHAs
- **Same APP_WINDOW node and producer:**
  - the recipe and `windowNode` are captured from the initial successful session (`oh_window_manager_client.cpp:2006-2020`);
  - `create()` marshals that same node (`wmc_recovery_impl.inc:75`);
  - `publish()` swaps only the remote, stage and window id, leaving the Java SurfaceControl, nodes and producer untouched (`:133-146`);
  - `discard()` destroys only the new actual session (`:110-123`).
- **Wire format:** the request and reply layout of `CreateAndConnectSpecificSession` matches the OH 6.1 stub (`scene_session_manager_stub.cpp:305-347`):
  - request: stage, channel, node, property, then a token only if `GetTokenState`;
  - reply: id, remote, config, level, display, type, rc.
- **Old stage isolation:** the old gate is closed before create (`session_recovery.cpp:41`, `wmc_recovery_impl.inc:63`) and on destroy (`oh_window_manager_client.cpp:2422-2423`). Publication holds the new gate's epoch mutex (`wmc_recovery_impl.inc:125-127`).
- **ID mapping:**
  - Java keeps the logical id (`sessions_` key);
  - SSM operations use the actual id (`oh_window_manager_client.cpp:2465`, `:2653`);
  - MMI translates actual to logical before `isKnownSession` (`oh_input_bridge.cpp:4960`, `:4979`);
  - retired ids map to -1, which is dropped (`session_recovery.cpp:83-87`);
  - `Routes::install` happens at the initial create (`oh_window_manager_client.cpp:2011`).
- **No rebuild for the same host:**
  - a candidate equal to the bound parent is Idle (`session_recovery.cpp:20`);
  - the old parent must be `Missing` (`WM_ERROR_NULLPTR`) before anything is created (`:28-30`).
- **HIDDEN / INACTIVE do not take foreground:**
  - `Foreground()` accepts only window-ready or stage 1/2 (`session_recovery.cpp:3-7`);
  - the focus request is made only after a fresh foreground record whose id equals the new parent (`wmc_recovery_impl.inc:161-165`).
- **No resource destruction or unbounded retry:**
  - polls are at least 1 s apart (`session_recovery.cpp:17`);
  - each record identity is tried once (`:22-27`), with at most 128 identities before a stop (`:26`);
  - any ambiguous result stops further attempts (`:29`, `:32`, `:43`, `:53-56`).

## Non-blocking notes
- `seen_` records an identity **before** the transient checks (`session_recovery.cpp:27` precedes `:28-39`). A record that is rejected only because the old parent has not yet been removed asynchronously is never retried. Recovery then waits for the host's next id-bearing record, such as SHOWN or ACTIVE.
- A stub `ERR_INVALID_STATE` (the server returned no session) arrives as an IPC error, is classified as `Unknown` (`wmc_recovery_impl.inc:81`), and stops recovery for the rest of the process. That is conservative; mapping it to `Failed` would allow a later record.
- The record path is hard-coded (`wmc_recovery_impl.inc:154`, user 100, `haps/entry/files`). Whether the deployed child can read it is still deferred, as in t1.
- `connect()` sends Foreground/RaiseToAppTop without re-checking HIDDEN between the last `unchanged()` and the IPC. This is a narrow race window, acceptable.

## Seal (interim review closed at the SHAs above)
- **B1 is a source-level risk, not an observed event.** No device run has shown that the old stage received a background or visibility-false callback, or that a committed recovery stayed white.
- **Java binding is limited:**
  - The behaviour quoted in B1 step 1 (`dispatchAppVisibility(false)` on background) comes from the source-build-host snapshot `SessionStageBridge.java` `0757e594`. That snapshot is **not proven** to be the deployed source.
  - In main `benchmark/2026-10-24-bcp-window-source-binding/` (`classes.json` `0e14f19d…`, `dex-method-excerpts.txt` `3c02eeca…`, historical CLAMP48 BCP JAR `ea5d8b27…`), the method **names** `onNotifySessionBackground`, `onNotifySessionForeground`, `onNotifyWindowVisibility` and `dispatchAppVisibility` exist in `Ladapter/window/SessionStageBridge;`.
  - Only the bodies of `onNotifyDestroy` and `WindowSessionAdapter.remove` were extracted there. The bodies of the three visibility/foreground methods were **not** extracted, so their DEX behaviour is unconfirmed. This review does not infer it.
- The next step is an incremental review of the peer's B1 fix once its SHAs are stable. This sealed review does not cover any later file version.

## Evidence increment: DEX method bodies for B1 step 1 (existing dump only, no new tool run)
- **Dump:** `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-24-bcp-window-source-binding/.private/window-classes.txt`, SHA-256 `90d75d72da3d91f75b350bea71963adbde4bb945033aa8d3810bc23e7b043f7e`, 5073 lines.
- **DEX binding:** the dump itself carries no DEX identity, so the binding is indirect.
  - Main `dex-method-excerpts.txt` (`3c02eeca…`) quotes this dump's lines L446 `[06b4cc] onNotifyDestroy` and L4649 `[0709bc] WindowSessionAdapter.remove`. The same lines and addresses are in this file.
  - Main `raw-index.json` binds that disassembly to `classes.dex` `c5bd7fd23b0ed5c8a6d2b8dce0bd387f899b6fd0b58f5423314c3e90983d35cf`, the sole member of BCP JAR `ea5d8b27…`.
- **Bodies (`Ladapter/window/SessionStageBridge;`):**
  - `onNotifySessionBackground(IZ)V` @`0x6b750` (dump L775-789): `logBridged`, then `const/4 v1, #0`, then `dispatchAppVisibility(Z)V` (method@075d), so it dispatches **false**.
  - `onNotifySessionForeground(IZ)V` @`0x6b778` (L793-809): the same pattern with `#1`, so it dispatches **true**.
  - `onNotifyWindowVisibility(Z)V` @`0x6b8a0` (L959-979): `dispatchAppVisibility(Z)V` is called with the incoming boolean `v3`.
- **Effect on B1:**
  - The Java-semantics gap in step 1 is closed for this DEX: a background or visibility-false callback reaching Java does call `dispatchAppVisibility(false)`.
  - It still does **not** show that OH sends such a callback to the old sub-window stage at runtime, or that this DEX is the one loaded on the current boot (the T106 disk record is historical). B1 remains a source-level risk.
