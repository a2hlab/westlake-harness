# t2 B1 fix candidate: incremental review

Snapshot `$HOME/.local/share/westlake/native-host-recovery-build-20261024/snapshot-01/candidate`. All nine files match `../source-pins.json` (`21a8c573…`). The peer directory now holds the same SHAs; the previously reviewed versions are not retained, so this is a read of the full new code against the base/ability38 originals, not a line diff against the prior candidate. Not compiled by me; no device or REA.

| File | SHA-256 |
|---|---|
| `oh_input_bridge.cpp` | `5e814a7d8c5118b855843f070094351df020a8cb9a3b2c0606658fc5e0b2ed97` |
| `oh_window_manager_client.cpp` | `418235c14fa012d7bab5a298c2dc99c5e0871022ab8dc6ccb438ffc87608a073` |
| `oh_window_manager_client.h` | `5f36b56bfb61ee4683229bebaeb4e1abe6edacebed3d5688c9c725c26555f083` |
| `session_recovery.cpp` | `5cd59abf8a7e2a7e88da29bcbdace65c3857962b429258558ae76f965f3dfe24` |
| `session_recovery.h` | `7607effafb220519fd50781ce45ec816c30899206870c00030509022884e39a5` |
| `session_stage_adapter.cpp` | `a71f76eb152efa11b493bc176775244627e92eb742db0b71093e754f09212b24` |
| `session_stage_adapter.h` | `9d818e3a88ece3c6c0cd52a2b032563023805f7c3bc4e71afa0955355cd4cb62` |
| `wmc_recovery_impl.inc` | `711a2ff8f4e1e146dc3c4f464952edb06b2308dc337f5545c5689775a2d6449c` |
| `wmc_recovery_state.inc` | `3bae1d4f07105b42fed32d23cc4b9d41dc91ca56d7298770888320867a33e1c2` |

## Verdict
**No blocking defect in JNI lifetime, threading or callback isolation.** There is **one conditional blocker** (C1), triggered when the callback buffer overflows.

## Checked OK
- **No cached `JNIEnv`, `va_list` or local reference:**
  - `callBridgeVoidMethod` (`session_stage_adapter.cpp:746-771`) copies the varargs into a `std::vector<jvalue>` immediately and calls `va_end` (757).
  - Every signature in the file is I/Z/J (`()V` ×4, `(Z)V` ×4, `(IZ)V` ×2, `(I)V`, `(IIII)V`, `(IIIII)V` ×3, `(J)V`). So the unsupported branch (758-763) is not reachable today, and the normal path does not lose callbacks.
  - The deferred lambda captures only `name`/`sig` strings and the value vector (770).
  - Replay runs `callBridgeValues` (773-806), which obtains a fresh `JNIEnv` on the replaying thread (attach and detach as needed), calls `CallVoidMethodA`, and clears exceptions.
- **Java references per endpoint:**
  - `recoveryEndpoint()` (91-97) constructs a new adapter, which takes its own `NewGlobalRef` of the window and creates its own bridge object (constructor 49-84).
  - Its destructor deletes only its own references (115-117), so nothing is shared with the old endpoint.
- **Lambda `this` lifetime:**
  - Pending callbacks live in the endpoint's own gate.
  - `activateRecoveryCallbacks()` is reached only through a live `sptr` (`wmc_recovery_impl.inc:180-185`).
  - `close()` and `beginBuffering()` clear `pending` (`session_recovery.h:21-28`).
- **Lock order:**
  - The callback entry takes `jniMutex_` then `gate.mutex`, and activation takes them in the same order (`session_stage_adapter.cpp:99-104`).
  - `publish` takes `gate.mutex` then `sessionMutex_` (`impl.inc:132-134`) and takes no `jniMutex_`.
  - Activation runs after `sessionMutex_` is released (176-180 vs 185), so Java called during replay can re-enter WMC.
  - I found no reverse ordering among the new code paths. Pre-existing WMC paths that call the stage while holding `sessionMutex_` were not re-audited.
- **Foreground re-read before activation:**
  - Activation needs a fresh record that is `Foreground` (stage 1/2 or window-ready) with id equal to the bound parent, plus the same state, the current actual id, and a gate that is still buffering (`impl.inc:172-185`).
  - A HIDDEN or INACTIVE record keeps the buffer closed. Focus is requested only after a successful activation.
- **Failure and destroy isolation:**
  - The old gate is closed before create (`impl.inc:69`) and on destroy.
  - `discard` drops the pending endpoint (127).
  - `publish` refuses an overflowed or non-buffering gate (133) or stale revision/id (136-139).
  - A retired, never-activated endpoint only buffers up to 64 entries and then drops (`session_recovery.h:32-33`).

## C1 (conditional blocker): an overflowed buffer leaves the window permanently mute
- `submit`: when the 65th deferred callback arrives, it sets `overflow = true` and clears all pending entries (`session_recovery.h:33`).
- `activate()` then returns false whenever `overflow` is set (38), and `enabled` never becomes true. Every later callback is dropped as well (32).
- `publish` also refuses an overflowed gate (`impl.inc:133`). But if the overflow happens **after** publish, while the host stays HIDDEN or INACTIVE, the committed endpoint is never activated.
- Effect: the Java window never receives the foreground or visibility-true callback, and the screen stays white for the life of the process. No log is written at activation time; only the `[HOST-SESSION]` outcome line from an earlier tick exists.
- Probability: likely low, because activation is normally attempted on the same tick as the commit. It becomes reachable when the host stays hidden after commit while the server sends rect, avoid-area or visibility callbacks.
- **Small fix options:**
  - (a) coalesce pending entries by method name and keep only the latest per method. There are at most about 17 distinct methods, so the buffer can no longer overflow from churn;
  - (b) at least log the overflow at activation and count it, so a white result is diagnosable.
