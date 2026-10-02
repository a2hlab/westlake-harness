spec: task
name: "U15 native slots and transaction parameterization"
inherits: project
depends: ["t1-images.spec.md"]
---

## 意图

Pin the arrived M3 runtime and leave Mindustry host and compat v3 pending while preserving board-local content identities and requiring explicit future transaction bindings.

## 已定决策

- Runtime94c3 is a native input, not the separate unchanged runtime JAR0349.
- Pending host and compat slots contain no selected artifact or candidate hash.
- Common9b42 and 61bf589 content profiles remain disabled; no U13 or U14 promotion is inferred.
- Future transaction binding requires a base path, full SHA and signed per-board evidence; 61b preserves both installer51e identities.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-plan/**
- specs/u15-plan/**
- tools/spec-checks/tests/u15_plan.rs

## 验收标准

场景: Arrived native input and pending slots stay non-executable
  测试: u15_native_plan
  假设 M3 runtime94c3 has a persistent donor and host and compat donors have not arrived
  当 The native slot ledger is checked
  那么 Only M3 has a pinned candidate and no final bundle or deployment is claimed

场景: Implicit promotion or wrong board identity is rejected
  测试: u15_native_plan
  假设 Content and transaction bases may differ by board
  当 A future binding lacks signed evidence or changes a board-local installer
  那么 Validation rejects it rather than deriving transaction admission from the content bundle

## 排除范围

- Compose a final deployable bundle, build pending native items or execute production replay.
