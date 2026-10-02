spec: task
name: "Fresh bridge static and import evidence"
inherits: project
depends: t1-compose
---

## 意图

Compare the selected bridge with deployed846 and intermediatee34 while exposing all new coverage findings.

## 已定决策

- Verify unchanged ordered NEEDED and direct provider of the new z-level import.
- Separate inherited baseline changes from M5/M6 function and text changes.
- Preview identical exceptions without writing the active registry.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-native-assembly/**
- specs/u14-native-assembly/**
- tools/spec-checks/tests/u14_native_assembly.rs

## 验收标准

场景: Direct import and unchanged open sites
  测试: u14_native_static
  假设 Old and new bridges have fresh ELF scans
  当 Imports and open or namespace deltas are compared
  那么 NEEDED stays ordered and the sole M5 import plus three inherited e34 imports have pinned direct providers

场景: New coverage findings are not silently approved
  测试: u14_native_static
  假设 Bridge sources were absent from the old bounded N1 manifest
  当 Candidate sources and JNI lookup risks are included
  那么 Existing identical findings are separate from pending new findings and VM or production PASS is not claimed

## 排除范围

- Registry apply, deployment and measured application gain claims.
