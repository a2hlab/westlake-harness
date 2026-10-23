### Estimate: T71 passive first-launch exit attribution

#### Contract Summary
- **Scenarios**: 2 (1 evidence-match path + 1 missing/mismatched-record path).
- **Decisions**: 5 fixed choices.
- **Boundaries**: 2 allowed output paths; read-only board access; no new crash, debugger, memory inspection, runtime change or deployment.
- **Inherited constraints**: 6 project constraints; the user's new authorization covers limited attribution only.

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | Bind existing record to PID/time/boot window | S1,S2 | 2 | 1.2 | 2.4 | Record may be absent or a different category |
| 2 | Compare high-level module identity with existing source metadata | S1 | 1 | 1.2 | 1.2 | Exact symbol/source binding may be missing |
| 3 | Preserve gaps and review receipts | S1,S2 | 1 | 1.2 | 1.2 | No fallback to intrusive diagnosis |

#### Summary
- **Base rounds**: 4.
- **Integration**: +0.5 rounds.
- **Verification**: +1 independent receipt-review round, not a claimed lifecycle PASS.
- **Risk-adjusted total**: 6.3 rounds.
- **Estimated wallclock**: 10–15 minutes at approximately 2 minutes per round, with a hard 15-minute investigation stop. The prior T69/T70 read-only tasks each finished in about four minutes; this budget includes missing-record risk and outer review.

#### Risk Factors
1. No matching crash record or exact symbol identity may exist.
2. A record can identify where an exception surfaced without identifying its cause.
3. Tool refusal terminates the affected investigation; switching models is not a retry path.
4. This estimate covers the bounded investigation, not restoring reliable desktop launch. Repair cannot be sized before an actionable defect is identified.

#### Confidence
- MEDIUM for bounded investigation and receipt delivery.
- LOW for full startup repair; no defensible completion ETA yet.

#### Observed result
T71 stopped after about 2 minutes 5 seconds when the safety classifier interrupted follow-up reasoning. A matching native record was retained, but attribution remained unresolved. Early termination is not successful diagnostic completion. T72 is a separate ordinary UI operation check, not a substitute repair claim.
