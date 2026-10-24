# ABI consumer review — native session recovery t2

**Current verdict: the latest side-table revision removes the identified WMC/policy ABI blocker. Do not expand the build to policy solely on the superseded layout finding.** The proposed WMC/Input/stage plus new core/reader set has no additional mandatory layout consumer identified in this bounded review. This is not a build, complete ODR proof, ID-semantics signoff or runtime qualification.

## Latest header recheck

- Candidate `oh_window_manager_client.h` SHA **5f36b56bfb61ee4683229bebaeb4e1abe6edacebed3d5688c9c725c26555f083**, compared with Ability38/Focus34 baseline header **71561caf1ed115d2a717bb3de80bc2a4652c96f2c690e91fe377014a96044732**.
- Removing comments/whitespace, the entire data-member tail from `bool connected_ = false;` through the end of the class is **identical**. This includes member order/types, the complete `SessionEntry`, map, recursive mutex and next-ID fields. `OHWindowSession` is also identical.
- The new header adds includes, a forward declaration, nonvirtual methods and `static recoveryStates()` (line 245); the destructor is now out-of-line. It no longer inserts observer fields into the instance or recovery/revision fields into `SessionEntry`. Static function declarations allocate no per-instance storage. The existing inline `isConnected()` accesses the unchanged member layout.
- Candidate `session_stage_adapter.h` SHA **9d818e3a88ece3c6c0cd52a2b032563023805f7c3bc4e71afa0955355cd4cb62**, baseline **54301267b82b9d6a9f9df239e86eacfceabd4058e398c1cd179cbab10bf7c7b8**. This class still adds `recoveryGate_` before JNI fields (line 319), changes size/offsets, and adds nonvirtual/inline methods. The existing virtual declarations are unchanged. Both its implementation and its allocator WMC are already in the proposed rebuild set.

## Superseded finding retained separately

The first inspected WMC header **ba44ead946a35639c9686bb00399770e9154ee657aba2312b319c84f938648f9** inserted observer atomics/thread before `connected_`, a recovery pointer before `SessionEntry::surfaceNodeId`, and a revision before `wmsShown`. For **that earlier candidate**, retaining the old policy object was incorrect. During this live review the author moved those fields to a side table. The intermediate draft captured new hashes with the old layout discussion; it was not a valid final binding and is explicitly corrected here. No build should be expanded based on that stale draft.

The concrete consumer remains useful evidence: Focus34 `framework/window/jni/oh_window_policy.cpp:19–22` locks `sessionMutex_`, searches `sessions_`, and reads `it->second.sessionRemote`. Lines 13–15 encode offsets 24/48/24 under `OH_WINDOW_POLICY_OVERLAY`; activation of that macro for the final object was not established here. Since the latest candidate restores the full data tail, these accesses do **not** by themselves require another policy compile now.

Actual linked policy object: `$ORB_WS/out-focus34/incremental/objects/westlake_framework_window_jni_oh_window_policy.cpp.o`, SHA **10144d24281a3c61e86ff302cf23d7a4fbbd79647d40891faa893968253f32e9**, independently rehashed from baseline staging. Original `.o.d:4` binds the Focus34 WMC header; depfile SHA **0d3464582c0370ba303e9beebebde7caaee2fff40a02bcb77dfe31d9cb7f06d1**. Its recorded/recomputed dependency key is **e5e0f140fce09224f8db3b10be926480f2f9f9b2c07907d778c08e43a554e159**.

## Other bounded consumers

| Consumer source under the snapshot | Expression / location | ABI conclusion for these header edits |
| --- | --- | --- |
| Ability38 `framework/window/jni/oh_window_manager_client.cpp` | singleton construction at 291; `new SessionStageAdapter` at 1794 | Already in proposed rebuild; owns WMC storage and stage allocation size. |
| Base `framework/window/jni/session_stage_adapter.cpp` | constructor/destructor at 36/91; member accesses throughout | Already in proposed rebuild; original object `out-touch21/fd/bridge15/objects/westlake_framework_window_jni_session_stage_adapter.cpp.o`, SHA `7501dad3afadca9d8e98fe924de7d919cdf3f1923af65e294ac040eb82fd7c4d`. |
| Focus34 `framework/core/jni/oh_environment.cpp` | 94 `getInstance().connect()`, 126 `.disconnect()` | Calls existing out-of-line methods, no detected layout/sizeof/allocation/inline getter use. |
| Focus34 `framework/surface/jni/oh_surface_bridge.cpp` | 188 `getInstance().getRSSurfaceNode(sessionId)` | Out-of-line call; no detected WMC layout dependence. |
| Focus34 `framework/window/jni/window_manager_adapter.cpp` | 28 takes address of `getInstance()` | Opaque pointer, no detected layout access. |
| Focus34 `framework/window/jni/window_session_adapter.cpp` | 52/73/99/107/111/119/126/218 getInstance/create/update/destroy/show/hide/node | Existing out-of-line API calls. Returned `OHWindowSession` layout is unchanged by the header diff. |

