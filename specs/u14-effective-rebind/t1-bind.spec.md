spec: task
name: "U14 per-board conditional binding and ABI slot"
inherits: project
---

## 意图

Provide parameterized common and 61b U13 transaction bases, preserve the board-local installer, and accept only a hash-pinned native ABI slot replacement after its donor arrives.

## 已定决策

- Common U13 content is 91272eaf; 61b content is 8861a11a. Planned identities come from U13 candidate maps, never from its T8 reference files.
- Only westlake_native/libwestlake_native_abi.so may change in the existing U14 artifact inventory. Images, JARs, root and Flutter ABI aliases remain byte-identical.
- Exception previews are unapplied and new findings remain unapproved.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-effective-rebind/**
- specs/u14-effective-rebind/**
- tools/spec-checks/tests/u14_effective_rebind.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Combined variant parameters bind planned U13 identities
  测试: u14_effective_binding
  假设 Common and 61b baselines have distinct bundle hashes
  当 Finalization selects a variant and explicit baseline hash
  那么 The selected base and full identity agree, while promotion_confirmed and execution_enabled remain false

场景: Wrong baseline or installer identity is rejected
  测试: u14_effective_binding
  假设 61b has two board-local 51e1 installer paths
  当 A baseline hash, reference identity or installer expected hash differs
  那么 Validation raises an error and produces no approved transaction

场景: ABI-only artifact delta rejects unrelated changes
  测试: u14_effective_binding
  假设 The incoming ABI has an explicit hash and verified donor evidence
  当 Artifact maps include a changed JAR, image, root alias or additional member
  那么 Validation rejects; an absent donor is pending, not a fabricated v2

场景: Fresh preview never applies pending approval
  测试: u14_effective_preview
  假设 Native findings change IDs with input binding
  当 Old and new findings are compared
  那么 Metadata-only matches retain old to new ID evidence, and new semantic findings have no approval

场景: Exact image approval cannot authorize another pair
  测试: u14_effective_preview
  假设 The outer signed only the new U14 input/output pair and interval
  当 Approval object hash, signer, input or output binding differs
  那么 Validation rejects; a matching approval is recorded without rewriting historical build receipts

场景: Diagnostic T8 references are explicit and replay is disabled
  测试: u14_effective_binding
  假设 Promotion has not occurred and the outer requests a diagnostic replay
  当 T8 common190afedd or 61b c0adc4a9 is selected, or replay lacks the outer token
  那么 The diagnostic base is explicitly bound and unauthorized replay exits 78 before any VM or device command

## 排除范围

- Promotion, authorization, native builds, image rebakes and production VM replay.
