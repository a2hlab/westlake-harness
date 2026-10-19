### Estimate: Toutiao remaining video repair and acceptance, 2026-10-20 02:20

#### Contract Summary
- **Scenarios**: t1=3, t2=3, t3=9; remaining unique work grouped below, existing restore/build diagnostics reused.
- **Decisions**: current t1=4, t2 includes r1-r4 revisions, t3=9; candidate r9 not yet selected.
- **Boundaries**: t1=2 allowed paths, t2=5, t3=6; no random-crash diagnosis or user-data reset.
- **Inherited constraints**: six project constraints; real dynamic frames and audio evidence remain mandatory.

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | Exact Java codec / native network attribution | t1 S1–S3 | 6–10 | 1.3 | 8–13 | Two parallel lanes; actual provider and Java null path still unknown |
| 2 | Reuse repair, candidate build and rejection gates | t2 S1–S3 | 8–14 | 1.3 | 11–19 | Conditional on an existing implementation; no from-scratch codec |
| 3 | Two playback cycles, visual/audio and regression | t3 S1–S3,S5–S9 | 5–8 | 1.2 | 6–10 | Existing rollback and capture reused; still requires actual playback |
| 4 | Source/build/API delivery | t3 S4 | 2–3 | 1.0 | 2–3 | Existing renderer/receipts reused |

#### Summary
- **Base rounds**: 21–35.
- **Integration**: +3–5 rounds.
- **Verification**: +5 rounds (15 scenarios/3; prior passed checks reused unless inputs change).
- **Risk-adjusted total**: 35–55 rounds.
- **Estimated wallclock**: 120–240 minutes (3–4 minutes/round plus a small board-window buffer; static lanes overlap). First attributed result expected in 20–40 minutes, not playback completion.

#### Risk Factors
1. Network provider binding/addrinfo ABI and Java codec enumeration may expose distinct blockers.
2. If actual decoder/audio production implementation is missing, this estimate is invalid and must be replaced with an implementation contract.
3. More than one major failed candidate window invalidates the 2–4-hour range.
4. The 00:06–02:19 scheduler gap is an actual coordination failure, not technical work. It is not hidden in this remaining-work estimate.

#### Confidence
- LOW: exact next repair not selected; no claim of dynamic/audio success. Historical r1–r8 windows show hidden integration work, so this is a conditional planning range, not a completion promise.
