spec: task
name: "B10 task85 five static wall families and frozen r14 backtest"
inherits: project
depends: [t2-class-presence]
---

## 意图

Within one hour, scan the existing 32 APK identities for five newly observed wall families and merge them into a versioned prediction table before reading undisclosed r14 results.

## 已定决策

- Five families: window type/flags, in-app bindService, VelocityTracker JNI, native bionic imports/ELF headers, SharedPreferences null contract.
- Reuse bounded startup graph and exact APK hashes; references alone do not prove runtime failure.
- Freeze detector/source/input/prediction hashes before reading r14 triage. Board-disclosed 18 apps are seed observations, not held-out hits.
- Distinguish valid ELF headers from runtime dlopen header failure, unresolved JNI from missing JNI, and own-app service targets from unknown targets.
- Publish a full 32 by 5 hit matrix including no-static-evidence and unknowns; preserve older prediction files.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/**
- tools/spec-checks/**
- specs/bms-static-v3/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No device operations, runtime changes, writes to APK/source input trees or git metadata.
- Do not inspect remaining r14 outcomes until the detector and prediction file are frozen.

## 验收标准

场景: 五族检测有正反例与不确定性边界
  测试: b85_static_rules
  假设 Synthetic DEX instructions and ELF imports include positive, absent and ambiguous cases
  当 Five static detectors inspect the inputs
  那么 Constants and own-service evidence are distinguished from generic references
  并且 Valid headers and weak imports are not reported as definite missing implementations

场景: 三十二APK全覆盖并冻结预测
  测试: b85_prediction_freeze
  假设 The pinned 32 APK cohort and prior class prediction table exist
  当 The scanner emits the hit matrix and merged predictions
  那么 Every app has five family verdicts and source/APK hashes in a frozen receipt
  并且 The scanner has no access to observed triage input

场景: 回测隔离已知样本与未看结果样本
  测试: b85_backtest_partition
  假设 Frozen predictions and subsequently read r14 observations are available
  当 Matching uses APK identity and family labels
  那么 Known seed cases, held-out cases, unmatched identities and unclassified observations have separate denominators
  并且 Nonfatal observed warnings do not become first-fatal successes

## 排除范围

- Runtime loader, namespace, signal, rendering or service implementation fixes.
- Treating a held-out retrospective evaluation as a prediction frozen before device execution.
