spec: task
name: "LibreSudoku ICU coverage"
inherits: project
---

## 意图

Decide whether the already-built ICU zero-init candidate covers the actual LibreSudoku country-display null path.

## 已定决策

- Trace the exact deployed Locale DEX and native country constructor before predicting coverage.
- Reuse 1e206531 if the path matches; do not make a second Java or native repair.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-libresudoku-icu/**
- tools/spec-checks/tests/u12_disappearance_native.rs

## 验收标准

场景: The existing ICU candidate covers the same static path
  测试: u12_libresudoku_icu
  假设 Actual PID log, pinned boot DEX and the approved ICU candidate
  当 Country-display null source and constructor codegen are checked
  那么 Prediction reuses 1e206531 for one key with next fatal and t20 unknown and no new library

## 排除范围

- Building another ICU, Java fallback edits and screenshot claims.
