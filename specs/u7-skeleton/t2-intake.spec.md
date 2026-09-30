spec: task
name: "Keep U7 and U6 evidence intake fail closed"
inherits: project
depends: [t1-catalog]
---

## 意图

List outstanding evidence for final U7 prediction and U6 scoring in separate intake checklists. Validate their pending state and preserve three independent scoring axes using the frozen U6 helper.

## 已定决策

- Intake is a completeness checklist, not a deployment gate or a freeze authorization.
- Missing run identity or outer review cannot become a scoring hit; checkpoint and t20 outcomes remain independent.

## 边界

### 允许修改
- benchmark/2026-10-01-u7-prospective/**
- specs/u7-skeleton/**
- tools/spec-checks/tests/u7_skeleton.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Missing component evidence prevents readiness
  测试: u7_pending_intake
  假设 T7d and N6 reviewed board results are absent
  当 The intake readiness report is requested
  那么 It reports missing evidence and exit 2 without creating a CSV or freeze file

场景: Independent score axes reject unsigned or identity-mismatched results
  测试: u7_scoring_separation
  假设 Synthetic observations have partial review or missing identity
  当 The unchanged frozen U6 scorer is replayed
  那么 First wall checkpoint and t20 are scored independently and missing identity yields three unknowns

## 排除范围

- Producing actual U6 verdicts, editing frozen scoring criteria, accepting evidence merely because a checklist is populated.
