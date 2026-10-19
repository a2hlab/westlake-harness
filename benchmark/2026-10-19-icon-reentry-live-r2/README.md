# Manual icon recovery: independently reviewed live evidence

The previous controlled-exit failure was an ownership refusal, not proof of a natural crash or a successful recovery. This package separates real feed images, identity/event records, a controlled SIGTERM, and the incomplete cold-start prefix. It then includes the later cross-boot feed supplement without rewriting the earlier failure/awaiting evidence.

**Token:** `icon-1919-evidence-partial`. **Verdict:** scoped recovery evidence accepted, including independently verified final guardian originals for both boots. The earlier missing r4 identity/event receipt is now closed. No unrestricted P0 signoff or zero-failure cold-start claim is issued.

## Observed scope

| Observation | Identity and evidence | Independent visual result |
|---|---|---|
| r3 natural-exit/manual reentry, seq4 | Boot `e3615aea-7396-4e8b-8175-95e6e0fde9d1`; parent `4614/4192`; child `27974/40329`; [events](evidence/events-r3.txt) | [Actual feed](seq4/screen.jpeg), SHA `8a928551cba9f7b10fb49ac81bd4ac310a0246ac6d46fb2323ee94ea23e1d11e` |
| r3 controlled exit and manual reopen, seq5 | Identity-guarded SIGTERM to child27974, not a natural crash; parent remains in after-TERM ps. Final event/instance/parent-identity originals record child `4517/55587`, same parent. | [Actual feed](seq5/screen.jpeg), SHA `d3225328502d532f4028425965ba6a64a23e6ff2dc948cb7d14b52244ba70d1d` |
| r4 completed cold-start prefix | Boot `7bf09d80-2526-4ee3-9305-4a234f960836`; new parent `4850/6152`; first child `6834/7768` exits and guardian enters AWAITING_REENTRY. Child absent, parent present in sampled ps. | [IMEhost only](second-boot-awaiting/screen.jpeg), not feed |
| r4 later manual recovery, after connectivity reconnect | Same boot in original capture record and [final guardian originals](evidence/final-guardian-r4/instance.txt): seq2 child `13713/17320`, parent `4850/6152`; [event197 READY](evidence/final-guardian-r4/events.log). Each received file has its original successful transfer receipt. | [Actual feed](second-boot-feed/screen.jpeg), SHA `275824685f9dd28438d7608a1655c313c4bf75861c189e6c5050e174515c9222` |

All four images were opened for independent review and copied byte-for-byte. The three feed views show the recommendation tab, text/image cards and navigation; they do not demonstrate video playback. Screenshot records preserve their original `pending_review` values; the independent judgments are in [results.json](results.json). No source receipt was overwritten.

Accepted scope is natural/controlled exit followed by manual reentry reaching feed, plus cross-boot persistence followed by eventual manual recovery. Random exits remain unfixed. Initial connectivity dependence remains an outer-reported limitation. Final event timestamps independently show 23 seconds from seq2 spawn (174) to READY (197), consistent with the approximately 24-second report; this is not a tap-to-first-frame latency guarantee. Earlier r3 seq1/2/3 did not establish feed. Reconnecting the same network before the r4 feed is not erased or attributed solely to the guardian change.

At 15 seconds after the controlled TERM, the state header was still READY while the event and ps showed the child exited. This package does not fabricate an immediate AWAITING receipt. The seq5 screenshot and subsequent READY event are separate observations. Birth values come from guardian records and the pre-TERM stat, not inferred from PID equality.

## Source, generation and placement

[Source/build pins](source-build-pins.json) bind reviewed source commit `59bee0b7239958b584e519a36d8c000962ee1e41`, the generator/base locks, original generation log, and all 20 actual plan payload files. This is shell-payload derivation, not a native/runtime rebuild. The outer explicitly armed startup files; their SHA differs from the disabled template and is recorded by [generation](evidence/armed-generation.json) and [plan](evidence/placed-plan.json).

The actual placement has cfg `91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e`, [transaction](evidence/placement-transaction.json), [result](evidence/placement-result.json), and [explicit remote rc0](evidence/cfg-remote-rc.txt). Both boot preflight snapshots bind that same cfg. No new build or old test suite was run for this evidence review.

Applicable existing contracts: `specs/toutiao-icon-reentry/project.spec.md`, `t1-reentry.spec.md` and `specs/toutiao-icon-deploy/t1-cfg.spec.md`, pinned in source-build-pins. Runtime/JAR/APK changes and random-crash diagnosis are outside this review.

## Preservation and counting

[Private-source manifest](private-source-manifest.json) records original file hashes and portable locations under `$HOME/.local/share/westlake/toutiao-resume-20261019`. Full child stderr, command triplets and network-related raw files remain private. Public process excerpts retain only the relevant PID rows; public records substitute `$HOME` or a relative screenshot path. Screenshots are unmodified.

[facts.txt](facts.txt) is the actual output of existing `scripts/lab/run_facts.py` over these selected screenshot records. Its t5/t20 liveness is unknown because this is not a timed batch-run layout; do not reinterpret its zero known-alive total as dead processes. Guardian identity/ps observations are separately bound. This package does not claim a full runtime fingerprint check.

The video executor reviews are separate: [initial blocker](video-script-review.json) is preserved; [rollback delta](video-rollback-delta-review.json) accepts the corrected rollback only for the recorded complete-apply state. No video/device command was executed by this reviewer.

## Final guardian supplement

The exact originals in [r3](evidence/final-guardian-r3/events.log) and [r4](evidence/final-guardian-r4/events.log) bind events, instance, state, sequence and parent identity. All ten original `FileTransfer finish` receipts report one file and byte counts equal to the preserved files. This is evidence of successful file reception, not an invented process exit-code receipt. [checks.json](checks.json) records all object and receipt hashes. This closes the prior raw identity/event gap; the original awaiting image and other limitations remain unchanged. No device operation or git staging retry was performed for this supplement.
