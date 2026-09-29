spec: task
name: "V2 secondary Activity and boot provider feedback"
inherits: project
depends: [t7-r16-feedback]
---

## 意图

Add two evidence-backed DEX requirement detectors to B10 after the v2 evaluation. Publish a separate 66-key post-hoc calibration and a runtime-only EGL experiment without altering prospective results.

## 已定决策

- Reuse existing DEX grammar, manifest parsing and bounded call resolution; record explicit destinations separately from class hints and unresolved callbacks.
- Detect ServiceLoader/JAR verification and provider-name lookup requirements; a runtime-JAR definition does not establish boot-loader visibility.
- EGL repeated-window surface creation remains runtime-only. API references do not prove a repeated native window or a failure.
- Pin APK identities and v2 frozen/report hashes. Calibration is post-hoc; unknown observations are excluded from precision denominators.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/*feedback_v2*.py
- benchmark/2026-09-30-v2-scanner-feedback/**
- specs/bms-static-v3/t8-v2-feedback.spec.md
- tools/spec-checks/src/lib.rs
- .octos/KNOWLEDGE-DIGEST.md
- README.md

### 禁止
- No devices, runtime repairs, APK changes, git metadata writes, or edits to existing frozen forecasts and backtests.

## 验收标准

场景: Static witnesses and unknown exceptions
  测试: v2_feedback_rules
  假设 DEX contains explicit Activity targets, unresolved callbacks and unrelated API names
  当 The two static detectors classify these instructions
  那么 Exact non-launcher destinations and provider lookup requirements have evidence
  并且 Class hints, runtime-only EGL and missing boot definitions cannot become proven execution or successful visibility

场景: Post-hoc coverage and freeze mutation rejection
  测试: v2_feedback_matrix
  假设 Sixty-six pinned v2 keys and their separately recorded outcomes exist
  当 The scanner publishes a calibration matrix
  那么 It emits 198 key-family cells with explicit unknown states for absent inputs
  并且 The prior frozen forecast and backtest hashes remain unchanged and the report labels its calibration post-hoc

## 排除范围

- New prospective accuracy, proving branch execution, runtime repairs, and board experiments.
