# T36 — host recreation reentry candidate (r4), offline replay

Status: **offline candidate, production-function replay passes; not deployed, not screenshot-verified.**
No device, no REA, no retry of the safety-refused parent environ read. The root cause it targets is
still **inferred** (T35 `whitescreen-01`), not observed.

## What was wrong (r3, deployed watchdog.sh `8bf74a08`)

T35 whitescreen-01 on 61b: after the user closed Toutiao, the guardian retired child 7140 correctly
(`process_exit` / strict exited) and sat in `AWAITING_REENTRY`, but the icon tap produced a white host
and **no event at all**. Static reading of the deployed sources:

- `rc_focus_state` treats `imehost0` as the host only if `verify_parent_window_soft` passes, i.e. the
  live parent's `WL_PARENT_ID` equals the focused WID. Otherwise it returns `other`, which silently
  disarms (no spawn, no event).
- `WL_PARENT_ID` is written into `run.sh` only by `real-start-parent-bounded.sh:9` when the parent is
  started; `real-spawn.sh` just sends `host_spawn` on the old socket. There is **no rebind path**.
- After the host was recreated (WID 66, later 72) the bootstrap parent kept its old WID, so every
  later host focus was `other`.

Deleting the WID gate would not fix this: `spawn.sh`/`start-parent.sh` re-verify the parent window.

## What r4 does (`src/`, diffs in `patch/`)

1. **Classify instead of going silent.** `parent_window_reason` (same reads as the gate) explains a
   failed parent-window check. When the host process is verified and the only failure is
   `wid_mismatch`, `rc_focus_state` returns `newhost <wid>`. Every other failure stays `other`, and r4
   common logs `focus_other reason=...` once per reason change. `rc_focus_reason` is reset per call.
   **The WID gate itself is unchanged** (test C.wid_gate_kept).
2. **Strict, one-shot parent epoch switch** (`rc_parent_epoch_switch`). It runs only on a genuine
   desktop→newhost edge, after the existing checks — child `gone`, no owned window, `rc_gates_ok` —
   in the same order as r3. Steps:
   - **Refuse without acting (rc 1)** unless all of these hold:
     - the old parent passes exact `parent_owned` (boot/PID/birth/namespace/exe SHA/run.sh inode);
     - the direct-child enumeration is complete and empty (an unreadable stat is unknown and refused);
     - exactly one `net/unix` listener inode exists for the fixed socket;
     - the only fd holder of that inode is the old parent;
     - the socket file identity is readable.
   - Persist `parent-epoch phase=stopping old=P:B wid sock sockfile`.
   - Re-check exact identity, then arm `rc_epoch_hold`. **From here on every failure is partial (rc 2)
     and never starts a second parent or spawns.**
   - Send one `SIGTERM` through `rc_send_term`. This is the only `kill -15` in the file, and it never
     reaches a generic or `parent_owned`-only path. Then wait up to 5 s for the birth to change.
   - Require no fd holder after exit. Unlink the socket only if its file identity is unchanged.
   - Run the **unchanged** `start-parent.sh`. It does its own `foreground_window_id`, the `run.sh`
     sed (new inode), the socket wait, `parent_owned`, `verify_parent_window`, and the `parent-identity`
     write and readback.
   - Require the new parent to be alive, exact, and bound to **the WID that triggered the switch**.
   - Persist `phase=switched old new wid`, update `parent`/`TT_PARENT_*`/instance, and log
     `parent_epoch_switched`.
3. Then `rc_gates_ok` is re-run, and the **unchanged** r3 single-spawn path follows.

## Evidence (receipts: `receipts/`, originals in private `$HOME/.local/share/westlake/manual-video-regression-20261021/host-reentry-candidate/`)

| replay | result |
|---|---|
| `tests/run-epoch-tests.sh` (whole r4 watchdog sourced; only device seams stubbed) | **140 passed, 0 failed** — A 11, B1 14, B2 30, B3 72, B4 7, C 6 |
| `tests/run-r3-suite-on-r4.sh` (unchanged r3 retirement suite, helper overlay = r2 helpers + r4 common) | **70 behavioural pass**; the only failure is the suite's own r3-common hash pin (expected, asserted exactly) |
| original r3 suite on r3 (unchanged) | 71 passed, 0 failed |
| `sh -n` on all four scripts | SYNTAX_OK |

Acceptance mapping:

- **New host, old child exited (B1).** Uses the 61b scene numbers: parent 5089/b5573 on WID 30, host
  on WID 66, child 7140 retired. Result: one TERM to 5089, one `start-parent`, one spawn. The new
  parent 6100/6200 is bound to WID 66 and read back. `start-parent` runs only after the old parent
  exited and the socket file was removed. Event order: `child_retired < parent_epoch_stop <
  parent_epoch_switched < child_retirement_cleared(spawn_started) < reentry_spawn_ok`, so the
  retirement tuple is kept until the new spawn boundary.
- **Live child / unknown refused (B2).** Each of these produces an explicit reason and no TERM, socket
  unlink, start or spawn:
  - a live child;
  - another direct child;
  - an unreadable `/proc` stat;
  - no socket listener;
  - a second fd holder;
  - a missing socket file;
  - no desktop edge;
  - parent identity drift.
