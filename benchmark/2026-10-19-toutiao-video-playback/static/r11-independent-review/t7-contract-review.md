# t7 debug-tool-compat — contract review (reviewer lane; NO substantive blocker)

Read-only review of main-tree `specs/toutiao-video-playback/t7-debug-tool-compat.spec.md` (4 scenarios,
parse/lint100). CX owns `tool-compat-r12` code. Purpose: validate an alternative reusable debugger
(NDK r23b static AArch64 server `13c0b4bf…` + SDK15 host `c6008509…`) on a dedicated self-owned OH
probe on idle board `5cd1e3dd…0923012c`, to route around the R11 SDK15-server `DataExtractor GetMaxU64`
assertion. Tool pass ≠ Toutiao playback / window-object proof. No device call by reviewer.

## Four-axis verdict — all PASS (no blocker)
- **Identity:** whitelist 5cd only, outer-held lock, read-only boot/kernel/SELinux/lock/proc first;
  target bound by this-launch receipt + boot/PID/birth/UID/exeSHA + server identity, never by name;
  od raw-byte cmdline + socket-inode→port-ownership; port 5039 proven free first, forward removed
  after. Default-deny without admission (zero device call); drift ⇒ refuse, never attach an existing
  app. Clean.
- **Hardware breakpoints:** require-hardware + remote-ohos + disable-memory-cache set first (same
  prelude validated in t6); exactly ONE explicit `--hardware` bp at the probe's noinline marker;
  IsHardware readback; two hits with distinct StopID, same-marker PC, increasing x0; no SW fallback /
  expr / target-call / reg mutation. The single-bp deterministic probe is a clean reduction of r11's
  multi-bp/return-association. HW-slot unavailability is a *failure outcome*, not a gap — this is the
  intended test of the open "HW slots unknown" question on a safe board.
- **Timeout / cleanup:** ≤15min window, 60s observation; delete own bp, detach keep-stopped false,
  independently confirm probe TracerPid=0 / non-T AND **count still increasing** (liveness proof);
  on failed detach, only after re-confirming boot/PID/birth/exeSHA may it terminate THIS OWN
  server/probe (safe — disposable), recording not-passed; never kill other processes or global hdc;
  120s self-exit is backstop not evidence; missing handshake/hit/cleanup ⇒ unknown/failed. Safer than
  r11 because the target is our throwaway.
- **Server-thread behavior:** directly exercises the server handshake + memory-read path where r11
  died; a server that cannot complete handshake+2 hits (assertion, hang, or protocol mismatch) ⇒
  connect-fail/timeout ⇒ failed/not-compatible (correct). Server is self-owned + killable + bound by
  socket inode; forward removed.
- **Scope:** does NOT modify R11 frozen tool pins; r23b server NOT auto-usable for Toutiao even if the
  probe passes (a successor observer version is separately accepted); human review signs only
  tool-compat on the probe, Toutiao object/playback stay unknown, R11 not silently relaxed. Aligns
  with "下一步不扩ANW改造".

## Minor non-blocking notes for CX's implementation (not contract defects)
1. Ensure the **self-owned lldb-server** is terminated / confirmed-exited at window end (not only the
   probe) and the 5039 forward removed, so nothing lingers holding the port for a later run (an r11
   `os._exit(2)` leftover forward, if any, is already caught by t7's "prove 5039 free first").
2. Host-lldb15 ↔ server-r23b protocol mismatch may present as a **hang** rather than an assertion; the
   60s timeout+cleanup covers it, and the contract already requires raw handshake bytes — capture them
   so a mismatch-hang is distinguishable from an assertion-crash for diagnosis.
3. `x0`=count relies on AAPCS64 (marker's first arg in x0); confirm the noinline marker's signature
   puts the counter in x0 and the marker is not tail-merged/inlined.

## Verdict
**No substantive blocker in the t7 contract.** Proceeding to wait for CX's tool-compat-r12 code; I
will review it on the same axes when it lands. Single CC window, no device call, ANW rework not expanded.
