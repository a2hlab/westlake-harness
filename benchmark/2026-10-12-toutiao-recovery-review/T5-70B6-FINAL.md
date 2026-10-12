# Frozen T5 checkpoint: rejected for deployment

## Evidence first

The immutable object is `70b6eeda5811819a6fcb03061906838ffce5f963`, not the
editing worktree. Its checkpoint manifest is `3997ee32f07f3f31eef0ae61b39d9ac099a4b5b5d618eb0ce3ffa41baf48972d`;
the executed Python program is `58244f9c1aab93a63ad68f0c4b3ca16fab887d9711b01d5891900b6067130b2c`.
All 58 manifest entries match the exported Git bytes. The author's checkpoint
already records executor tests exit 1; this review does not relabel that as PASS.

Independent subprocesses executed the frozen CLI, with real plan/auth files,
full plan digest, and an explicit caller auth digest. No `_sha` shortcut was
used. Twenty-six CLI cases completed: 22 expected outcomes, three blockers,
and one informational preserved-stop observation. Seven boot-shell cases and
ten receipt/known-answer tests passed, separately from CLI acceptance.

## Three blockers sent directly to t0

1. **Interrupted direct placement cannot be rolled back.** In `partial_send`,
   the entry and first watchdog alias were written; the second alias retained
   seven bytes after failed transfer. Apply exits 2. Rollback exits 2 with
   `foreign/partial replacement`, before restoring the first alias. There is
   no rollback receipt or stop, and both aliases remain unrestored.
   Frozen `executor.py:122` sends directly to controls; `:191` rejects partials.
   Fix the transaction's partial-write recovery or validated atomic placement;
   do not widen acceptance to arbitrary foreign bytes.
2. **Unknown after-label reaches a write.** `after.label=null` passes the
   key-presence check at `executor.py:38`. The entry and first watchdog alias
   are sent before `chcon None` fails. Apply exits 2, but rejection is too late.
   Known metadata values must be validated before the first write, not merely
   checked for key presence.
3. **Zero-write, missing ROOT does not close as a no-op.** Backups and
   `transaction.json` exist, but failure of the first mkdir leaves ROOT absent
   and sends zero files; both original aliases are unchanged. Rollback at
   `executor.py:166` redirects to `ROOT/stop` without its parent and exits 2.
   The stage for CFG isolation also lives under ROOT (`:106`). A real local
   POSIX-shell missing-parent redirection independently fails, confirming the
   model. No stop or success receipt is fabricated. Distinguish a verified
   zero-write no-op from an already-written transaction requiring restoration.

## Passing and limited observations

- Preview makes zero transport calls. Wrong pin/plan/serial/boot/expiry,
  missing preimage label, backup truncation, and observed preimage drift reject
  without sending controls. Full real-file authorization is reachable.
- Guardian PID reuse, wrong UID, wrong argv, and mismatched lock boot reject
  before creating stop. A guardian that stays alive receives only cooperative
  stop; timeout fails without a signal or completed receipt.
- An exact inert CFG followed by injected failure is retryable: first rollback
  exits 2 without completion, retry exits 0 and restores both aliases. This
  previously suspected retry blocker is **not present** in this frozen object.
- Corrupt backups and wrong transaction binding reject before rollback writes.
  Authorized current-boot rollback works while retaining the original origin.
- `old_stop_drift` changes only fixture metadata between apply and rollback.
  Rollback does not recheck this preserved item, but neither removes nor writes
  it. This is an observation, not a new claim that the program cleared stop.
- Seven selected real boot-shell tests execute relocated frozen source, with
  recorded tools and a substituted entry endpoint: two kernel boots without a
  Mac ticket, previous/root stop, unsigned/config/member drift, and installed
  UID mismatch. These do **not** prove fresh real WID, parent namespaces,
  init token, screenshot acquisition, refresh/article, or autonomous board UI.

## Reproduction and boundaries

The protocol model never invokes HDC, USB, shell commands on a device, remote
tools, or VM. Its directory model enforces missing parents. The CLI projection
has four original members, in original order: entry, two watchdog aliases, CFG;
real captured preimage bytes and metadata are retained. Prerequisites are
excluded explicitly. It is not a complete 22-member production transaction,
nor a signature, preboot, mount/remount, SELinux, or board admission.

The receipt test reads the persisted bms attempt when run after landing in
master. If that external raw attempt is unavailable, it explicitly skips with
a reason; it never infers candidate PASS from absent artifacts.
The exact original records are indexed with SHA in
`evidence/t5-70b6-artifact-index.json`, including discarded reviewer setup
attempts 1/2. Attempt 3 used a three-control projection without directory
semantics; attempt 4 is the authoritative four-control/directory review.
Nothing in prior attempts or the original 52-file R2 handoff was overwritten.
The first known-answer run exposed a reviewer multi-phase auth comparison
mistake, preserved in its raw stderr; the corrected ten tests pass.
For `new_boot_rollback`, the persisted auth is the rollback ticket; the initial
apply digest is reproducible by restoring its boot field to the plan's boot.

Future revisions require a new immutable commit and a new attempt. Rerun only
the changed fault families, not the accepted R1/T4 suites:

```sh
python3 benchmark/2026-10-12-toutiao-recovery-review/review_t5_70b6.py \
  --commit FULL_NEW_COMMIT --attempt NEW_UNIQUE_ATTEMPT \
  --case positive_cli --case mkdir_first_failure --case partial_send \
  --case null_after_label --case inert_retry
```

All authorization files in this recorder are explicitly synthetic; they are
not usable deployment approval. Plan-2 remains 61b's 20 keys plus the existing
5cd 128-key cross-check, not a new 61b 128-key regression. No board, VM,
remote, build, stop clearing, permissions, user data, signature, or push occurred.
