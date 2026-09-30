spec: task
name: "Freeze a 66-key Activity transition forecast"
inherits: project
---

## 意图

Predict which applications advance or show a page after START_ABILITIES_FROM_BACKGROUND is granted, before reading rollout results.

## 已定决策

- Reuse the existing DEX/manifest scanner; inspect launcher lifecycle calls and Splash classes, resolve explicit Intent class targets and local factory returns conservatively.
- Keep exact APK identity, calibration labels and source callsite witnesses for every key.
- Separate permission benefit, next-Activity dispatch and visible-page predictions, including unresolved paths and runtime prerequisites.
- Freeze CSV, JSON, policy and input hashes with UTC time; preserve freezes and score only matched, grant-confirmed, post-freeze observations.

## 边界

### 允许修改
- benchmark/2026-09-30-background-start-prospective/**
- specs/bms-background-start/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No post-authorization run/screenshot/log reads before freezing; no modifications to older predictions or raw inputs.

## 验收标准

场景: Intent 与分支边界
  测试: background_start_rules
  假设 Explicit Intent targets, factory returns, unresolved branches and finish calls are present
  当 The detector classifies Activity transitions
  那么 Definite target flow is distinct from names-only hints and ambiguous calls remain unknown
  并且 Calibration evidence does not become a claimed static detection

场景: 前瞻冻结和回测口径
  测试: background_start_freeze
  假设 The 66-key manifest and a new offline prediction are supplied
  当 The predictor freezes its output and prepares future scoring
  那么 Exactly 66 keys retain APK identity and full hashes with immutable timestamps
  并且 Unknown permissions or pre-freeze clicks are excluded from strict prospective scoring with reasons

## 排除范围

- Implementing permissions, exercising applications, making screenshot judgments, or assuming runtime parity.
