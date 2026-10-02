spec: task
name: "U15 framework and FZ-005 preparation"
inherits: project
---

## 意图

Prepare pinned effective U14 boot inputs with the accepted Bitmap framework replacement, a disabled hw248 rebake recipe and a fresh paired receipt template.

## 已定决策

- Only framework9e55 replaces one of nine effective BCP inputs; stubs87cf and runtime JAR0349 are preserved.
- Rebuild the complete 27-image group with frozen ae865 dex2oat and 14b1 driver, two runs at identical working paths and live tee logging.
- hw248 has hostname ecs-9f6c; require the approved lab-home identity instead of inheriting the SSH user's HOME.
- New output hashes, actual changed-image count and approval remain unknown until execution and outer review.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-plan/**
- specs/u15-plan/**
- tools/spec-checks/tests/u15_plan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Effective inputs and complete forecast are pinned
  测试: u15_image_plan
  假设 Both U14 content bundles and the framework donor have exact SHA256 identities
  当 The offline input plan is validated
  那么 Exactly one BCP member changes and 27 outputs remain unbaked without claimed readiness

场景: Incomplete receipt or historical approval is rejected
  测试: u15_image_plan
  假设 The U15 bake has not executed
  当 A receipt lacks an input or output or substitutes the U14 exception
  那么 Validation rejects the claim and the default shell entry exits before any machine probe

## 排除范围

- Execute the recipe, modify registries, change bundle payloads or grant production admission.

