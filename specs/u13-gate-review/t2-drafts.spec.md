spec: task
name: "Pending exact-identity admission rows"
inherits: project
depends: [t1-proof]
---

## 意图

Produce directly reviewable rows without granting permission and require fresh bindings when the host or manifest changes.

## 已定决策

- Two N1 findings use native-predeploy row format; two compatibility aliases use static-policy format.
- Pending approvals are null, never placeholder strings accepted by a gate.
- Recompute issue IDs from manifest and inputs; do not replace only their hash fields.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-gate-review/**
- specs/u13-gate-review/**
- tools/spec-checks/tests/u13_gate_review.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Pending review cannot authorize deployment
  测试: u13_gate_review_drafts
  假设 Three review cases need two distinct gate formats
  当 Draft rows are emitted
  那么 N1 rows and both static aliases remain unapproved and execution is disabled

场景: Stale manifest is rejected
  测试: u13_gate_review_drafts
  假设 The held host changes the manifest identity
  当 A report still carries the previous manifest or input hash
  那么 Draft generation rejects it instead of rebinding approval implicitly

场景: Fresh identity changes finding IDs
  测试: u13_gate_review_drafts
  假设 The same source finding is scanned under a fresh manifest
  当 The report and inputs match that manifest
  那么 New issue IDs are calculated and approval fields remain null

## 排除范围

- Editing exception registries, applying automatic approvals and production dry-runs.
