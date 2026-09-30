# Contract Review: Score U5 against frozen J6 N4 predictions

## Intent

Score all 66 first scheduled U5 attempts against the unchanged bae8fd74 prediction CSV, separately reporting checkpoint correctness, new walls and outer-reviewed t20 UI.

## Decisions

- Use the frozen score_reviewed decision function, with positive evidence required for crossing and unknown for missing or masked evidence.
- Bind each record, APK, raw log and t20 image by SHA; subsequent flaky probes cannot replace first attempts.
- Use the outer loop's explicit U5 visual review as the UI authority, not process counts.

## Boundaries

**Allowed:**
- benchmark/2026-09-30-u4-sweep/J6N4-SCORING.md
- benchmark/2026-09-30-u4-sweep/J6N4-SCORING.json
- benchmark/2026-09-30-u4-sweep/j6n4-scoring/**
- specs/b10-port-u5-score/**
- tools/spec-checks/tests/b10_port_u5.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

**Out of Scope:**
- Changing frozen forecasts, rerunning devices, attributing UI gains to one of several changed artifacts, or scoring later flaky probes as first attempts.

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 0 | 0 | 100.0% |

- ✅ Every frozen key keeps its first attempt and evidence identity
  - test: `u5_score_identity`
- ✅ Missing evidence never becomes a successful crossing
  - test: `u5_score_decisions`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Every frozen key keeps its first attempt and evidence identity | u5_score_identity | found | pass | computational |
| — | Missing evidence never becomes a successful crossing | u5_score_decisions | found | pass | computational |
