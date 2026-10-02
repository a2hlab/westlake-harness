spec: task
name: "Relink and resident-only lineage proof"
inherits: project
---

## 意图

Provide instruction-level evidence for the compatibility diagnostic PC shift and source/binary evidence for two newly covered NOLOAD sites.

## 已定决策

- Compare branches, imports, GOT targets and string contents rather than instruction addresses alone.
- Retain the original unknown-clobber diagnostic even when control-flow explains it.
- New source coverage is not evidence that a resident owner is available at runtime.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-gate-review/**
- specs/u13-gate-review/**
- tools/spec-checks/tests/u13_gate_review.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Rebased function preserves semantic operands
  测试: u13_gate_review_proof
  假设 The two android_dlopen_ext bodies have different addresses
  当 Branch-relative operands and exact referenced symbols and strings are compared
  那么 The full normalized bodies match and the diagnostic PC shifts by0x300

场景: Old binary sites were not new loader behavior
  测试: u13_gate_review_proof
  假设 Full graphics source is newly added to N1 coverage
  当 Old source and both runtime scan records are inspected
  那么 Both old statements and NOW plus NOLOAD flags remain pinned with miss paths explicit

## 排除范围

- Scanner repairs, new exports and owner publication changes.
