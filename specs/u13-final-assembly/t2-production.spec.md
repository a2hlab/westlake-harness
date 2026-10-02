spec: task
name: "Fresh two-surface production receipts"
inherits: project
depends: t1-compose
---

## 意图

Accept only real fresh production outputs bound to the final bundle while leaving device execution disabled.

## 已定决策

- Failed lane-local probes remain failures; accessible outer replay is separately attributed.
- Verify original output hashes, actual OS identity, final bindings and all production checks.
- Production PASS is distinct from outer window authorization and screenshot outcomes.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-final-assembly/**
- specs/u13-final-assembly/**
- tools/spec-checks/tests/u13_final_assembly.rs

## 验收标准

场景: Real Mac and VM receipts bind the same final package
  测试: u13_final_production
  假设 Accessible outer replay produces actual Darwin and Linux results
  当 Original outputs and native inputs plus transaction plans are checked
  那么 Both surfaces have exit zero and G1 G2 static native and frozen checks pass for the identical final SHA

场景: Green production checks do not authorize a window
  测试: u13_final_production
  假设 Both production executor dry runs succeed
  当 Final bundle and report authorization flags are inspected
  那么 Device IO and deployable remain false and Stage A authorization is pending

## 排除范围

- Device access, deployment, promotion and screen interpretation.
