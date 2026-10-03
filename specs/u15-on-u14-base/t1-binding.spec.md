spec: task
name: "Prepare immutable U15 metadata with explicit U14 BASE"
inherits: project
---

## 意图

Prepare common and 61b U15 transaction metadata using explicit matching U14 BASE and full SHA while preserving all candidate payload and native bindings.

## 已定决策

- Validate the reviewed candidate or an explicitly supplied arming-only equivalent; do not infer promotion.
- Refuse wrong variant, artifact change, reused output or installer action.
- Keep the existing unapproved policy and active registry untouched.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-on-u14-base/**
- specs/u15-on-u14-base/**
- tools/spec-checks/tests/u15_on_u14_base.rs
- README.md

## 验收标准

场景: Matching explicit bases preserve immutable candidate artifacts
  测试: u15_u14_binding
  假设 Both disabled U15 variants and matching U14 BASE plus full SHA are supplied
  当 Metadata copies are prepared
  那么 Five native paths three JARs and twenty image changes are recorded without installer actions

场景: Invalid identity and unauthorized artifact changes are refused
  测试: u15_u14_binding
  假设 A wrong variant or changed payload or installer action is supplied
  当 Binding checks run
  那么 Preparation refuses without authorizing execution or promotion

## 排除范围

- Apply registry, approve exact classes or promote U14.
