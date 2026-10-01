spec: task
name: "Inventory U8 delegation and reference registration evidence"
inherits: project
---

## 意图

Enumerate direct, dynamic, and separate Typeface registration dispatch and retain function bodies, initialization coordinates and cache-owner evidence without inventing skipped side effects.

## 已定决策

- Strip comments without losing original line coordinates; commented-out registration names are not active dispatch.
- Preserve exact mangled provider symbol and source identity; unresolved functions and unknown version provenance remain unknown.
- Treat whole-function delegation, external initializer omissions, and duplicate-owner cache omissions as different claims.

## 边界

### 允许修改
- benchmark/2026-10-01-b10-registration-impact/**
- specs/b10-registration-impact/**
- tools/spec-checks/tests/b10_registration_impact.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Active delegation remains complete and source-coordinate bound
  测试: b10_registration_inventory
  假设 Active and commented registration entries and a nested original function
  当 Registration dispatch and initialization evidence are parsed
  那么 Only active entries count and body lines are preserved without treating full-function delegation as skipped initialization

场景: Wrong source identity is refused
  测试: b10_registration_identity
  假设 A changed source hash or an unverified AOSP version
  当 A final reference comparison is requested
  那么 The changed hash is rejected and the wrong version cannot become a verified comparison

## 排除范围

- Repairing owner caches or inferring runtime call success from source or exported symbols.
