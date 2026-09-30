spec: task
name: "Freeze v2 for the v3c r17j 66-key sweep"
inherits: project
depends: [t1-forecast]
---

## 意图

Freeze one auditable prediction per application before reading the new full sweep. Distinguish expected own UI, progress past a named prior wall, unchanged blocking behavior and unknown.

## 已定决策

- Pin v3c package 668e4f7c, r17j JAR 20dcb71b and installer background-start plus SelectLauncher prerequisites.
- Cite prior first-hand logs or adjudicated screenshots for each key. A supplied library or removed first wall does not establish a visible destination page.
- Preserve all earlier freezes and snapshots. Score later only with matched APK/profile identity and launch time after freeze, separately by board and prior calibration.

## 边界

### 允许修改
- benchmark/2026-09-30-v3c-r17j-prospective/**
- specs/bms-background-start/t2-v3c-r17j.spec.md
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No board I/O or new full-sweep results before freeze. Do not change v0/v1.

## 验收标准

场景: 完整冻结
  测试: v3c_r17j_freeze
  假设 The prior 66-key input and exact candidate profile are available
  当 v2 is frozen
  那么 Each unique key has an APK identity, one of four forecast labels and cited prior evidence
  并且 Full SHA receipts pin the predictions, policy and source snapshots

场景: 身份或时间失败拒绝计分
  测试: v3c_r17j_scoring
  假设 Observations have a wrong APK or profile, missing evidence or pre-freeze launch time
  当 The scorer checks eligibility
  那么 Invalid observations are excluded with reasons and unknown forecasts abstain
  并且 No process-survival field establishes a visible page

## 排除范围

- Deploying, installing, repairing runtime behavior, or making future screenshot judgments.
