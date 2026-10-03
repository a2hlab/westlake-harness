spec: task
name: "Audit strict registry rebinding and provide outer G2 commands"
inherits: project
depends: ["t1-classes.spec.md"]
---

## 意图

Provide all 204 old-to-new finding IDs with strict field comparisons and separately list any changed or new findings plus the exact guarded outer Mac and VM replay commands. Explain the ANL Jitsi fix and observation limits against the current U16 matrix.

## 已定决策

- Remove only binding and decision envelopes; retain every risk field including evidence line and sequence.
- Recompute issue IDs from native manifest inputs gate and exact finding bytes.
- Do not use broad auto-identical normalization to claim strict equality or run remote G2 here.
- Distinguish the paired Jitsi routing change from mechanical relink; absence from current signoffs is not lit or a current mover.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-outer-review-packet/**
- specs/u15-outer-review-packet/**
- tools/spec-checks/tests/u15_outer_review_packet.rs
- README.md

## 验收标准

场景: All mapped rows retain strict equality or explicit differences
  测试: u15_outer_registry
  假设 Fresh reports and the old-to-new ID mapping contain 204 rows
  当 Binding-free complete fields are compared
  那么 Every row has field proof and any line or sequence difference is separately reported without applying registry entries

场景: Evidence drift cannot be hidden by normalization
  测试: u15_outer_registry
  假设 Only an evidence line or registration sequence changes
  当 Strict finding comparison executes
  那么 The row is unequal and exact issue ID verification still applies

场景: ANL calibration does not invent an observed mover
  测试: u15_outer_registry
  假设 Paired ANL and host add Jitsi routing but the current matrix does not contain fd-meet
  当 Source binary deltas and existing host markers are audited
  那么 Report a conditional historical target separately from zero current covered moves and do not claim ANL-specific marker or lit

## 排除范围

- Apply exceptions, grant approval, execute VM or obtain board locks.
