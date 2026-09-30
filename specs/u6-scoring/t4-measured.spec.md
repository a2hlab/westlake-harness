spec: task
name: "Score outer-signed U6 against the frozen forecast"
inherits: project
depends: [t3-terminal]
---

## 意图

Use the complete four U6 shard directories and outer ACK95 04:36:43 screenshot signoff to score all 66 frozen rows independently on first wall checkpoints and t20.

## 已定决策

- Adapt the actual shard layout without writing source runs or changing frozen CSV b9a414ed.
- Verify all runtime and boot files plus per-key APK sidecars and first-attempt records. Changed inputs stay unknown and are listed separately.
- Use first_fatal for termination-linked wall evidence; never map an earlier warning to the causal wall or use absence of errors as checkpoint proof.
- Outer own-UI observations are 24 preserved plus catima opencamera feeder and two flaky keys; frozen flaky exclusions remain in scoring.
- Keep exact per-axis verdicts even if they differ from the outer aggregate lighting count.

## 边界

### 允许修改
- benchmark/2026-10-01-u6-scoring/**
- specs/u6-scoring/**
- tools/spec-checks/tests/u6_scoring.rs
- scripts/lab/first_fatal.py
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Actual shard intake preserves every first attempt and identity
  测试: u6_scoring_measured_intake
  假设 Four signed shard directories including the resumed 5ea shard
  当 The adapter binds selected records and checks the frozen inventories
  那么 All 66 unique keys are represented and changed APK or sidecar identities are explicit non-comparable observations

场景: Published scoring replays independently on three axes
  测试: u6_scoring_measured_replay
  假设 Pinned observation excerpts reviewed causes checkpoints and outer screenshot labels
  当 The frozen scorer replays every row
  那么 Published first-wall checkpoint and t20 counts match the reviewed per-row evidence without converting unknowns or flaky t20 to hits

## 排除范围

- Changing runtime files performing new board tests or modifying frozen predictions.
