spec: task
name: "Learn seven U5 requirement families without key allowlists"
inherits: project
---

## 意图

Add key-independent DEX and ELF rules for seven missed U5 families, retaining original evidence and distinguishing static requirements from runtime outcomes.

## 已定决策

- Inspect every classesN.dex and actual strong undefined symbols or DT_NEEDED edges.
- Never infer missing symbols from strings, weak imports, or another consumer's failure.
- Report startup reachability, namespace resolution and field initialization as unknown unless independently established.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/rules_u5_feedback.py
- benchmark/2026-09-29-static-wall-prediction/scan_u5_feedback.py
- benchmark/2026-10-01-u5-feedback-v1/**
- specs/u5-feedback/**
- tools/spec-checks/tests/u5_feedback.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Seven families have exact positive and near-miss negative rules
  测试: u5_feedback_rules
  假设 DEX calls and ELF imports or dependencies are supplied without app keys
  当 The scanner evaluates positive and mutated negative facts
  那么 Each family matches only its required consumer and API or dependency and weak imports do not become strong requirements

场景: Fourteen known keys are covered by static replay
  测试: u5_feedback_coverage
  假设 SHA-bound static facts and a separately reviewed U5 target list exist
  当 New predictions are regenerated without reading runtime outcomes
  那么 All fourteen keys have the expected conditional family with file evidence and coverage is labeled retrospective not held-out accuracy

## 排除范围

- Runtime fixes, device reruns, unconditional startup or lighting forecasts, changing historical scores.

