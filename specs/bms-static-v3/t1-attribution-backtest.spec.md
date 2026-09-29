spec: task
name: "B10 v3 JNI registration ownership and fatal-wall backtest"
inherits: project
tags: [bms, offline, cx-bms]
---

## 意图

Attribute compiled JNI tables using AOSP registration source, then add bounded dlopen, Koin, WorkManager and attach risk rules. Backtest #75 and available #78 evidence without using known fatal text as a static prediction input.

## 已定决策

- Resolve table ownership through explicit registration call/class constants; ambiguous ownership stays unknown.
- Require exact name/descriptor/function and compiled source evidence in the packaged ELF before registered.
- Pin source hashes and scanner dependencies in cache validity; preserve six existing known JNI answers and outer-approved exceptions.
- Emit separate observed fatal, caught first exception, static risk and profile/input eligibility fields.
- Preserve pre-v3 predictions for honest before/after scoring and #78 frozen prediction comparison; missing observations do not count as passes.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/**
- scripts/lab/jni_gate.py
- tools/spec-checks/**
- specs/bms-static-v3/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No device command, installation, runtime source modification or deployment.
- No write to external input trees or git metadata; outer lane commits.

## 验收标准

场景: 注册表归属与包内证据同时成立才计覆盖
  测试: b10_v3_registration_ownership
  假设 Source tables contain multiple classes and overloaded methods
  当 The scanner joins tables to packaged native pointers and compiled source files
  那么 Correct class and descriptor are attributed and missing or ambiguous evidence stays unknown
  并且 The six prior JNI known answers remain correct

场景: 门禁缓存覆盖新依赖且认可例外不丢失
  测试: b10_v3_cache_and_exceptions
  假设 Outer-approved exceptions and a generated matrix exist
  当 A scanner dependency or attribution source changes
  那么 The cached matrix is rejected
  并且 Uncovered entries still block and approved exceptions retain their identity

场景: 新墙预测不读取致命日志作为输入
  测试: b10_v3_risk_rules
  假设 APK manifest, DEX call paths and packaged ELF dependencies are available
  当 Rules scan namespace load paths and initialization dependencies
  那么 Machine-readable risk rows cover dlopen, Koin, WorkManager and attach with evidence and uncertainty
  并且 Service stub policy remains separate from needs-real paths

场景: 回测区分伴随异常与致命异常及前瞻边界
  测试: b10_v3_fatal_backtest
  假设 The twelve p73-fatal observations and any available task 78 results are supplied
  当 The backtest compares frozen and updated predictions
  那么 Caught theme sync errors do not replace final fatal causes
  并且 Numerators, denominators, unknowns and unmatched APK or generation cases are explicit

## 排除范围

- Proving runtime namespace resolution or initialization success from static risk presence.
- Deploying fixes, claiming screenshots or live-process totals, or silently approving new exceptions.
