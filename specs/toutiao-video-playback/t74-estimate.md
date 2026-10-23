### Estimate: T74 cold-power demo readiness and launch delay audit

#### Contract Summary
- **Scenarios**: 2 (1 evidence/candidate + 1 insufficient-evidence/denial)
- **Decisions**: 5 task choices (plus 3 inherited project decisions)
- **Boundaries**: 3 allowed output paths, 1 grouped prohibition
- **Inherited constraints**: 6

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | Existing boot chain and ordinary event timeline | 1 | 3 | 1.2 | 3.6 | Exact deployed-source map exists; causal timing remains unknown |
| 2 | Candidate or bounded missing-evidence handoff | 2 | 1 | 1.2 | 1.2 | No board changes; excludes stopped fault diagnosis |

#### Summary
- **Base rounds**: 4
- **Integration**: +0.5 rounds
- **Verification**: +1 round (artifact review, not unimplemented lifecycle test)
- **Risk-adjusted total**: 6.3 rounds
- **Estimated wallclock**: 13–19 minutes at 2–3 min/round; first useful findings requested within 8 minutes, not guaranteed completion.

#### Risk Factors
1. The 31-second click-to-spawn interval has not yet been attributed to a specific wait.
2. This contract only delivers readiness analysis/candidate; it does not implement or verify the complete cold-power requirement.
3. Conditional downstream planning allowance is 30–60 additional minutes if the repair is confined to the existing launch scripts, including board verification; this is not a full-task guarantee. Unknown runtime blockers require re-estimation.
4. Physical power removal may require the user; external waiting is excluded. Normal reboot and USB disconnect are not substitutes.

#### Confidence
- MEDIUM for bounded T74 analysis; LOW for full cold-power demonstration completion until the first findings.
