spec: task
name: "Bind all thirty-two unlit U7 apps to raw terminal and thread evidence"
inherits: project
---

## 意图

Read the signed formal sixty-six cohort and replay first_fatal on the thirty-two non-own-UI records without changing frozen scores.

## 已定决策

- Select exactly the complement of the thirty-four signed own-UI keys, including the input-blocked no-capture key.
- Bind raw record and hilog hashes, app PID, screenshot cutoff and selected first termination; retain unknown causes and do not replace an early exit with a later crash.
- Preserve PID-scoped main-thread identification and final pre-t20 execution lines for B-class white apps; no observed thread stack means current execution state unknown.

## 边界

### 允许修改
- benchmark/2026-10-01-u7-death-clusters/**
- specs/u7-death-clusters/**
- tools/spec-checks/tests/u7_death_clusters.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Exact complement and terminal-first identity are preserved
  测试: u7_death_evidence
  假设 Signed thirty-four own-UI keys and raw records for the remaining thirty-two
  当 The bound offline intake is replayed
  那么 Exactly thirty-two unique rows preserve original first terminal root and no-capture evidence while source drift is rejected

场景: White apps retain honest main-thread observations
  测试: u7_death_threads
  假设 Target PID and available main-thread binding plus hilog timestamps
  当 Final execution lines before screenshot capture are extracted
  那么 Every retained line belongs to the target PID and thread and missing stack evidence remains unknown

## 排除范围

- New board sampling, screenshot reinterpretation and repairing first_fatal rules.
