# Expert briefing: adversarial fact check

Evidence first: the final U9 signoff contains **115/166**, not the draft's114; U3's J3 sweep contains **25/66**, while27 is cumulative ever-lit. The named Git snapshot contains **379 tracked benchmark directories**, not384. The same snapshot's final correction already says U14 Realm has passed `_ctype_`, so an unconditional “sysconf moves0” forecast is stale. Two of the three demonstration commands contain shell placeholders; their concrete replacements can be replayed successfully on retained evidence.

The original briefing was **not edited by this reviewer**. The input changed externally during review from360 to353 lines (the sysconf text and diagram were revised). This report binds the initial SHA and retains exact reviewed sentences in `evidence/reviewed-source-lines.json`; it is not a full draft copy. `current_draft_line` maps unchanged sentences to the latest captured revision. Removed/reworded sentences should be checked against that revision before applying corrections. No board, HDC, lock, VM or remote-server command was executed. Only local Git/document reads and three read-only historical-data replays were used. The task's30-minute slice constrains primary-source re-derivation: `confirmed` means the claim has documentary support, **not** a fresh hardware or causal experiment.

## Scope and outcome

- Draft: `$WORKSPACES/westlake-inputs/reports/2026-10-08-harness-briefing/briefing.zh.md`, SHA256 `dc39bce4983a8e0d0699273c34e0b52d025225cca6fb497cead4854617b60a5d`.
- Statistical snapshot: `aa948b8c9a857ef9a674b138f772056b3a2594aa` (2026-10-03).
- Master at review start: `a068a5c90348bbded0023ddb3ef80be67c3e969e`; later inventory reports are cited explicitly, not included silently in snapshot totals.
- **185 assertion records on 182 substantive draft lines**: 122 confirmed, 11 wrong, 45 misleading, 7 unverifiable.
- Each finding carries the **exact draft sentence and line**, a separately scoped claim, a verdict, `path:line` evidence and an editorial correction. Mixed-statistics rows have more than one finding.
- Titles, decorative diagram connectors and delivery recommendations are not empirical claims. Eight numbered principles, ten displayed tool categories, all58 tool-name occurrences, numeric tables, incidents, growth curve and demonstration assertions were covered.

`findings.json` is the authoritative row-level deliverable; `results.json` records scope and validation. `unverifiable` means an exact citation/definition/replay is missing in this slice, not that the statement is necessarily false. Earlier board counts are not labeled wrong merely because later messages were appended.

## Corrections to make before presenting

| Draft lines | Issue | Evidence / correction |
|---|---|---|
|18,251,354|384 directories conflates tracked snapshot and local checkout.|`evidence/statistics.json`:379 at snapshot; current checkout386, including untracked data.|
|20|“The same mistake never happens twice” contradicts the campaign.|FLAW008 recurrence8; FLAW001 recurrence7; wrong-glob regression repeated. Say failures become recorded and bounded.|
|51,299|“115 lit keys also have two copies” hides different libraries.|Double-copy table:115 have bridge2;85 have runtime2 and30 have runtime1. Copy count does not discriminate this white cluster.|
|57,292|sysconf single-fix forecast uses the superseded Realm wall.|DIGEST791 / snapshot commit message: effective U14 native ABI already exports `_ctype_`; latest plan puts sysconf+4 behind user-approved frozen-order evolution.|
|60|30-minute full166-key sweep / identical fingerprints overclaims reality.|Actual campaigns use several45/35 windows;61b installation-chain exceptions are explicit.|
|62|U10.1 non-promotion decision lacks later outcome.|Initially not promoted alone; later U10.1+T8+U11i promoted by user decision.|
|95,180,359|86 Rust tests is a file/function ambiguity.|86 integration source files,87 scoped Rust files,310 `#[test]` declarations.|
|121|114 no-header roles were all “manually read”.|17 manually curated operational entries;97 test/body-declaration fallbacks.|
|175,176,358|Blackboard totals use inconsistent grammars.|R2 literal mention lines120, quoted record lines104; generic redecision27, narrow 作废15.353/355 cannot establish pairing.|
|247,248|Incorrect document starting line counts.|First tracked DIGEST Sep26/58; first RUNBOOK Sep28/62.331/84 need a different dated commit if retained.|
|254,255|Tool causal history merges distinct incidents.|Signature drift motivated ABI checks; same-signature constructor call-graph drift motivated `--calls`. `--detach` is a later timeout fix.|
|262–266|Signed sample, cumulative count and preliminary count mixed.|U2 sample24;U3 sample25/cumulative27;U7 formal34;U8 initial99/later100;U9 final115;U10.1T8 signed116 plus a separate lottery.|
|305–322|Two advertised “verbatim” demo commands are placeholders.|Provide actual paths, environment setup and persistent data; all three concrete replays returned0.|

