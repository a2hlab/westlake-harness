# t2 C1 fix (review02): coalescing semantics only

- **Manifest:** `$WORKSPACES/westlake-harness-t37-peer/.../session-recovery/review02-manifest.json`, SHA-256 `f156d990caff276ce456027098d23fa0e9558530adaaf26319c2e0af5a4b220c`. All nine candidate files match it.
- **Changed relative to snapshot-01 (only these two):**
  - `session_recovery.h` → `cc1a2b3ccae8f2810a5ee8c8b68fde50d8ef03927b43c9ded83f1f8839f3ce1f`;
  - `session_stage_adapter.cpp` → `9fdb24b064c3bc35a88631bf21298028d4f4c707048bbefe2314fed4c79e5bb9`.
- JNI/ABI parts are not re-reviewed (they passed in `b1-fix-review.md`). Not compiled by me; the 1422 Gate assertions are the author's claim and I did not rerun them.

## Verdict: no blocking defect; C1 is closed for the coalescing semantics
- **Method keys are complete:**
  - `CallbackGate::knownMethod` lists 16 names.
  - The stage file has exactly 16 `callBridgeVoidMethod` call sites. Set difference: none missing, none extra.
  - The check also gates the enabled path. Because the sets are equal, normal sessions lose no callback; an unknown name would be logged (`session_stage_adapter.cpp:770-772`) rather than dropped silently.
- **Last-arrival order:**
  - `submit` removes the earlier entry with the same method and appends the new one (`session_recovery.h:48-52`). The buffer is therefore bounded by 16 distinct methods regardless of frequency, so 65 or more repeats can no longer overflow.
  - `overflow` is now set only by the unsupported-signature branch, which is unreachable with the current I/Z/J signatures.
  - **Interleaving example:** Background → Foreground → Background replays as [Foreground, Background].
  - **Cross-method example:** `NotifyWindowVisibility(false)` followed by `NotifySessionForeground` replays in that order. Both reach `dispatchAppVisibility` (DEX `c5bd7fd2`, see `session-review.md`), so the final Java state equals the final server state.
- **Close isolation is unchanged:**
  - `close()` clears `pending` and disables the gate.
  - After close, `submit` drops the callback (returns true without buffering), and `activate()` returns false.
  - `publish` still refuses an overflowed or non-buffering gate.
- **Binding to the actual stage calls:** the key is the same `methodName` literal passed at each call site. The lambda still captures only the copied values (line 770).

## Non-blocking note
- Coalescing by method name keeps only the last `onUpdateAvoidArea(type, …)`, so avoid areas of other types (status bar, cutout, keyboard) are dropped.
- In the bound DEX this has no effect: `SessionStageBridge.onUpdateAvoidArea` at `0x6ba4c` only logs (dump `90d75d72` L1168-1179).
- If a later Java version consumes avoid areas, the key should become `(method, type)` for that method.
