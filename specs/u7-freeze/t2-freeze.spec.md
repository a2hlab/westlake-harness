spec: task
name: "Freeze 66 prospective U7 rows before combined sweep"
inherits: project
depends: [t1-inputs]
---

## 意图

Use signed U6 observations and labeled T7d component priors to predict the first wall named repair checkpoints and first t20 for every selected key, then register an immutable CSV SHA before the combined run.

## 已定决策

- Treat six changed U6 identities as observations only, not revised U6 scores; freeze their actual current inputs for U7.
- Preserve four flaky exclusions and unknown causes; do not infer a Compose root cause from a white screenshot.
- Pin prediction code source evidence input identities and candidate files in FREEZE; refuse a second freeze or altered evidence.

## 边界

### 允许修改
- benchmark/2026-10-01-u7-prospective/v1/**
- benchmark/2026-10-01-u7-prospective/README.md
- specs/u7-freeze/**
- tools/spec-checks/tests/u7_freeze.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: All predictions preserve three independent prospective axes
  测试: u7_final_predictions
  假设 Signed U6 observations and separate T7d component records
  当 Predictions are reproduced
  那么 There are 66 unique input-bound rows with explicit first-wall checkpoint t20 criteria and labeled component priors without any combined U7 score

场景: Freeze rejects altered files and duplicate registration
  测试: u7_final_freeze
  假设 A registered prediction CSV and pinned source files
  当 The bundle is verified or a second freeze is attempted
  那么 Unmodified files pass while changed bytes missing evidence or refreezing fail without rewriting the first freeze

## 排除范围

- Scoring U7 before its measured sweep or weakening the strict U6 scoring identity gate.