The stage header prepends `recoveryGate_` before JNI member fields and adds nonvirtual methods/inline accessors. Its existing virtual method declarations are unchanged; this does not by itself prove a vtable-slot change. It does change object size/member offsets. Both allocator WMC and stage implementation must use the new header; they are already in the proposed three TUs. The new `recoveryGate()` / `recoveryReady()` inline accessors must likewise be compiled with that header. The WMC `isConnected()` getter remains inline at an unchanged member offset in the latest revision; no call to it was found in the bounded linked-source set. This is an ABI-consumer review, not a claim of full C++ ODR equivalence for mixed-generation class definitions.

Coverage was bounded to the snapshot's 50 base source records plus its recorded Focus34/Ability38 overrides and the actual baseline/T29 link object list. Of 53 linked `.o` arguments, 47 have matching dependency records in the existing window archive. Seven depfiles include either reviewed header (WMC, stage, policy, environment, surface, window-manager and window-session). Three additional T29 consumer depfiles (`consumer-0.d`, `consumer-1.d`, `consumer-logger.d`) contain neither header. The two CRT objects are not project class consumers. The remaining T18 audio object has no matching `.d` in this window archive; its recorded input pins do not list either header, but that is not an exhaustive fresh preprocessing proof. No whole-repository search or build was performed.

## Separate keep-screen-on ID question

Policy line 22 selects the session remote from the entry, while lines 29–35 serialize `ACTION_UPDATE_KEEP_SCREEN_ON`, presence=true, **`WriteUint32(sessionId)`**, enabled, and send to that remote. Thus after logical/actual IDs diverge, the outgoing integer demonstrably remains the Java logical ID. This is separate from the superseded ABI break; it is an open semantic question, not a blocker imposed on the current three-TU candidate by this review.

No corresponding pinned OH `WindowSessionProperty` action deserializer / `SessionStub` update-property handler / keep-screen-on consumer body was present in the bounded local source and already collected CC excerpts inspected here. Therefore this report does **not** assert that the integer is used for an actual-ID lookup, ignored, or validated against the target remote. Minimal next source evidence is the `ACTION_UPDATE_KEEP_SCREEN_ON` serialization/deserialization and receiving action branch from the already identified OH version. If it requires actual persistent ID, select both `sessionRemote` and actual ID from one coherent committed recovery entry, then write the actual ID; do not merely substitute an unverified global/new-host ID. Preserve existing frozen keep-screen-on behavior and its validation requirements. No ID-semantic source patch is authorized or made by this review.

## Exact input pins

- `peer/benchmark/2026-10-24-native-host-window-recovery/session-recovery/candidate/oh_window_manager_client.h`: `5f36b56bfb61ee4683229bebaeb4e1abe6edacebed3d5688c9c725c26555f083`
- `peer/benchmark/2026-10-24-native-host-window-recovery/session-recovery/candidate/session_stage_adapter.h`: `9d818e3a88ece3c6c0cd52a2b032563023805f7c3bc4e71afa0955355cd4cb62`
- `main/sources/api-implementations/bridge-d4fa-source-snapshot/ability38/framework/window/jni/oh_window_manager_client.h`: `71561caf1ed115d2a717bb3de80bc2a4652c96f2c690e91fe377014a96044732`
- `main/sources/api-implementations/bridge-d4fa-source-snapshot/ability38/framework/window/jni/session_stage_adapter.h`: `54301267b82b9d6a9f9df239e86eacfceabd4058e398c1cd179cbab10bf7c7b8`
- `main/sources/api-implementations/bridge-d4fa-source-snapshot/focus34/framework/window/jni/oh_window_policy.cpp`: `959a2f0ff90a1d2c5982114e9f79c4b0cb464146370aa6e47848af9b91b10e3a`
- `main/sources/api-implementations/bridge-d4fa-source-snapshot/snapshot.json`: `8f395ea9bbadcd4a6ac73364159f1d19109ba19f135e4c8e3642e5a47adbd6b6`

Dependency evidence: existing `window.tar.gz`, members under `ORB_WS/out-focus34/incremental/objects/` and the original WMC/stage paths; no archive extraction or source mutation. Link-list evidence: `$HOME/.local/share/westlake/wmc-baseline-build-20261024/mac-original-link-01/argv.json`, already producing the exact T29 b0e baseline. This review changes only this report: zero builds, device/SSH/REA operations, or candidate edits.
