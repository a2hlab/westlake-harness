spec: task
name: "U14 effective BCP and rebake plan"
inherits: project
---

## 意图

Snapshot the accepted U14 runtime and stubs inputs and prepare a disabled hw248 FZ-005 rebake plan.

## 已定决策

- Runtime0349 is outside BCP; only stubs87cf replaces one of nine BCP inputs.
- Generate 27 predicted image rows without inventing output hashes or a changed-file count.
- Record live tee logging, same-work-path two-run comparison and exact paired receipt checks.
- The repository t5 script is not the frozen14b1 driver; require remote SHA verification before execution.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-jar-image-plan/**
- specs/u14-jar-image-plan/**
- tools/spec-checks/tests/u14_jar_image_plan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Plan binds exactly the effective inputs
  测试: u14_jar_image_plan
  假设 The U13 content base and U14 runtime and stubs donors have pinned SHA256 values
  当 Input snapshots and the image forecast are checked offline
  那么 Exactly one of nine BCP inputs changes and all 27 candidate output hashes remain unknown

场景: Incomplete or broadened evidence is rejected
  测试: u14_jar_image_plan
  假设 No U14 bake or production replay has run
  当 A receipt omits an input or output or claims a historical exception as automatic approval
  那么 Validation rejects it rather than granting readiness

## 排除范围

- Execute dex2oat, replace JARs or images, modify gate registries or authorize a window.
