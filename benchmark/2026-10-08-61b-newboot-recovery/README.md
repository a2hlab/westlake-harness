# 61b recovered and unlocked after approved placeholder cleanup

**Final outcome:** [continuation/results.json](continuation/results.json) records `restored-verified-unlocked`. On outer approval at 21:55:26, the only allowed path passed additions ownership, no-mount, and EMPTY-hash readback, then the unchanged `remove_placeholder` primitive removed it. The original restored smoke passed with runtime `452447a4a0ba` / boot `ee927db88a67`; final 321/319 identity has `diff={}`, `absent=[]`, and fresh parent/child views with single ART. UNLOCK succeeded and held returned rc=1 with empty stdout/stderr. Original journal unchanged. No other board was accessed.

Final verbatim [facts](continuation/facts.txt), [smoke stdout](continuation/smoke.stdout.txt), [final identity](continuation/final-identity.json), [guards](continuation/placeholder-guards.json), [absence readback](continuation/placeholder-removed.json), [HelloWorld t20](continuation/helloworld-t20.jpeg) and [ZigZag t20](continuation/zigzag-t20.jpeg). Screenshot signoff remains with outer. The first continuation stopped before deletion because the VM lacked EXPECTED_BOOT; only explicit environment forwarding was corrected, with fresh output and no guard relaxation.

The separate offline executor fix is in `benchmark/2026-10-08-u7-replay-placeholder-cleanup/` (Mac/VM 30 tests each). It was not installed during this window.

## Initial refusal retained as evidence

Evidence first: [restored identity](evidence/restored-identity.json) is U13, 321 assertions / 319 paths, `diff={}`, `absent=[]`, runtime `452447a4a0ba`, boot `ee927db88a67`. The unchanged original executor returned `baseline_restored`; 56 recorded mount layers were replayed under the new `cx-t0` holder. [Original smoke output](evidence/smoke.stdout.txt) returned **rc=1**. The only rejected check is runtime fingerprint: expected `452447a4a0ba`, observed `204ab50509d1`.

The old October 3 holder was gone and the board had a new boot. Treating a historical LOCK line as a live holder would prevent recovery; rewriting the old journal boot would corrupt transaction ownership. Outer authorized a two-minute announcement, new holder, and the original `--restore-baseline --from-journal` primitive with a fresh replay journal. No executor, original hook, smoke specification, or frozen artifact was changed.

## Captured scope difference, without further device commands

[Offline diff](fingerprint-scope-diff.json) compares the captured smoke fingerprint with the signed recovery reference. All 124 signed paths match. Missing paths: 0; changed signed paths: 0. The smoke glob includes one additional path, `/system/android/lib64/libicu74compat.so`, with SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty content). The 125-path hash is `204ab50509d1`; restricting the capture to the original 124 paths recomputes `452447a4a0ba`. This does not authorize deleting that path or amending the smoke verdict. Its creation provenance was not investigated in this window.

## Safety disposition

The runner stopped immediately after the smoke refusal. Final identity verification and UNLOCK were not executed. [Held query](evidence/held-query.json) confirms `cx-t0 22036 2026-10-08T21:40:24+0800`. The original double-transaction journal remains SHA256 `f24718730ccd4165d876a411daf0d717630311de0ac2a1c5b1c20923c8ebde67`, unchanged. Only 61b received device commands; 5ea/5cd received none. No reboot, installer swap, source rebuild, or gate relaxation occurred.

The smoke passed control survival at t20, GCM marker, ART/JVM single-copy checks, the signed bridge/runtime two-copy expectations, and every child-view SHA. Those are engineering observations, not a screenshot signoff. [HelloWorld t20](evidence/helloworld-t20.jpeg) and [ZigZag t20](evidence/zigzag-t20.jpeg) await outer visual review. [facts.txt](facts.txt) is the verbatim `run_facts.py` output for the exact controls run, excluding the separate probe record. No point-lighting count is claimed.

## Evidence and reproduction inputs

[results.json](results.json) records the raw attempt path, persistent archive path/hash, failure and remaining lock. Original stdout/stderr, per-command receipts, replay journal, hashes, maps, records and screenshots are retained in the archive under `$WORKSPACES/westlake-inputs/reports/2026-10-08-61b-newboot-recovery/`. Small JSON/text copies here replace only the recording workspace prefix with `$WORKSPACES`; original raw bytes remain in that archive. `recover.py` is a one-window recorder using the unchanged approved primitives and an exact new-holder/boot assertion; it is not a generalized recovery fallback.

Required next decision: outer must review the added empty path versus the signed smoke scope before any retry or unlock. Until then, keep the lock and board state unchanged.
