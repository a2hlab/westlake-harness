### Estimate: APK slides and illustrated inventory

#### Contract Summary
- **Scenarios**: 4 (2 happy + 2 exception)
- **Decisions**: 3 fixed choices
- **Boundaries**: 3 allowed paths, 2 forbidden rules
- **Inherited constraints**: 2

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | Evidence selection and curated PPTX | S1 | 3 | 1.2 | 3.6 | Known python-pptx pattern; verify real images |
| 2 | Shared manifest, classified deck and inventory | S2 | 4 | 1.2 | 4.8 | Five output formats; preserve status and source |
| 3 | Exclusions and missing evidence | S3 | 1 | 1.2 | 1.2 | Canonical 115/13 partition available |
| 4 | Package integrity and rendering | S4 | 2 | 1.2 | 2.4 | ZIP/media references and native viewer |

#### Summary

- **Base rounds**: 10
- **Integration**: +1 rounds
- **Verification**: +2 rounds (lifecycle retries)
- **Risk-adjusted total**: 15 rounds
- **Estimated wallclock**: 30–40 minutes (at 2–2.7 min/round); first curated deck 10–15 minutes from dependency readiness.

#### Risk Factors
1. Ignored screenshots live in a sibling worktree, requiring hash-bound copying.
2. Native rendering is subject to application availability and sandbox access; LibreOffice wrapper exists but its target app does not.
3. Network installation and main-worktree board writes need outer support under this sandbox. Artifacts remain persistent in delivery.

#### Confidence
- MEDIUM: Tight contract and deterministic counts; native render availability uncertain.
