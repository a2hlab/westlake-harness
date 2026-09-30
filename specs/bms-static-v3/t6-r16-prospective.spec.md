spec: task
name: "R16 prospective lighting and first-wall prediction"
inherits: project
depends: [t5-batch-feedback]
---

## 意图

Freeze one explicit lighting and first-wall forecast for all 66 keys before inspecting r16 full-sweep results, then evaluate only against independently observed outcomes.

## 已定决策

- Inputs are frozen r15c observations, current static outputs and previously disclosed r16/network changes. Do not read r16 full-run directories before the freeze.
- Freeze predictions, decision rules, input hashes and scoring policy together; immutable published SHA goes to the board immediately.
- Every key has a binary lighting forecast, confidence, first wall or none, candidate alternatives and generation assumptions. Unknown causes stay unknown even with a binary forecast.
- Score lighting only from screenshot adjudication; score first-wall labels separately. Preserve unknown and APK/profile mismatches.
- Because execution may already have started, separate outcome-blind forecasts from strictly pre-click forecasts using recorded clicked_at.

## 边界

### 允许修改
- benchmark/2026-09-30-r16-prospective/**
- specs/bms-static-v3/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No device operations, git metadata writes, edits to old frozen outputs or reading full r16 results before freezing.
- No changing forecasts or scoring definitions after outcome exposure.

## 验收标准

场景: 六十六项预测先冻结后读结果
  测试: r16_prospective_freeze
  假设 Frozen static and r15c inputs are available without new full-run outcomes
  当 Predictions and policy are emitted
  那么 Exactly 66 keys have binary lighting forecasts and explicit first-wall values
  并且 Input, code, policy and prediction hashes are recorded before result exposure

场景: 回测保留未知与时间边界
  测试: r16_prospective_scoring
  假设 Synthetic adjudicated outcomes include unknown, mismatched and post-freeze starts
  当 Frozen scoring rules evaluate them
  那么 Only adjudicated exact identities contribute to lighting accuracy
  并且 First-wall accuracy and strictly pre-click subsets have independent denominators

## 排除范围

- Runtime fixes, identifying screenshot content from process survival, claiming already-started cases were predicted before execution.
