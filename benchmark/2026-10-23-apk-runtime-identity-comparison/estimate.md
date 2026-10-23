### Estimate: T80 APK/runtime identity comparison; not demo completion

#### Contract Summary
- **Scenarios**: 2 (difference, match/missing evidence).
- **Decisions**: 5 task decisions; 3 inherited decisions.
- **Boundaries**: 3 allowed paths; no deployment, launch, configuration changes or fault diagnosis.
- **Inherited constraints**: 6. Contract rendered with agent-spec; parse 2 scenarios and lint 100%.

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | A: success-bound APK/ART/JAR/native inventory | both | 3 | 1.2 | 3.6 | Codex offline; missing SHA remains unknown |
| 2 | B: current exact-path fingerprints | both | 3 | 1.2 | 3.6 | CC read-only; up to 40 files |

#### Summary
- **Base rounds**: 6 total, 3 on each parallel branch.
- **Integration**: +1 outer comparison round.
- **Verification**: +1 evidence-review round; no unimplemented lifecycle test claim.
- **Risk-adjusted total**: 9.2 agent-rounds; 5.6 wallclock critical-path rounds, rounded to 6.
- **Estimated wallclock**: 12–18 minutes at 2–3 minutes/round. A first handoff at 5 minutes and B at 8 minutes are bounded checkpoints, not completion promises.

#### Risk Factors
1. Historical success records may not bind every deployed artifact; unknown is a valid result and gives no repair candidate.
2. Inner Codex transport failed in T78; device collection is assigned to CC, with no permission changes.
3. Fingerprint equality does not establish runtime readiness or explain an exit.
4. The earlier T74 source-analysis refusal remains separate from the repaired REA client approvals. This task does not repeat that refused analysis.

#### Confidence
- MEDIUM for the bounded comparison deliverable; LOW for whole-demo completion.
- Overall repair ETA is **unknown**: no identified cause or implementation candidate exists.
- Conditional final validation estimate from T75: 6 base rounds ×1.2 risk +1 integration +1 verification ≈10 rounds; 30–40 minutes at 3–4 minutes/round **after** a candidate is ready, excluding build/fix time and onsite power-action waiting. This is a validation attempt, not a promise it will pass.

#### Dependency Analysis
- T78 identity -> max(T80 A, T80 B) -> outer comparison.
- Repair is gated on a defensible candidate; actual power-cycle acceptance is gated on repair and an onsite power action. More agents cannot remove these dependencies.
