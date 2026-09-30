spec: task
name: "Prepare completed U7 shard evidence against frozen identities"
inherits: project
---

## 意图

Bind completed shard records to the unchanged U7 candidate, actual input inventories, launch attempts and original t20 captures while preserving failed prelaunch attempts.

## 已定决策

- Verify 149 frozen pins and exact 119 runtime plus 36 boot entries; APK package metadata and external sidecars are separately checked.
- A completed shard can be processed without inventing missing shards; finalization requires all 66 keys.
- Zero child_hilog in a facts summary is not proof of absent app log evidence; use package/PID bindings in retained hilog.

## 边界

### 允许修改
- benchmark/2026-10-01-u7-scoring/**
- specs/u7-scoring/**
- tools/spec-checks/tests/u7_scoring.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Mismatched candidate or input remains noncomparable
  测试: u7_scoring_identity
  假设 Frozen identities and retained completed records
  当 A runtime boot metadata APK or sidecar hash changes
  那么 The identity check rejects comparison without rewriting the frozen forecast

场景: First timed attempt is preserved across aborted runs
  测试: u7_scoring_attempts
  假设 A no-click aborted run and a completed timed run plus a possible later retry
  当 Completed shard selection is audited
  那么 Prelaunch failures remain visible and selecting a later clicked attempt fails while missing shards cannot be finalized

## 排除范围

- Mutating runtime inputs logs frozen files or batch tools.
