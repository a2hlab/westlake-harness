spec: task
name: "Publish provisional shard scores without inventing outer acceptance"
inherits: project
depends: [t1-intake]
---

## 意图

Publish first-wall checkpoint and t20 scores separately for completed U7 shards, keeping analyst visual previews separate from outer-signed t20 results.

## 已定决策

- A screenshot draft may inform a provisional no-wall analysis but cannot authorize the t20 scoring axis.
- Missing positive checkpoint evidence remains unknown; install success alone cannot replace a demanded installed APK hash readback.
- Formal scoring requires all 66 unique frozen keys and hash-bound outer visual reviews; this initial delivery selects only completed 5ea.

## 边界

### 允许修改
- benchmark/2026-10-01-u7-scoring/**
- specs/u7-scoring/**
- tools/spec-checks/tests/u7_scoring.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Three axes remain independent and screenshots await outer review
  测试: u7_scoring_axes
  假设 A bound first wall and unsigned visual draft with missing positive checkpoint receipts
  当 The frozen scoring function is applied
  那么 First wall can be provisionally scored while checkpoint and t20 remain unknown and flaky predictions are not promoted

场景: Frozen evidence reproduces the preliminary report
  测试: u7_scoring_replay
  假设 Pinned completed shard observations and analyst reviews
  当 JSON and Markdown scoring reports are reproduced
  那么 Every selected key is represented with independent axis totals and missing shards while altered reviews or premature formalization are rejected

## 排除范围

- Declaring a full U7 outcome before all shards and outer screenshot signoff.
