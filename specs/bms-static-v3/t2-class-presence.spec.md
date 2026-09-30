spec: task
name: "B10 v3 boot class presence and service interface risks"
inherits: project
depends: [t1-attribution-backtest]
---

## 意图

Predict missing framework definitions in Wikipedia first, then the requested app cohort, using only APK DEX and pinned v3a/r13 jars.

## 已定决策

- Replace the baseline runtime jar with r13 in the scanned set; do not union two generations of that jar.
- Count DEX class definitions, never type references or class-name strings, as presence.
- Keep definition presence separate from runtime load success and bounded startup reachability.
- Extract service interface requirements from actual r13 bytecode and preserve file/line evidence.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/**
- tools/spec-checks/**
- specs/bms-static-v3/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No device operations, runtime changes or writes to input trees.
- No guessing missing app identity or declaring static references executed.

## 验收标准

场景: 类定义和服务接口已知答案
  测试: b10_v3_class_presence
  假设 Pinned v3a jars and r13 overlay plus Wikipedia APK are available
  当 The scanner compares direct references and service interface prerequisites with DEX definitions
  那么 android.net.IConnectivityManager is absent while android.app.Activity is present
  并且 A reference-only fixture cannot satisfy class presence

场景: 启动路径与覆盖边界
  测试: b10_v3_class_reachability
  假设 Manifest roots, bounded method paths and a declared app cohort exist
  当 Class and service risks are emitted
  那么 Reachable paths have evidence and unresolved paths remain unknown
  并且 Missing inputs and duplicate cohort identities are explicitly counted

## 排除范围

- Proving class initialization, runtime loader order, branch execution or screenshots.
