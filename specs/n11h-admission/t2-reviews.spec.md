spec: task
name: "Bind itemized strings and exception review requests"
inherits: project
depends:
  - t1-compat.spec.md
---

## 意图

Package the exact strings allowance proposals and manifest-bound exception lineage with existing evidence, without self-approving the new owner query.

## 已定决策

- Every one of 3 dropped and 16 added strings has a unique outer checkbox, pinned byte-value hash, necessary reason and existing source line.
- N2 registry-delta contains exactly103 auto-identical observations matched against approved r3 bodies, with existing evidence paths and inherited removal conditions.
- Existing53 N1 observations are separately matched for optional old-row rebinding; the one new N1 request is never included in either exception delta.
- Simulated registry application may prove N2 clears and new N1 remains rejected, but does not authorize a window or edit a live registry.

## 边界

### 允许修改
- benchmark/2026-10-02-n11h-admission/**
- knowledge/smoke/n11h-compat-readout.json
- specs/n11h-admission/**
- tools/spec-checks/tests/n11h_admission.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: All strings require individual review
  测试: n11h_admission_strings
  假设 Pinned accepted native artifacts and their exact raw string differences
  当 The nineteen-item allowance checklist is generated
  那么 It covers each delta once with a source witness, preserves unrelated strings, and has no checked or approved row

场景: Identical finding lineage cannot approve a new query
  测试: n11h_admission_exceptions
  假设 Approved r3 findings and the accepted new manifest's raw rejection report
  当 N2 and old N1 semantic matches produce proposed deltas and the new N1 produces an outer review request
  那么 Exactly103 N2 and53 old N1 match, evidence exists, binding IDs recompute exactly, and the new N1 stays rejected in simulation

## 排除范围

- No live registry edit or outer approval fabrication; no pass claim for the complete candidate.
