spec: task
name: "Full-package static delta and honest production dry-runs"
inherits: project
depends: [t1-compose]
---

## 意图

Inventory every effective native ELF, retain raw scanner findings, and distinguish proposed registry replay from actual production gate results.

## 已定决策

- Cache scans by verified artifact SHA while retaining every target and alias.
- Run auto_approve_exceptions without --apply; review new findings separately.
- No new path means an empty new-native admission draft, not inferred approval.
- External VM execution failure remains blocked, not copied from historical U12 results.

## 边界

### 允许修改
- benchmark/2026-10-02-u13-assembly-draft/**
- specs/u13-assembly-draft/**
- tools/spec-checks/tests/u13_assembly_draft.rs

## 验收标准

场景: Full-package evidence includes unchanged targets
  测试: u13_assembly_draft_evidence
  假设 A completed full-package scan inventory
  当 The report is checked
  那么 Every effective ELF target is represented and every scan SHA has evidence

场景: No new native member is admitted implicitly
  测试: u13_assembly_draft_evidence
  假设 Five changed existing native targets
  当 The composition and admission drafts are checked
  那么 New admissions are empty and both execution flags remain false

场景: Dry-run refusal is not reported as a pass
  测试: u13_assembly_draft_evidence
  假设 Actual production and surface evidence
  当 The report is checked
  那么 Return codes and actual OS are retained without claiming board activity

## 排除范围

- Registry mutation, board executor changes and new native candidate implementation.
