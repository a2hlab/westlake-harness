spec: task
name: "Compose only the three reviewed native donors"
inherits: project
---

## 意图

Produce an exact, disabled U13 draft on U12 with no host or Java changes and paired alias rollback.

## 已定决策

- Reuse the U12 production bundle validator and planner.
- Verify full SHA for each donor and both frozen base manifests.
- Bind source sidecars to the actual new artifact bytes; do not reuse stale runtime provenance.

## 边界

### 允许修改
- benchmark/2026-10-02-u13-assembly-draft/**
- specs/u13-assembly-draft/**
- tools/spec-checks/tests/u13_assembly_draft.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: The draft cannot authorize execution
  测试: u13_assembly_draft_disabled
  假设 An offline candidate manifest
  当 The safety guard checks its rollout flags and authorization
  那么 Enabled flags or a window authorization are rejected

场景: The held host remains unchanged
  测试: u13_assembly_draft_disabled
  假设 A draft with exact U12 host identity
  当 The proposed McDonald host is substituted
  那么 The guard rejects the candidate

场景: Both aliases are one transaction
  测试: u13_assembly_draft_disabled
  假设 Root and route compat and policy aliases
  当 Either alias differs from its paired frozen donor
  那么 The guard rejects the split transaction

## 排除范围

- New builds, automatic registry approval, screenshot acceptance and deployment.
