spec: task
name: "McDonald private zlib package route"
inherits: project
depends: [t1-policy]
---

## 意图

Append com.mcdonalds.app to the actual U12 zlib whitelist without importing another host routing implementation. Audit the SHA-bound librealmc imports before predicting that its first fatal can move.

## 已定决策

- Change one package literal in zlib-route.h, the header actually used by host 2a87118e.
- Preserve package-boundary matching and existing inherit calls.
- Report remaining symbols and unproved live namespace scope explicitly.

## 边界

### 允许修改
- benchmark/2026-10-02-u13-single-native/**
- tools/spec-checks/tests/u13_single_native.rs
- specs/u13-single-native/**

## 验收标准

场景: The exact package receives the existing private path
  测试: u13_single_native_route
  假设 The original two whitelist packages
  当 McDonald is added and the host route is tested
  那么 The three packages receive westlake_native and host C source remains unchanged

场景: Package prefixes do not receive the route
  测试: u13_single_native_route
  假设 com.mcdonalds.app.evil or a different app
  当 Search and permitted paths are evaluated
  那么 The private root is not returned

场景: An unresolved import is not declared fixed
  测试: u13_single_native_evidence
  假设 Actual librealmc DT_NEEDED and undefined symbols
  当 Candidate providers are compared
  那么 Any absent symbol or unproved scope remains a disclosed prediction condition

## 排除范围

- Root zlib alias, generic missing-library routes and deployment.
