# Explicit window ownership and current BLAST sync JNI

The previous interpretation of the Wikipedia failure was wrong: the two
`firstCreate` events belong to **different sessions**, 297 and 298. At hilog
line 55630, `SC.create 'OH_Surface_297'` already carries **sessionId=298**.
`VRI[DefaultIcon]` then resolves BBQ to session 298 / shim `3974C910` /
OH NativeWindow `32FC86F0` and creates EGLSurface `31CB1810`. Only later does
`VRI[InitialOnboardingActivity]` create its own BBQ and collide with that
same producer. This is explicit evidence of an ownership error before EGL,
not evidence that an owner should forcibly destroy somebody else's surface.
The rule established here is: **SC and BBQ routing must preserve their own
session identity; a global last-created session cannot identify an owner.**

Evidence is extracted from the existing 5ea r17p run
`20260930T052052-c0742d1c`, PID 23726. See
[source-evidence/wikipedia-timeline.txt](source-evidence/wikipedia-timeline.txt)
and [log-evidence.json](log-evidence.json) for original line numbers, paths
and log hashes. No device command was issued in this task.

## Candidate and scope

- Package: `/Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83`.
- Runtime SHA256: `32dfac830320394d0b62781afcde68537d3b5fff372b5170d7a53baa069013b7`.
- Package manifest SHA256: `30f63ef76b14a8ba2c1334940c66f5cc0e98aa4862152b81e6379f35d0b62c12`.
- Rollback runtime: `9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f`.
- Exactly one payload and live target differ from v3c: `/system/android/lib64/liboh_android_runtime.so`.
- Host, provider, ANL, bridge 84695d62, HWUI be59260f, installer and Java are unchanged.
  The paused next-series AudioSystem/ANL changes are not included.

The frozen B91/9e14 build recipe and B87 private input tree are used, not the
newer unrelated graphics changes in the tracked aggregate source. The two
changed translation units and B91 AndroidRuntime.cpp are frozen in `src/`.
The same focused patch is also applied to the tracked runtime sources.
`source-provenance.json` records the existing persistent B87 source/toolchain
archive, actual compiler hash, extra inputs, and hashes of the frozen sources.
`runtime-recipe.sh` and `build.sh` are the full executable build recipe.

## Changes

1. Root SC identity is parsed strictly from the existing WSA name
   `OH_Surface_<positive sessionId>`. A child inherits its explicit parent SC.
   Copy and mirror retain that identity. Invalid/overflowed owner names stay
   unbound instead of borrowing a global session.
2. Surface/BBQ conversion, update and lazy getSurface use only their SC/BBQ
   identity. Changing an owner clears a cached NativeWindow. A SurfaceView
   child allocation failure does not fall back to the main window producer.
   No EGL destroy or refcount behavior is changed.
3. BLAST's complete 13-method registration table and sync implementations
   are copied from the VM Westlake source at commit
   `22b945321929987c86b35cd99f9f2d2f4283e82e` (file clean, SHA `a34b6750...`).
   A byte-preserved source copy is in `source-evidence/westlake-compat-shim.cpp`.
   This is an existing implementation, not a newly invented synchronization
   mechanism; device equivalence still requires the control run.

The four registration errors describe an **API-generation mismatch**. Three
old names (`nativeSetNextTransaction`, `nativeSetSyncTransaction`,
`nativeFlushShadowQueue`) are absent from the actual frozen DEX. The fourth,
`nativeGatherPendingTransactions`, returns a Transaction object, not `long`.
The replacement table supplies `nativeSyncNextTransaction`, stop/clear sync,
and the correct object-returning gather, matching **13/13 actual DEX natives**.
No new methods are added to the Java boot class.

Westlake returns false from syncNextTransaction (no callback armed), creates a
valid empty Transaction for gather, and preserves JNI exceptions on class /
constructor / allocation failure. Returning null on the normal gather path
would violate the caller's object contract. Flush/apply-pending remain the
existing no-op because this OH shim does not collect SF-side transactions.

## What the white-screen evidence proves

| App / child PID | EGL create result logs | RS flush entry logs | finishDrawing entry logs | OH vsync callback logs |
|---|---:|---:|---:|---:|
| AppManager / 27114 | 1 | 1 | 0 | 4 |
| K9 / 30598 | 1 | 1 | 0 | 4 |
| Tusky / 32508 | 1 | 1 | 0 | 27 |

