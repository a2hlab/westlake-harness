spec: task
name: "Prepare three board B4 rerun and v4 aggregation offline"
inherits: project
depends: [t2-consolidate]
---

## Intent
Deliver item 59: one 66-key plan split into three balanced 22-key shards, complete master-runner commands and artifact roots, plus an offline v3-compatible v4 aggregation entry.

## Decisions
- Freeze master runner/manifest and historical v3 evidence identities; use history only to balance known wall families.
- Each full serial has one disjoint shard, preserving controls then blocked then tail order within that shard.
- All commands include reinstall, hilog 15, shots 5 and 20, strict focus checking, exact serial and lane.
- Aggregate current-round evidence only; preserve missing keys, rejected probes and unknown causes without automatic LIT claims.

## Boundaries
### Allowed Changes
- benchmark/2026-09-28-bms-route-deploy/batch/**
- specs/bms-route-batch/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- No device commands, runner behavior changes, deployment, commit or push.

## Completion Criteria
Scenario: All three shard plans are exhaustive balanced and executable offline
  Test: bms_rerun_offline
  Given the frozen 66-key manifest and historical v3 wall families
  When each shard CLI plan and all selected entries run against FakeBoard
  Then each serial has 22 unique keys and the union contains all 66 exactly once
  And command options and artifact paths match the shard config with no external subprocess

Scenario: v4 aggregation preserves per-key outcomes and visual uncertainty
  Test: bms_rerun_offline
  Given current-round records and target-attributed fatal evidence
  When the offline aggregation entry reads three shard outputs
  Then v3 category and early-blocker histograms are recomputed from current records
  And failed focus probes and late crashes remain distinct from visual success

Scenario: Duplicate stale wrong-board and incomplete inputs cannot become a complete v4
  Test: bms_rerun_offline
  Given a duplicate key wrong serial wrong run identity or missing records
  When aggregation validates its inputs
  Then invalid identity is rejected and incomplete input requires an explicit partial mode
  And partial results retain all missing keys as not-run without borrowing v3 outcomes
