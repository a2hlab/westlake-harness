spec: task
name: "Task90 r15c observations and next wall predictions"
inherits: project
depends: [t3-r14-wall-families]
---

## 意图

Within thirty minutes, revise frozen v4-r2 predictions using all 66 r15c records and the two-layer network requirement; publish separate stub_ok and needs_real priorities for the next run.

## 已定决策

- Preserve v4-r2 outputs; write a versioned task90 successor.
- Count captures from record.json and survival from target UID process rows. Only outer screenshot adjudication establishes own UI.
- Rank startup-observed affected app keys separately from static reference counts. Tolerated errors on accepted apps cannot be counted as blocking walls.
- Network recovery requires child gid 3003 and installed synthesized HAP INTERNET permission; existing installations require reinstall with the corrected installer.
- Outcome-informed revision is retrospective, not a new backtest success. Missing inputs and uncertain causality remain unknown.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/**
- tools/spec-checks/**
- specs/bms-static-v3/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No board operations, runtime changes, input mutations or git metadata writes.
- Do not equate process survival, warnings, view visibility constants or permission declarations with successful first screen/network access.

## 验收标准

场景: 原始证据计数与截图签认分开
  测试: b90_observations
  假设 66 recorded APK identities and process snapshots exist
  当 Offline observation extraction runs
  那么 Capture and survival counts have per-app source evidence
  并且 Only the six externally adjudicated keys are labeled own UI

场景: 联网候选需要界面与故障双证据
  测试: b90_network
  假设 Some apps have own UI and target-process network denial
  当 Conditional direct recovery candidates are emitted
  那么 Noice keys are candidates requiring both network layers and reinstall
  并且 Wikipedia with additional known walls is excluded from direct recovery

场景: 下一轮排序不污染旧预测
  测试: b90_rankings
  假设 Frozen prior predictions and PID-attributed startup failures are available
  当 Revised predictions and grouped rankings are written
  那么 All 66 keys have coverage and uncertainty labels and both policy lists are ordered by affected startup keys
  并且 Prior frozen outputs remain unchanged and tolerated errors are excluded from blocking counts

## 排除范围

- Deploying r16 or networking fixes, taking screenshots, and claiming new lights or prospective hit rates.
