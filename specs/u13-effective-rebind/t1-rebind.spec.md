spec: task
name: "Effective identity and unchanged payload rebind"
inherits: project
---

## 意图

Replace the wrong U12 comparison baseline with the real signed U10.1T8 state and expose all incremental members.

## 已定决策

- Recompute reference inventories and image references from signed deployed identities.
- Retain native manifest and input identity when output objects do not change.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-effective-rebind/**
- specs/u13-effective-rebind/**
- tools/spec-checks/tests/u13_effective_rebind.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Real baseline and unchanged native outputs
  测试: u13_effective_rebind
  假设 Signed U10.1T8 has 318 identity assertions and per-board fingerprints
  当 Rebinding comparison and transaction metadata
  那么 All baseline fingerprints match and no U13 output artifact changes

场景: Never transfer new findings or claim unrun production
  测试: u13_effective_rebind
  假设 Same-object prior outer reviews authorize binding transfers
  当 Fresh static differences are compared against those reviews
  那么 Unmatched findings remain blocked and production stays pending until fresh outer receipts

## 排除范围

- Native builds, device I/O, VM use, authorization and promotion.
