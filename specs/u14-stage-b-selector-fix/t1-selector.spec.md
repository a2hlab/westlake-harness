spec: task
name: "Wire the complete U14 candidate union into Stage B"
inherits: project
---

## 意图

Replace the incomplete direct-runner selection with a named physical-candidate union for windows 1–6, classify exclusions and bind the actual CLI outputs into the disabled Stage B entry.

## 已定决策

- Direct and nested candidate runners are one domain; U13 controls are excluded.
- An unknown record path rejects; a pre-launch board interruption without hilog remains unknown.
- Re-enumerate the domain at retention admission instead of trusting a numeric count.

## 边界

### 允许修改
- scripts/lab/stage_a_selftest.py
- benchmark/2026-10-03-u14-stage-b/**
- benchmark/2026-10-08-u14-stage-b-selector-fix/**
- specs/u14-stage-b-selector-fix/**
- tools/spec-checks/tests/u14_stage_b_selector_fix.rs

## 验收标准

场景: Complete candidate selection
  测试: u14_stage_b_selector_fix
  假设 Windows 1–6 include direct runners and nested window6 candidates
  当 The CLI selects the U14 candidate domain
  那么 The 348 physical records pass and the old 308-record glob rejects

场景: Controls and unknown paths cannot enter
  测试: u14_stage_b_selector_fix
  假设 A U13 control runner is mixed into the requested selection or an unknown record path exists
  当 The selector and Stage B admission run
  那么 Each defect independently rejects and excluded classes are counted

场景: Missing observation is not success
  测试: u14_stage_b_selector_fix
  假设 The board is lost before click and no hilog exists
  当 The actual CLI aggregates the record
  那么 The record remains unknown with a separate evidence explanation

## 排除范围

- Signing promotion, device operations and changing active policy tables.
