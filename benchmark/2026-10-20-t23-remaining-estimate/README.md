# Remaining Toutiao playback acceptance estimate

The earlier 45–75 minute figure cannot be a repair or successful-seal deadline: the outer reports real feed and user-confirmed audio, but cycle 01 has four identical pictures over 20 seconds and cycle 02 advances its progress bar while the video is black. These observations come from the outer handoff; this estimate does not independently certify those pictures. Moving controls do not prove moving video content.

This report uses the installed agent-spec-estimate v1.3.1 and tool-first workflow. Main contracts and `contract`/`explain --history` were read only. No device calls, new window, tests, builds or main-tree edits were performed. Source and CLI hashes are in `source-index.json`.

### Estimate: T23 EGL import — remaining acceptance only

#### Contract Summary
- **Scenarios**: 5 (3 happy/delivery + 2 exception; 1 human).
- **Decisions**: 5 local fixed choices, plus 3 inherited choices.
- **Boundaries**: 3 allowed paths, 1 composite forbidden bullet (6 atomic prohibitions).
- **Inherited constraints**: 6; 2 additional local constraints.

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | Existing host/build closure | S1–S4 | 0 remaining | 1.0 | 0 | Actual source/build/peer receipts already exist; do not rebuild merely because main has no run history. |
| 2 | Bind actual window evidence and human verdict | S5 | 2–3 | 1.2 | 2.4–3.6 | Review bindings/import results against real content and confirmed audio; a failed verdict is valid delivery. |

#### Summary
- **Base rounds**: 2–3 remaining.
- **Integration**: +1 rounded round (10–15% allowance).
- **Verification**: +1 round for the one remaining human scenario; full original five-scenario allowance is not charged again.
- **Risk-adjusted total**: 5–6 rounded rounds.
- **Estimated wallclock**: 15–24 minutes at 3–4 minutes/round. This review overlaps the T3 review below and must not be added twice.

#### Risk Factors
1. Current black content does not satisfy S5; static acceptance is distinct from playback acceptance.
2. Runtime provider bindings and actual content ROI must refer to the same window.

#### Confidence
- MEDIUM for reviewing and recording the current outcome; LOW for any successful-video ETA.

### Estimate: T3 playback seal — current-window closure without new code

#### Contract Summary
- **Scenarios**: 9 (3 happy/delivery + 6 exception/safety; all 9 human). S9 is classified as diagnostic delivery with a rejection branch.
- **Decisions**: 11 local fixed choices, plus 3 inherited choices.
- **Boundaries**: 8 allowed paths, 1 composite forbidden bullet (6 atomic prohibitions).
- **Inherited constraints**: 6.

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | Audit actual cycles, frame/audio attribution and final verdict | S1–S3 | 2–3 | 1.2 | 2.4–3.6 | Includes T23 S5 review. Black/frozen frames yield NOT_PASSED, not a forced extra window. |
| 2 | Outer restoration receipts, identity/feed and release audit | S6, S8 | 2–3 | 1.2 | 2.4–3.6 | Remaining physical work belongs to outer; this estimate opens no window. Credit already completed restoration when evidence arrives. |
| 3 | API/source/build/evidence delta, archive and delivery review | S4 | 2–3 | 1.0 | 2–3 | Existing source/production closure reused; add actual outcome without rewriting history. |
| 4 | Existing admission and diagnostic guards | S5, S7, S9 | 0 extra | 1.0 | 0 | Audit existing receipts inside modules 1–2; do not rerun old R8 operations. Drift invalidates the no-new-code assumption. |

#### Summary
- **Base rounds**: 6–9 remaining.
- **Integration**: +1–2 rounded rounds (10–15% allowance, rounded up).
- **Verification**: +2 rounds for six remaining active acceptance/safety scenarios; completed gates are not recharged.
- **Risk-adjusted total**: 10–15 rounded rounds.
- **Estimated wallclock**: 40–60 minutes at a mixed 4 minutes/round (offline work about 3, hardware/human review about 5). Add 5–15 minutes evidence/handoff reserve: **45–75 minutes conditional closure budget**. This is not a successful-seal promise and may end with NOT_PASSED.

#### Risk Factors
1. T3 still explicitly names historical 61b-only/four-file flows. Current 5cd work must cite the later board-specific contract and exact candidate/recovery authority. It cannot be called verbatim T3 acceptance; board-specific reconciliation is required before final signoff, without weakening its two-cycle evidence standard.
2. Two cycles each require 20 seconds of real content motion, 3 seconds paused, 10 seconds resumed, exit to feed and icon reentry. The numeric lower bound is not the full operational duration. Audio has user confirmation; video remains unpassed.
3. A new API/decoder/import/producer blocker invalidates this closure estimate as a successful-delivery ETA. It does not prevent recording an honest failed outcome and restoring the baseline.
4. Main `explain` reports T23 5 skips and T3 9 skips with no run history. This is not evidence of missing inner host/build execution; use the pinned actual receipts. No retry-frequency calibration is possible from these main histories.

#### Confidence
- MEDIUM for no-new-code closure under stable restoration and accessible evidence; LOW for successful playback completion.

#### Dependency Analysis
- Critical path: actual outcome review → outer recovery confirmation → signed outcome/API delivery. API drafting and evidence indexing may overlap the review; final publication waits for exact outcome and restoration receipts.
- T23 review is wholly included in T3 module 1. Adding the two totals would double count shared work. Extra agents cannot parallelize a single board's lock or human playback verdict.
- No new repair contract exists for the currently observed black video. Under the estimate skill's exploration rule, **the next unknown repair round and total seal date remain unestimated**. First bind a real failure and precise scope, then estimate that contract's implementation, exception tests, ABI/build, one bounded deployment and recovery. A diagnostic timebox is not a repair deadline.
- REA allocation to Codex/octoscode is a tool-safety constraint, not evidence about another agent's technical ability and not itself a timing multiplier.
