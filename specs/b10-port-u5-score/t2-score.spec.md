spec: task
name: "Score U5 against frozen J6 N4 predictions"
inherits: project
depends: [t1-paths.spec.md]
---

## 意图

Score all 66 first scheduled U5 attempts against the unchanged bae8fd74 prediction CSV, separately reporting checkpoint correctness, new walls and outer-reviewed t20 UI.

## 已定决策

- Use the frozen score_reviewed decision function, with positive evidence required for crossing and unknown for missing or masked evidence.
- Bind each record, APK, raw log and t20 image by SHA; subsequent flaky probes cannot replace first attempts.
- Use the outer loop's explicit U5 visual review as the UI authority, not process counts.

## 边界

### 允许修改
- benchmark/2026-09-30-u4-sweep/J6N4-SCORING.md
- benchmark/2026-09-30-u4-sweep/J6N4-SCORING.json
- benchmark/2026-09-30-u4-sweep/j6n4-scoring/**
- specs/b10-port-u5-score/**
- tools/spec-checks/tests/b10_port_u5.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Every frozen key keeps its first attempt and evidence identity
  测试: u5_score_identity
  假设 Frozen predictions and U5 evidence contain 66 unique keys
  当 The score report is verified
  那么 All keys remain including input failures and raw-line evidence references resolve to pinned excerpts

场景: Missing evidence never becomes a successful crossing
  测试: u5_score_decisions
  假设 Positive crossings unchanged walls missing evidence and failed promises are represented
  当 The frozen scoring rules evaluate reviewed observations
  那么 Counts and per-key results agree and unknown cases stay outside the evaluable denominator

## 排除范围

- Changing frozen forecasts, rerunning devices, attributing UI gains to one of several changed artifacts, or scoring later flaky probes as first attempts.
