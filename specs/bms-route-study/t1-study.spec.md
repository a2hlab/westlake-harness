spec: task
name: "BMS source and evidence study"
inherits: project
---

## Intent

Audit PAC and payload materials, run the host-only readiness check, and deliver a first-hour BMS deployment checklist and historical app priority list for board item 15. The earlier six-question assessment is superseded; no device operations are executed.

## Decisions

- The report uses three execution-preparation sections and explicit R2 verification levels.
- The machine-readable results record artifact hashes, host readiness, first-hour steps, and app priorities.
- Source references use paths relative to 00.Workspace or this repository with line ranges.

## Boundaries

### Allowed Changes
- benchmark/2026-09-28-bms-route-study/**
- specs/bms-route-study/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### Forbidden
- Do not modify 00.Workspace or run device commands.
- Do not push commits.

## Completion Criteria

Scenario: Execution materials and traceable evidence are delivered
  Review: human
  Test: bms_route_study_evidence
  Given the three requirements in board item 15
  When the report and machine-readable results are inspected
  Then artifact audit, first-hour checklist, and historical app overlap exist
  And cited source spans resolve to recorded source hashes

Scenario: Reject promotion of unexecuted deployment to verified results
  Review: human
  Test: bms_route_study_evidence
  Given no device operation is authorized in this task
  When the report states its R2 verification levels
  Then device deployment is unverified
  And historical device evidence is labeled separately from present source verification
