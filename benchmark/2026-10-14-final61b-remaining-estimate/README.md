### Estimate: #91 remaining V2 critical path

#### Contract Summary

- **Scenarios**:9 across original t4-stability(5) andt5-seal(4):7 happy/integration and2 exception scenarios.
- **Decisions**:17 local fixed decisions plus6 inherited project decisions. Existing user authorizations remain applicable;no standard or spec was changed.
- **Boundaries**:6 distinct allowed path patterns/files,2 out-of-scope bullets.
- **Inherited constraints**:8. This estimates remaining work only;completed historic branches are not scheduled again.
- Both original `agent-spec contract` commands returned0;rendered contracts are retained beside this report.

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
|1|Remaining W03-W08 full128 execution|t4 list/group/game/reboot gates|6 hardware cycles|1.1–1.2|6–7|92 keys;unchanged original three identity passes and smoke per window;120–145min estimated|
|2|Final raw collector824+130|t5 fingerprint|1|1.0–1.2|1–2|3–7min estimated after current board run|
|3|Original consume/compile/verify and newproof live954|t5 exact realization/drift|1|1.0–1.2|1–2|4–11min estimated;actual fresh raw checks still required|
|4|Image review,final admission/runbook/signoff and archive|t4 human review;t5 runbook/restore provenance|overlapping review|1.2|1–2|15–35min work can largely overlap remainingwindows;final dependency tail remains|

#### Summary

- **Base rounds**:8 heterogeneous evidence cycles,not8 coding iterations.
- **Integration**:+1 cycle;**Verification**:+1 review cycle,overlapping where evidence permits.
- **Risk-adjusted total**:10–12 effective cycles. Do not multiply by the default3min:hardware timings dominate.
- **Estimated wallclock**:135–180 minutes remaining from01:35,conditional completion window03:50–04:35 CST. Original regression accounts for120–145min;parallel preparation/review leaves approximately15–30min additional critical tail. No lowfork saving is applied this round.

Observed calibration:W01 consumed26.33min from pre-lock output-directory creation to after-identity completion. W02:22.34 min observed. Its18 captured-record keys are complete. W01 per-key mean52.29s/median57.48s;W02 mean40.15s/median37.04s. Complete identity passes measured152.47–173.30s each;both smoke gates are approximately121.8s. Every future window incurs three full identity passes and a smoke gate,including the final two-key window. Run-directory timestamps and record mtimes measure transport/desktop/snapshot overhead as well as app execution;they are not pure app runtime.36 records does not mean36 accepted apps.

#### Risk Factors

1. Onlytwo18-key windows calibrate later heterogeneous apps;the range is a planning range,not a statistical confidence interval.
2. Identity/boot/transport/lock failure,cutoff or missing keys stops the original driver;no safe cross-generation resume is available.
3. Image regressions or unresolved admission scope can block signing. A completed pending-review record is neither a visual PASS nor automatically an app failure.
4. A changed run.sh/WID before final capture can trigger the frozen824SHA gate and require a fresh independentlybound input path. No duration for new repair/rebinding is assumed.
5. The forecast assumes current scoped Boat/feed and restoration evidence remains admissible;it does not declare V2 accepted or weaken any gate.

#### Confidence

MEDIUM for an uninterrupted evidence-producing run;LOW for an unconditional promise of signed completion because actual acceptance is still pending. No HDC call,experiment,execution pause,spec edit,active-pin change or signing was performed.

#### Dependency Analysis

Critical path:remaining same61b windows → final raw capture → real admissions/consume → original compile/verify → actual newproof live954 → final signoff/archive closeout. Screenshot review,existingreceipt hashing,runbook drafting and archive staging can progress inparallel without borrowing anotherboard's acceptance. See observed-timings.json for36per-key rows and results.json for the frozen-plan/time snapshot.
