spec: task
name: "Exact guarded gate patch batch"
inherits: project
---

## 意图

Prepare sequential byte-exact U15 204-row and U16 208-row native patches, one U16 image exception and separate approved static-policy outputs. Supply an outer-only transactional runner with independent per-stage prerequisites and rollback, plus the new PendingFuture Class context.

## 已定决策

- Prove202 inherited U16 findings without dropping evidence lines; six additional signed rows retain exact scope.
- Each stage checks all held views and target SHA before writing. Hold nonblocking maintenance file mutexes across application and validation to prevent a new window racing table writes.
- Prebuild all staged bytes and verify patches/tool/signature hashes. Archive original bytes, restore on failure and provide exact-postimage-only explicit rollback.
- Static policies are derived review outputs for a later bundle rebind, never in-place authorized bundle edits.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-u16-gate-batch/**
- specs/u15-u16-gate-batch/**
- tools/spec-checks/tests/u15_u16_gate_batch.rs

## 验收标准

场景: Batch projects only signed objects
  测试: u15_u16_gate_batch_guards
  假设 Signed204 and208 native rows, one image pair and exact class/delta policies exist
  当 The prepared changeset is checked
  那么 It preserves prior rows and authorized bundles and records all approved scope projections

场景: Held board or stale target refuses before writes
  测试: u15_u16_gate_batch_guards
  假设 One held result is nonempty or a target SHA differs
  当 The guarded stage is requested
  那么 It writes no gate bytes and rejects ambiguous empty command results

场景: Failure rolls back exact original bytes
  测试: u15_u16_gate_batch_guards
  假设 A write or post-write validator fails after an earlier stage succeeded
  当 The transaction handles the failure
  那么 It restores all changed targets and retains original execution logs

场景: Disabled preview cannot apply or access boards
  测试: u15_u16_gate_batch_guards
  假设 The explicit outer apply flag is absent
  当 The default entry is executed
  那么 It only calculates the planned bytes and never checks live locks or writes gates

## 排除范围

- Deployment, remote operation, committing, gate-code changes, new findings or altering signed content.
