# T37 revised candidate and production assembly review

The original r4 evidence accepted unknown exit/enumeration data as absence. T37 reproduced those failures independently. Revision r4b repaired the original 16 cases, but malformed UID fields and an unrecorded run inode still allowed unsafe transitions. Revision r4c now passes **18/18 safety assertions**, including the successful transition and repeated-click controls, with **0 harness errors**. No old rejected SHA was replayed in this continuation; historical receipts are verified without executing them.

## Exact final review object

- Watchdog: `c73dadb3c0d6ba082c030d7c1096810129b5afec7e3aced4d896dce86e59f0e5`.
- Reentry common: `b806eb6c1bb390be357f2ac689024bf3947217611bf637850cfc65e7538681c9`.
- Package manifest: `14cb20ef1fc6d0781245e369c2d1aeadfe58d3cea6e1442f101ef3e1c499d864`.
- Entry: `583df035cccbc8750b79bbe15266e311d07780f3fa2f4401f21c224f716b7647`.
- Source capture/replay: `r4c-c73dadb3-01/`; complete package pin audit and preserved text files: `assembly-r4c-02/`.
- Review bound to exact bytes. At initial capture, r4c was an uncommitted revision on author base `a06156a958`; a later commit name does not replace these byte identities.

The final author commit is `fa2b91117fd49ec0119986b6c3174d0857d10229`; `author-observation-final.json` compares the reviewed working bytes to committed blobs.

## Independent replay findings

Real production functions execute with synthetic process/OS/start/signal seams. The fixture invokes production `rc_record_bootstrap_epoch`, `rc_epoch_binding`, `rc_wait_exit`, loop and launch functions. Positive controls exercise one TERM, one parent start, one child spawn and current-shell identity persistence. Repeated edges while the new child lives cause no second epoch/spawn. Live child, foreign holder, failed enumeration, PID reuse, unknown exit, malformed stat, missing proc/fd views, failed readlink, non-listener rows and partial start/stop failure refuse or hold as required.

The two r4b failures are preserved at `r4b-3aba9d8e-03/replay/malformed_owned_uid.receipt.json` and `recorded_run_inode_changed.receipt.json`. The first uses actual `rb_uid` and `rc_owned_pids_strict`; the second restores actual `parent_owned`, records the old epoch, then changes matching physical/private run inode observations. r4c validates four numeric UID fields and compares recorded runid, removing both failures without disabling the positive path.

The tests cover synthetic boundaries, not actual kernel atomicity or device behavior. Signal execution, OS ownership observations and starts are doubles; no real process was signalled. Native runtime behavior, the actual device namespace/proc visibility and manual visual acceptance remain outside T37.

The author records an unresolved legacy-suite result on r4b (53 passed / 18 failed), attributed to an incomplete `/proc` fixture, and did not rerun author suites on r4c. T37 does not certify that full regression suite or adopt that diagnosis as independently proven. The 18-case result above is the bounded independent safety review.

## Full production assembly

The author supplied `candidate-package-r4c/payload`. All **22 members** were hashed independently; **165 pin checks passed**. Five actually replayed files (watchdog, common, ownership, exit-verdict and WMS parser) match the package byte-for-byte. Inputs remained unchanged through the audit.

`boot-entry -> entry -> watchdog -> start-parent -> bounded real parent start -> reentry loop -> spawn -> real-spawn` is statically connected. Entry now pins the exact reviewed watchdog. The member table, startup member/bounded-start/decoder/probe hashes, startup.expected and package MANIFEST agree. The original r3 screen-gate and synthetic decoder JPEG were available in this package and matched their original manifest hashes; they were hashed, not executed or copied into the peer evidence.

This carrier deliberately has `STARTUP_ENABLED=0`, `STARTUP_APPROVED_BY=UNAPPROVED-T36-candidate`. Config and init path still reference `icon-manual-20261021-r3`. **Do not interpret pin consistency as a deployable fresh-root authority.** Outer must derive the actual new ROOT/init/approval package, recompute all affected pins, rerun this audit and preserve the old signed recovery. No authority file was enabled or changed by T37. The unchanged `start-parent.sh` refuses a preexisting socket before start; the new recorded epoch is created only on the guardian's own bootstrap-parent path, while the adoption path does not gain signal authority.

## Runner and handoff

`candidate_review.py --candidate ... --payload ... --expect-watchdog-sha ... --out ...` selects exact SHA, captures immutable sources and checks stability. Known watchdogs exit3 without rerunning; `--assembly-only` allows review of a completed package for an already reviewed source. Missing functions/fixture errors are `harness_error`, not safe refusal. Safety and assembly verdicts are separate; every report keeps deployment acceptance false.

The first extractor and one enumeration oracle needed fixes; their failed receipts remain in r4b runs 01/02. Run03 and the r4c run use the corrected versions. `RUNNER.md` records those corrections.

Messaging stopped after the two permission denials, as instructed. Outer relays the reports and lands the exact listing. No author files, device state, historical signoff or frozen source were changed. No commit retry or push occurred. Screenshot/alive counts are unknown because this lane had no device run. The manual two-cycle dynamic-frame/pause/resume/exit matrix stays pending; historical audio acceptance is retained without asking again.
