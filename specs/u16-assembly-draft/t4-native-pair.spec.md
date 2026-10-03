spec: task
name: "U16 corrected two-artifact native static review"
inherits: project
depends: t3-native
---

## 意图

Stage the accepted runtime1d42 and corrected FlutterA3 eb90 together on actual U15 content. Keep their per-object static reports and combined raw native-gate rejections visible without enabling a generation bundle. Outer13:34 replaces b1c9 with A3 without changing the westlake_native owner.

## 已定决策

- Select only accepted FlutterA3 eb90 built on b1c9 and U15 9b82; retain all three ATrace exports and reject withdrawn15e988 or supersededb1c9.
- Exactly root runtime and westlake_flutter libandroid payloads change; westlake_native libandroid and existing domains remain unchanged.
- Both objects receive ABI calls and219-consumer checks against exact U15 counterparts; runtime callset3 remains a review item, not calls0.
- Combined N1/N2 use the current active table without signing or applying exceptions. All execution rollout and transaction BASE fields remain disabled or null.
- Recompute the eight arrived native/JAR increments for both U15 content variants and bind exact observation keys6f42bf0a; unbaked27 images remain pending, not invented CSV hashes. Removing all Flutter observers must reject both Flutter rows.

## 边界

### 允许修改
- benchmark/2026-10-03-u16-assembly-draft/**
- specs/u16-assembly-draft/**
- tools/spec-checks/tests/u16_assembly_draft.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Corrected pair has exact two payload changes and preserved ABI
  测试: u16_draft_native_pair
  假设 Corrected donorA3 eb90 and accepted runtime1d42 have full SHA256 identities
  当 Both native objects are compared with their exact U15 counterparts
  那么 Exactly two selected payloads change and Flutter removes zero exports with219-consumer checks and source-bound raw output retained

场景: Withdrawn donor or raw rejection never becomes final approval
  测试: u16_draft_native_pair
  假设 Withdrawn15e988 loses ATrace exports or combined native gates reject new bindings
  当 Slot validation and final disabled composition are checked
  那么 Withdrawn donor is rejected and active-table changes or fabricated final bundle or transaction BASE cannot pass

## 排除范围

- Rebuild native donors, rebake images, approve findings, update gate tables, contact VMs or deploy.
