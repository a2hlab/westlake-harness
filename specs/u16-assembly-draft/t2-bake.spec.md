spec: task
name: "U16 frozen FZ-005 rebake plan"
inherits: project
depends: t1-inputs
---

## 意图

Prepare a guarded hw248 two-run full 27-image rebake recipe, exact planned argv and a fresh input-bound paired receipt template without executing it.

## 已定决策

- Reuse U15 bcp-v2 frozen dex2oat ae865 and driver14b1, hostname ecs-9f6c and approved HOME identity.
- Both runs use one work path and distinct persistent tee logs and outputs; collect actual argv, toolchain, host libraries and every exit code.
- New stubs8593 inputs require new output comparison and boot.art evidence; U15 or T7d exceptions do not transfer automatically.
- The shell entry must exit 78 before any probe when no separate outer execution authorization is provided.

## 边界

### 允许修改
- benchmark/2026-10-03-u16-assembly-draft/**
- specs/u16-assembly-draft/**
- tools/spec-checks/tests/u16_assembly_draft.rs

## 验收标准

场景: Default entry cannot execute a bake
  测试: u16_draft_bake
  假设 No execution approval or completed bake exists
  当 The guarded entry and paired receipt template are checked
  那么 Entry exits 78 before probes and both runs have identical planned argv but null actual argv logs statuses and all 27 output hashes

场景: Partial evidence and borrowed approvals reject
  测试: u16_draft_bake
  假设 A fresh pair must bind all nine current JARs and all 27 outputs
  当 A receipt drops an input output or logging status or uses an old boot.art approval
  那么 The evidence check rejects without enabling deployment

## 排除范围

- Execute dex2oat, SSH, VM probes, board operations or frozen registration.