- **Partial failure, no double start (B3).** Injected faults:
  - parent not exited;
  - signal failed;
  - replacement listener;
  - socket file replaced;
  - start nonzero, garbage or dead;
  - new parent bound to another WID;
  - persistence failure before the signal and after the start.

  None of them reaches a second parent or a spawn. The old identity stays in the event log and in
  `parent-epoch`, and the tuple is not cleared.
  - If the old parent is still alive, the sticky hold consumes the next edge.
  - If it is gone, the loop-top gate refuses `parent_identity` (rc 2, lock kept).
  - A persistence failure is `io_fail` (exit 5, `IO_FAILED`).
- **Warm return / history (B4 + r3 suite).** On a warm return the parent is kept and nothing is
  spawned. A same-WID reentry does not switch the epoch. `other` cancels the arm. r3 behaviour passes
  70/70.

## Hard-precondition gaps (not hidden)

1. The live parent's `WL_PARENT_ID` on 61b was **never observed**. The T35 read was stopped by the
   safety classifier and is not retried. The cause stays INFERRED until the deploy card sees a
   `focus_other` or `newhost` event on the board.
2. Socket ownership is read from the old parent's `/proc/<pid>/net/unix` and every `/proc/*/fd`. This
   is sound only if the guardian (root on 61b) sees that network namespace and all PIDs. It is
   unverified on the device, so an incomplete view fails closed (`socket_owner_unknown` /
   `socket_holders_unknown`).
3. The real SIGTERM behaviour of the parent (clean exit within 5 s, socket closed, no init-supplied
   socket) is replayed only through the `rc_send_term` seam.
4. Recovery after a post-exit partial failure, or after `io_fail`, is manual by design: there is no
   automatic retry.
5. If the host is recreated a second time during the switch, the result is a fail-closed hold
   (`new_parent_wid_wid_mismatch`), not a retry.

The Codex peer independent review requested by the card is **not** part of this delivery. Entry
points for it are `patch/watchdog-r3-to-r4.diff` (the `rc_parent_epoch_switch` / `rc_focus_state`
hunks) and `patch/reentry-common-r3-to-r4.diff` (the `newhost` branch).

## Rule set by this card

A guardian that gates on a mutable host attribute (WID) must log *why* it rejects a host focus and
own an explicit, proven-exclusive path to rebind. Reaching that path needs an exact old identity, a
proven-empty child set, a proven socket owner, and a single signal behind a sticky hold. Silently
mapping a mismatch to `other` hid this wall for a whole session.

## Revision after rejection (r4 `9072bbfb` → r4b `3aba9d8e` → r4c `c73dadb3`)

The outer loop rejected r4 `9072bbfb`, the exact object T37 replayed. **The author's 140/0 replay does
not offset T37's proven counterexamples.** r4 stays in `src/watchdog-reentry-r4.sh` as the failed
version; the revisions are new files.

| T37 counterexample | r4b/r4c fix |
|---|---|
| birth read failure taken as exit → unlink/start | `rc_wait_exit`: exited only if the `/proc` entry is gone **and** the guardian's own entry proves a live view. PID reuse → hold. Unreadable entry → hold. |
| malformed stat, missing proc root, missing fd dir, failed readlink taken as empty | Strict `rc_stat_ppid`. Enumerations require a live-view witness and ≥1 entry. An unreadable existing entry, fd dir or fd link → unknown. Only a vanished entry is skipped. |
| socket row not checked as listener / creation ownership | Row must be listening (`00010000`), stream or seqpacket, `01`, and match the exact path. It must be visible in the guardian's own net view, and the old parent must be its only holder. After exit, before unlink: no holder, unchanged socket file id, zero listener rows. |
| read-only `parent_owned` not bound to a recorded epoch | Signal authority is the guardian-written `parent-epoch` record (`bound` at bootstrap after its own `start-parent`, or `switched`). It must name the exact parent, with mntns, socket inode, socket file id and (r4c) run.sh inode unchanged. Children are re-checked right before TERM. |
| `rb_owned_pids` failure taken as empty → spawn | The frozen helper's rc is only the last loop test. `rc_owned_pids_strict` replaces it in the window check, `do_one_launch` and pre-TERM. A same-uid entry is non-owned only with a readable non-route-b exe. (r4c) A malformed `Uid:` line → unknown. |

Evidence, kept separate:

- **Unmodified peer harness on r4b.** The counterexamples no longer reproduce, but only because the
  new epoch-record gate refuses first. Not used as evidence.
- **Peer case scripts, unchanged, with an additive fixture** (`peer-replay/replay_r4b.py`: live-view
  entry, ns links, a bound epoch record, real `rb_uid`). r4b 26/26. The same fixture on 9072bbfb gives
  9/26: the counterexamples are caught there, and the success controls succeed on both.
- **Peer on r4c `c73dadb3`.** 18/18 function replay, 0 harness errors. This is the peer's report and
  was not re-run here.

Complete candidate package: `candidate-package-r4c/`, built by `tests/assemble-payload.py`, 22 files.
Only `watchdog.sh` and `reentry-common.sh` change against the r3 package. The entry.sh literal pin,
`members.tsv`, `startup.env`, `startup.expected.sha256` and `MANIFEST.sha256` are recomputed. The
peer's `assembly_audit` gives 165/165 rows pass (`peer-replay/r4c-assembly-audit`). The package is
**disabled and unapproved** (`STARTUP_ENABLED=0`). `deploy-cfg`, CHAIN and generation are not
regenerated; that belongs to the deploy card.

Open items:

- The r3 regression suite fails on r4b (53/18). Its fixture has no complete `/proc`, so strict
  enumeration answers unknown.
- Author suites were not re-run on r4c.
- **No device run: the white screen is NOT claimed fixed.**
