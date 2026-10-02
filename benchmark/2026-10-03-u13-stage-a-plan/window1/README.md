# U13 Stage A window 1 on the signed effective baseline

The live executor rejected 61b before any transaction or deployment, despite both offline surfaces passing. Its common baseline prerequisites required `libinstalls.z.so=2c9a5294` at both system paths, while the signed 61b identity correctly contains `51e1b525`. The independent 318-assertion hook passed the actual board; the executor refused its conflicting baseline. No assertion was relaxed, installer changed, or rejected deployment retried. 61b completed base recovery smoke and final 318 verification, then unlocked. A board-specific baseline rebind is required before its next U13 window.

The authorized source bundle is `91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28`. The independent armed copy is `2abe4a4917e09d53f47edcfec0ec21b9e131fc72253b8f4aa3d47ff87e8d5aa0`: only rollout metadata changed. Native manifest `85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6` and inputs `c40faa79d197f023dbe47a62ae186d5eb5671f9b8f4a448924098fdd5f02f185` remain unchanged. Both real production surfaces used baseline `190afedd`, N1 55 / N2 104 excepted, zero rejected, and static/RB/T4b/G1/G2/frozen passed.

All three boards locked at 03:22:15. The 35-minute new-key cutoff was honored; no tests were added during restoration. 5ea/5cd applied 40 members, passed activation smoke with 321 assertions / 319 unique paths, and executed the approved shards. Each unconditionally restored U10.1T8 and completed recovery smoke, final 318 assertions / 316 unique paths, and unlock within 45 minutes. 61b changed no member. Final runtime fingerprints: 5ea/5cd `f3b604c94df4`, 61b `d6848fa2c989`; all boot fingerprints `e3806b65a079`.

Formal observations: 5ea 27 (17 unique keys), 5cd 24 (19 unique keys), 61b zero. These are coverage counts, not lit counts. Selftest schema2: selftest_error/badtag/probe_error all zero; unknown observations 6 / 4 / 0 respectively. Unknown and empty cutoff shards are not PASS. All per-shard results were posted immediately without interrupting Stage A. 5ea's two additional longwait keys were unmeasured at cutoff; 5cd never reached its auxiliary section; 61b was rejected before any section. Exact continuation ledger is in `results.json` and public `evidence/production/coverage.json`.

An initial fresh VM replay reused a T4b output directory and was correctly rejected. That attempt remains archived; a new report directory passed unchanged gates. A diagnostic sample used `ps comm` and missed vmgr: its zero RSS is explicitly invalid and never served as final admission. The corrected command-line sampler fails closed if no vmgr process is found. Actual final pre-lock RSS was 2,818,640 KiB with orb 0.107 s, following the documented preventive reopen and bind readback. Post-window RSS was 2,467,200 KiB with orb 0.126 s.

## Evidence and reproduction

- `results.json`: restoration, selftest categories, observation/remaining ledger, and disclosed invalid attempts.
- `arming-receipt.json`: exact two-field metadata delta.
- `evidence/production/`: sanitized copies of actual Mac/VM production receipts, tool readiness, image gates and health readings.
- `evidence/<board>/`: exact record/screenshot copies, selected log excerpts, per-shard selftests, facts verbatim, and recovery identities. Excerpts are explicitly not complete hilog.
- `sheets/*-t20.jpeg` and order files: outer visual readout; no UI verdict asserted here.
- `raw-inventory-index.json`: hashes of 132 full inventory chunks for 98,541 immutable raw files under `$WORKSPACES/westlake-inputs/generations/u13-stageA-window1-20261003`. Full logs, faultlogs, refused attempts and transport outputs remain there; public copies normalize local paths only.

The configuration delegates to the reviewed U12 transaction hooks, master production gates, master `board_run.py --detach`, activation smoke, and master batch runner. Parent hook copies are unchanged; the window wrapper selects only this approved configuration. `test_window_config.py` passed three offline tests; the bound draft suite passed 28. Plans retain executed values for audit, and their original output directories are nonempty: they cannot be reused. Any continuation requires fresh output and outer scheduling; no window 2 was started.

The separate authorized Frequent Habits ability-fallback baseline window is documented in `benchmark/2026-10-03-frequent-habits-ability-capture/`; its observations are not mixed into U13's formal denominator.

The reused hook preserves its historical candidate `state=U12` label in raw identity rows. The actual U13 package manifest, bytes and fingerprint checks are binding; this label does not mean an old U12 bundle was applied. The executor reference fingerprint covers 123 paths, whereas the batch/smoke fingerprint additionally covers the new root mediandk path (124); each report retains its own path set rather than mixing hashes.
