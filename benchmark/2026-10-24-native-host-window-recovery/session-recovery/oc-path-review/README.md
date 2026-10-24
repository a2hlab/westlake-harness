# T126 OC path review — native host-window session recovery (review02) (2026-10-24)

Independent static source review of the fixed review02 candidate (input package `$PRIVATE/t126-review02-input/`, 14/14 SHA-256 verified against `input-manifest.json`; `source_commit 5970ec078c…` is outer-supplied provenance, not independently verified). The initial blocked record is preserved locally only (outside public deliverables) under `$PRIVATE/t126-review02-input/blocked-originals/`; it is deliberately not linked from landing-paths to avoid stale links and user-path disclosure. No device, no REA, no permission changes, no candidate edits, no deploy retry; stopped T71/T74/T91/T121 controller/executor bodies untouched.

## Answers to the three assigned questions

**Q1 — Does a stale/invalid old parent permanently skip recovery?** **No** — unless the probe IPC itself is ambiguous (see F1). An old parent that answers `Rejected`/still-valid returns `Outcome::Rejected` and later polls re-evaluate normally (`candidate/session_recovery.cpp:30`). A genuinely missing parent (`WM_ERROR_NULLPTR` → `Reply::Missing`, `candidate/wmc_recovery_impl.inc:66`) is exactly the admission gate that allows recovery to proceed. Runtime caveat: whether SSM actually returns NULLPTR for a dead parent is runtime-unverified here.

**Q2 — Do failed/unknown IPC states block later legal new hosts?** **Per logical session: yes, permanently** (this is F1 below); **across sessions: no** — each admitted session gets its own `Coordinator` instance (`candidate/oh_window_manager_client.cpp:2020-2022`), so one session's stop does not affect another session's recovery.

**Q3 — Do focus/input paths still use stale IDs after commit?** **No stale-ID use found on the reviewed paths.** `publish()` writes `entry.windowId = next.actual` under `sessionMutex_` before publishing the parent cache (`wmc_recovery_impl.inc:144,146`); `requestFocusForSession` reads `windowId` from `sessions_` under the same mutex (`oh_window_manager_client.cpp:2642-2644`), so focus always targets the committed actual ID. `Routes::replace` retires the old actual ID (`session_recovery.cpp:75`) and `Routes::logical` returns `-1` for retired IDs (`session_recovery.cpp:86`) — retired IDs never fall back. Both MMI entries translate `GetAgentWindowId()` through the route table (`oh_input_bridge.cpp:4960,4979`); unrecovered sessions keep actual==logical so pass-through is correct. `destroySession` erases routes and recovery state (`oh_window_manager_client.cpp:2418-2419`).

## Actionable conclusions (≤3)

**F1 (only finding) — Per-Coordinator permanent recovery stop on any ambiguous IPC result; no retry and no reset within that Coordinator's lifetime.** Static source fact; runtime impact unverified. Outer ruling: confirmed static limitation / to-be-verified runtime risk; **not** the current white-screen root cause; no candidate modification started. This partially implements the spec's explicit anti-duplicate policy for unknown create results.
- Terminal latch: `session_recovery.cpp:16` (`if (stopped_) return Outcome::StoppedUnknown`).
- All five `Reply::Unknown` branches latch it: `session_recovery.cpp:28,31,43,47,55`; plus the 128-identity bound at `session_recovery.cpp:26`. Field declared `session_recovery.h:97`; no code path ever resets it.
- Sources of `Unknown`: `wmc_recovery_impl.inc:63-67` (parent probe: any IPC error/unreadable reply), `:82,88,93` (create: IPC failure, unreadable parcelables, **even a nonzero server rc**), plus connect/cleanup paths in `session_recovery.cpp:55` (comment: "stop all later creates").
- Consequence: one transient IPC fault on the `TF_SYNC,1` channel permanently disables host-window recovery **for the lifetime of that Coordinator** — until the logical session is destroyed/re-created — even when later host records are legal and the fault has cleared. It does not affect other sessions or new processes. Whether transient IPC faults occur on device is runtime-unverified; no on-device trigger evidence exists.
- No change proposed: the anti-duplicate stop on unknown create results is contractual; no generic unlatch is suggested.

No second or third actionable defect found within the assigned scope. B1/C1 not re-argued (already fixed per card). This review is not evidence that the observed white screen is fixed and not a seal; t2 lint status (100% with warnings) is outer-reported and not re-verified here.

## Limits

Static review only. The cross-compile receipts referenced in `session-recovery/results.json` are marked `candidate_inputs_current=false` (historical snapshot01 objects) — build currency of the review02 bytes was not part of the three questions and is not re-verified here.