These are counts of matching **existing log lines**, not frame counters or
proof that RS consumed a buffer. In particular, `oh_rs_flush_transaction`
was reached: “apply never executes” is too strong. The missing current JNI
bindings are established; whether repairing them clears the entire
first-frame/foreground chain is **unverified**. `finishDrawing` handling and
transaction committed listeners may remain independent gaps if this candidate
still fails. No screenshot or survival totals are claimed for this task.

## Offline validation

- Two complete builds produce the same runtime SHA.
- Strict link succeeds with undefined-symbol checks; Profile-B edge check passes.
- 22 NEEDED entries and order, SONAME unchanged; no new imports, no removed exports.
- Five offline tests: actual production owner parser, malformed/overflow owners,
  13 DEX signatures and exact Westlake implementation, JNI success/failure paths
  with an explicit fake JNIEnv, and one-file package/SHA/dry-run checks.
- Two negative controls: wrong replacement SHA rejected before copying;
  an unrelated ANL change rejected by replacement validation.
- `dry-run.json`: passed, `device_io=false`; this is package validation only,
  not a board admission or render verdict.
- Agent-spec B12: 5/5 scenario verdicts pass, lint 100%. Scope explicitly ends
  at offline delivery. Repository known-answer results are in `known-answers.txt`.

R2: **verified** source mismatch, identity trace, build, ABI and package;
**unverified** board repair and HW/ZigZag regression.

## Discriminating device experiment (outer schedules a board)

5cd is reserved by cc-t3. Do not deploy there. After 5ea or 61b is released,
the board owner takes its full-key lock, records the active package and Java
receipt, and uses one-file replacement only. Keep the same Java SHA for A/B.
If the resident package differs from v3c (for example newer TLS additions),
rebase this runtime onto that exact active package using `prepare_for_base.py`;
do not activate this package wholesale or discard overlays.

1. Run HW and ZigZag controls first. Require app content at t5/t20, not just
   live processes. Any regression rolls back this one file immediately.
2. Require `android/graphics/BLASTBufferQueue registered 13/13`, no four old
   registration errors, and no new UnsatisfiedLinkError/NPE in sync/gather.
3. Wikipedia: pair SC name/session, BBQ name/session, shim and OH NativeWindow
   by PID. Main and onboarding must map to distinct owners and windows. Require
   successful onboarding EGL creation; no automatic destruction of another
   owner's live surface. If session identity is fixed but BAD_ALLOC persists,
   investigate a same-owner lifecycle separately.
4. AppManager/K9/Tusky: capture t5/t20 and the finishDrawing/RS/foreground chain.
   If JNI registrations are repaired but still white, record as a failed
   rendering hypothesis, not success. The next observation points are HWUI
   frame-completion callback, sync-group ready/apply, and OH buffer consumption.
   Add per-frame markers at those boundaries only after this minimal A/B.
5. Use master bms_batch.py preflight (16M/private off/time/screen),
   `--shots 5,20 --focus-check`; deliver exact facts.txt and screenshots to outer.

Example (only after board assignment, lock/held, and Java overlay retirement):

```sh
scripts/lab/deploy_generation.sh "$SERIAL" "$CANDIDATE" \
  --replace /system/android/lib64/liboh_android_runtime.so --lane "$LANE"
# Restore the recorded Java overlay, validate unchanged Java SHA, then test.
# On failure: retire that overlay again, undo this last native replacement,
# then restore the same Java overlay and verify the baseline.
scripts/lab/deploy_generation.sh "$SERIAL" "$CANDIDATE" \
  --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane "$LANE"
```

The deployer verifies hashes/maps and restarts appspawn-x; no foundation restart
or installer change is part of this experiment.

## Per-board rebases

[Three board packages and exact apply/rollback commands](board-packages/README.md)
are prepared from the current boot-matched ledgers. No board writes; 5ea first,
5cd/61b gated on its acceptance.

## Authorized 5cd follow-up (2026-09-30)

The user subsequently released 5cd and requested immediate deployment before 5ea. [Device evidence](device-5cd/README.md) supersedes the earlier scheduling restriction only: 32df+r17q deployed, BLAST13/13 confirmed, HW/Auxio/Droidify UI retained, AppManager validation frame visible, K9/Tusky/Termux still white. Restoring original ZigZag sidecar mounts after reinstall recovers its menu. 5cd released with graphics resident; 5ea/Wikipedia remains outer-owned.
