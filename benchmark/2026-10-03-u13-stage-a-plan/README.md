# U13 Stage A draft: visual preservation and process crypto health

U12's screenshot-only preservation gate missed a process-wide defect: the R3 Cipher wrapper never initialized its BC delegate on Android libcore. Outer counted `selftest error` in154/174 U12 runs versus0/133 U10.1T8 runs. U12 therefore was not promoted. U13 must pass both the visual gate and per-run process selftests, rather than promoting from t20 images alone.

## Status and restoration

**DESIGN ONLY, DEFAULT DISABLED. No board or lock was used.** Final package/bundle/native-manifest hashes and candidate fingerprints remain null until cx-bms final assembly. `draft_guard.py` refuses all actions even if flags are manually toggled. None of the draft hooks can deploy or restore a board. Real production transaction bindings and fresh Mac+VM full artifact gates must replace the guarded slots before outer authorization. Unit tests passing is not a production package dry-run.

Visual reference: master29b525e181 `benchmark/2026-10-03-u13-reference`,122 outer-signed bright keys (40/39/43), built from116 prior keys,5 signed U12 gains and itsdicey re-sign. Reference sources hash is pinned in each plan. This is a signing reference, **not the deployed restoration state**. Restoration is unchanged U10.1T8, bundle190afedd / native4db32703,318 assertions, runtime5ea/5cd=f3b604c94df4 /61b=d6848fa2c989,boot=e3806b65a079. Per-board frozen installation-chain differences stay unchanged.

## Main windows and keys

`plan-{5ea,5cd,61b}.json` follows the reviewed U12 Stage A shape:45-minute cap,35-minute new-key cutoff, detached runner, fresh output, same final package bytes across continuations, unconditional finish U10.1T8 +318 + recovery HW/ZZ smoke + final readback before unlock. Failed recovery retains the lock. Pre-lock requirements include vmgr RSS and orb latency (RSS>3GiB: RUNBOOK preventive restart before LOCK), HDC whitelist, bind SHA, VM tools and actual final package gates on Mac+VM.

The corpus retains all166 unique keys on their existing55/55/56 boards. The older observation-key input supplies movers/cv2-new priority and four lottery blocks, not its stale116-lit denominator. Keys already in a movers group are not duplicated in the ordinary lit group; their run still counts toward the122-key preservation obligation. Each lottery key gets six consecutive same-board single-key shards, with multiwin misroute readout. Other registered flaky keys use same-board k/n: one white cannot confirm regression; authorized repeated samples and outer t20 judgment are required. Missing/cutoff observations are unknown.

Main run counts are65/60/61=186:166 unique corpus observations plus20 lottery repeats. Ordinary screenshots remain5/20. Outer pair_sheet uses the new U13 reference, its sources/signoff chain and same-board screenshots. Alive, foreground-unconfirmed, READY or PASS alone is not a visual verdict.

## Six auxiliary long waits (outer01:59 steering)

Replaces the earlier three-board Toutiao repetition: `longwait-{board}.json` contains six keys, one clean observation each, two per board.5ea:frequent-habits/vector;5cd:plus/libretube;61b:mcdonalds/toutiao. Only these auxiliary observations move plus/libretube to5cd; their normal regression assignments remain unchanged. Each uses its correct original/cv2 manifest and input root with `--reinstall --wait95 --hilog95 --shots20,45,90`. Each auxiliary board window is capped30min/20min cutoff. Total proposed main+auxiliary observations=192.

These observations are excluded from the t20 regression numerator/denominator and supply only first-fatal/phase evidence. Their process crypto selftests are still counted. `maps-t20` alone is approved; no collector change. `board_run` currently hardcodes5/20, so arbitrary shard timing JSON is not executable support. Auxiliary windows must use the existing master batch command via a reviewed detached wrapper, and final apply/finish bindings; the draft refuses execution.

Toutiao's new gain prediction remains0/unknown: the baseline package contains libicui18n.so, but westlake.anl.app cannot see it. Two61b longwait runs already reached bind then ICUWrapper+100 pc0 crash. Do not mistake absent namespace visibility for an absent file or predict JIT will solve this native wall. Frequent-habits may still fail icon lookup; such a run is unknown, not an invented native first fatal.

## Process selftest gate and promotion criteria

`process_selftest.py` inventories **every record**, complete hilog, target BMS UID/PID and each process's exact `[WL-KS-PROBE] selftest error` lines and `validateAead(...)=OK` lines. It recognizes the actual success form `validateAead(random 256-bit SecretKeySpec)=OK`. The older expected `selftest AEADBadTagException` diagnostic is not falsely counted as a `selftest error`; it also is not a successful validation. Unseen PID, missing/incomplete log or absent success is unknown, not zero-error success.

Default gate: every measured bridged process has explicit validation OK and zero selftest errors. Errors and unknowns must be individually explained by outer, each exact record/PID/line number/hash (or explicit unknown), exact report/package binding and an existing evidence file with its hash. No exception is approved or written by this draft. A counter-only or blanket explanation is rejected. Crypto report SHA and the measured-record set must be bound by the outer Stage A decision.

`promotion_hook_u13.py` derives the U12 `retention_reason` safeguards: activation smoke, exact final bundle/manifest and outer signer, all signed-reference-lit keys measured and same_or_lit under k/n, zero confirmed regression. It changes the visual reference field to `u13_reference_lit_total`122 and adds the crypto report gate. This file is a criteria blueprint only; it has no apply/finish/device code. Final promotion must also retain the U12 production hook's identity/fingerprint gates, fresh same-board/window HW/ZZ outer signature and unconditional restoration on failure. There is no Toutiao bright-screen promotion condition.

Important wiring gap is explicit: current board_run has no post-shard crypto hook. Before enabling, wire a reviewed runner wrapper to evaluate each finished shard's records, stop on unreviewed selftest error/unknown, and always run finish regardless of the crypto verdict. The gate is not silently delegated to an ignored JSON field. Full Stage A output (including smoke and auxiliary runs) must be aggregated for promotion; outer binds all measured records so a healthy subset cannot replace the complete set.

## Offline validation

Mac and actual a2hlab VM:17 tests passed. Tests cover real marker syntax, U12's captured negative line, correct PID scope, expected old BadTag wording, missing data, disabled plans, fail-closed hooks,166-key coverage, six consecutive lottery trials, six balanced longwait observations, wrong bundle,116-vs122 denominator and crypto failure despite preserved screenshots. No final candidate exists, so artifact_identity/native/frozen/image/production dry-run verdicts are pending, not PASS.
