spec: task
name: "Freeze a 66-key U6 first-wall forecast"
inherits: project
depends: [t1-inputs.spec.md]
---

## 意图

Produce a versioned CSV and JSON predicting each key's first blocking wall or expected crossing before the combined U6 full sweep, with explicit evidence and score criteria.

## 已定决策

- Use U5 and separately labeled component pretests as prior evidence, never U6 outcomes.
- Unresolved ordering or UI-only failures remain explicit unknown predictions rather than invented exception signatures.
- Require positive crossing evidence and target identity; preserve first-attempt scoring and flaky status.

## 边界

### 允许修改
- benchmark/2026-10-01-u6-prospective/**
- specs/u6-prospective/**
- tools/spec-checks/tests/u6_prospective.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Every cohort key has a reproducible prospective row
  测试: u6_forecast_coverage
  假设 The original 66-key cohort and the reviewed per-key forecast decisions are fixed
  当 CSV and JSON are generated
  那么 Each key occurs once with candidate input SHA expected first wall repair IDs evidence and explicit log plus t20 criteria

场景: Frozen predictions reject drift and missing positive evidence
  测试: u6_freeze_and_scoring
  假设 Frozen hashes and positive masked mismatch and missing evidence examples exist
  当 Identity and scoring rules run
  那么 Hash drift is refused no missing error becomes a crossing and all previous frozen predictions remain unchanged

## 排除范围

- Post-hoc rewriting of forecasts, U6 device execution, scoring a T7d rollout against the T7c forecast.
