spec: task
name: "Build an unsigned U14 Stage A closing packet"
inherits: project
---

## 意图

Aggregate candidate runner records from six windows, rescan all PID failure lines and explain each unknown issue; bind signed visual coverage and pending seal/OrganicMaps to an unsigned decision draft.

## 已定决策

- Reuse schema-2 process_selftest and U14 retention criteria; one badtag always vetoes.
- Window6 candidate and control trees are separate, not captured by the old direct-runner glob.
- promotion_authorized remains null; only the outer can sign after the 126-key gate closes.

## 边界

### 允许修改
- benchmark/2026-10-08-u14-stage-a-decision-draft/**
- specs/u14-stage-a-decision-draft/**
- tools/spec-checks/tests/u14_stage_a_decision_draft.rs

## 验收标准

场景: Select only physical candidate records
  测试: u14_stage_a_decision_draft
  假设 Direct runner and nested window6 candidate records coexist with control, recovery, copies and symlinks
  当 The record domain is enumerated
  那么 Only candidate records enter the aggregate and every excluded record has an explicit class

场景: Exact bundle and report bytes are required
  测试: u14_stage_a_decision_draft
  假设 The candidate bundle is wrong or report bytes change
  当 The retention verifier checks the packet
  那么 Each independent defect rejects

场景: Every unknown issue needs an explanation
  测试: u14_stage_a_decision_draft
  假设 One required explanation is missing
  当 The retention verifier checks the packet
  那么 The incomplete issue set rejects

场景: A badtag from any PID vetoes
  测试: u14_stage_a_decision_draft
  假设 A failure marker exists for a PID absent from the t20 process list
  当 The all-PID rescan and retention verifier run
  那么 The failure rejects even if package binding matches

场景: Incomplete visual coverage never authorizes promotion
  测试: u14_stage_a_decision_draft
  假设 Only 123 of the 126 signed reference keys are measured
  当 The regression gate is checked
  那么 Promotion rejects and the actual draft stays unsigned with pending rows

## 排除范围

- Device restoration, screenshot interpretation, promotion execution and signing for the outer.
