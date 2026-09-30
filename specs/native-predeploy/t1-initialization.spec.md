spec: task
name: "Gate packaged native initialization"
inherits: project
---

## 意图

Turn the accepted native source/DEX replay scanner into a build-output gate bound to the candidate package, rather than treating a historical replay as permission to deploy a new binary.

## 已定决策

- Require both namespace and JNI-order coverage and bind every profile artifact, source manifest and DEX artifact to the candidate package.
- Preserve scanner findings and unknowns. Exceptions require exact issue and input identities, rationale, evidence, approval and removal conditions.
- Expose a machine-readable CLI result and reusable Python API for the deployment lane.

## 边界

### 允许修改
- scripts/lab/native_*.py
- knowledge/gates/native-predeploy-exceptions.json
- benchmark/2026-10-01-native-predeploy-gates/**
- specs/native-predeploy/**
- tools/spec-checks/tests/native_predeploy.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md

### 禁止
- Do not weaken or modify the historical scanner, old fixtures or deployment implementation.

## 验收标准

场景: Real scanner risks reject candidate initialization
  测试: native_predeploy_initialization
  假设 A package-bound manifest covers namespace creation and JNI initialization
  当 The gate runs with bad and corrected source orders
  那么 Bad order or NOLOAD findings reject and bounded clean inputs pass

场景: Evidence cannot authorize another package
  测试: native_predeploy_identity
  假设 The manifest and source bytes are pinned
  当 Package bytes source hashes DEX identity or required profile coverage change
  那么 The gate fails closed before a pass can be returned

场景: Exceptions cannot hide new failures
  测试: native_predeploy_exceptions
  假设 Exact approved exceptions describe known findings
  当 A new finding appears or an old finding disappears
  那么 New findings reject and disappeared matching exceptions report STALE

## 排除范围

- Rebuilding native binaries, proving C++ source-to-binary equivalence, approving operational exceptions, or deploying to a device.