## Three demonstration replays

1. **Facts:** the printed directory exists locally. With `WORKSPACES` resolved explicitly, master `run_facts.py` returned0 and exactly reproduced runtime32c76e6fac13, FROZEN4/0, screenshots2/2 and t20 alive1. Without that environment variable, the literal invocation failed at a `/westlake-harness…` path. See `evidence/demo1.txt`.
2. **Variables:** explicitly select the **runner/organicmaps/trial-1/batch** directories under window6's5cd `control-r2` and `candidate`; master `compare_runs.py` returned0, `variables: 7`, and the quoted hypothesis verdict. See `evidence/demo2-instantiated.txt`, which supplies both full portable paths. The original angle-bracket placeholders remain non-executable. Recovery-smoke directories under the same roots are a different experiment and must not be substituted.
3. **Freeze:** supplying the facts replay's concrete fingerprint to master `check_frozen.py --git --fingerprint` returned0: `frozen: 8 entries, 34 checked, 0 violation(s)`. See `evidence/demo3-instantiated.txt`. This establishes that concrete input, not an invariant count for any arbitrary fingerprint.

A fresh public clone alone lacks the historical run directory and external octoscode installation. Ship a small signed offline evidence bundle plus a setup/preflight script before promising a three-minute live demonstration.

## Five questions terminal experts are most likely to ask

1. **What does “129 apps work” mean?** Answer129 signed APK builds/keys,128 package names; startup UI at agreed capture time, including splash/empty-list/error-dialog states. It does not establish login, TLS, camera, audio, persistence, background lifecycle or complete app behavior. Separate candidate gains from the promoted126 baseline.
2. **Is the growth curve comparable?** It mixes a66-key corpus and166-key corpus, single-run samples, cumulative ever-lit and k/n acceptance. Publish denominators, snapshot dates, flaky confidence and signed endpoint revisions rather than one unqualified monotone curve.
3. **Why should double-load fix white screens if lit apps also double-load?** The evidence invalidates copy count as a discriminator for the observed white cluster. It does not disprove cached-field/JNI cross-owner bugs in the seven terminating AssetManager apps. Distinguish correlation, mechanism and tested fix scope.
4. **Do passing gates prove compatibility?** Gates have explicit exceptions, unresolved sites, declared probes and outer judgment. U12 demonstrated an AES/GCM regression invisible in startup screenshots. State exactly what each gate checks and what it cannot cover.
5. **Can an independent machine reproduce this?**259 files includes122 tests/adapters, not259 standalone tools; external retained runs/toolchains/raw logs are needed.86 Rust modules is not86 tests, and not every deployed bridge/HWUI build has a reproducible source chain.

## Missing stories and numbers worth adding

- **The U12 crypto counterexample:**154/174 process selftests failed while startup screenshots appeared non-regressing. Promotion was stopped. U13 added three-class checks; its219 candidate records were180PASS,39 explained unknown,0selftest_error/0badtag/0probe_error. This is stronger evidence for trustworthy evolution than “mistakes never recur” (DIGEST93; U13 outer-stage-A certificate).
- **Real-data fixtures defeated green synthetic tests:** board_run used a two-level glob/fixture for a three-level run layout. Replaying real directories exposed the error; subsequent rc1 foreground-unconfirmed handling was independently corrected. Explain why known-answer tests must use production objects (DIGEST645–648; RUNBOOK202).
- **Evidence loss is a distinct reliability failure:** a worktree `git clean` destroyed U8 hilog/maps/facts; ignored screenshots survived. Read-only output retention and files_gone index preservation followed (DIGEST566). This exposes limits of “every point has reproducible raw evidence”.
- **The measurement model:**129 APK hashes but128 packages;259 maintenance files but137 operational/helpers;115 U9 final not114;116 U10.1T8 signed plus separate lottery. Add the per-state denominator and uncertainty instead of a single “lit” scalar.
- **What remains outside the demo:** no full-functional acceptance, known board installation-chain differences,39 explained probe unknowns, retained external artifacts, and human screenshot signoff. Show one screenshot alongside its facts, selftest and first-fatal evidence.

## Validation and handoff

The auditor checks draft SHA/line preservation, unique finding IDs, evidence-line existence, scoped tool-name presence, category/statistical known answers, and captured replay exits. The reviewer did not mutate master code, the original briefing, devices or original run data. Local commit only; outer receives `landing-paths.txt` and runs `land.py --preflight` before landing.
