spec: task
name: "Freeze paired r17o r17p forecasts"
inherits: project
depends: [t2-v3c-r17j]
---

## 意图

Freeze 66 per-key forecasts for each of two exact JAR variants before reading the next full sweep. Preserve prior v2 outcomes, disclosed targeted-test exposure, and independently testable progress checkpoints.

## 已定决策

- Pin v3c 668e4f7c, libhwui a578b949, 5ea installer 6aadb8b4/7048c7c5, and full r17o/r17p JAR hashes.
- Reuse B10 v2 feedback; static references are conditional requirements, EGL remains runtime-only, and no library presence implies app-domain visibility.
- Disclose r17o targeted outcomes already read on the board; no r17p outcome or upcoming full-sweep result is input to the freeze.
- Score exact labels, minimum promise, coverage, confusion and an always-unchanged baseline by actual JAR and prior exposure. No best-of-two-column selection.

## 边界

### 允许修改
- benchmark/2026-09-30-r17op-prospective/**
- specs/bms-background-start/t3-r17op.spec.md
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No board I/O, git writes, or changes to prior freezes/backtests. No new full-sweep outcomes before freezing.

## 验收标准

场景: 双列冻结完整
  测试: r17op_freeze
  假设 Sixty-six pinned APK identities and two JAR hashes exist
  当 The paired forecast is frozen once
  那么 The emitted CSV and JSON each contain 66 rows with a valid label in each column, reason, prior evidence and named checkpoint
  并且 The receipt pins the profiles, code, scanner outputs and disclosed prior exposure

场景: 错误运行件或提前点击拒绝
  测试: r17op_scoring
  假设 A run uses the other JAR, old libhwui, a changed APK or a pre-freeze click
  当 The scoring gate evaluates the run
  那么 It excludes the mismatched observations and never selects whichever forecast scored better
  并且 Survival alone remains insufficient for UI and unknown labels abstain

## 排除范围

- Runtime repairs, deployments, and screenshots or outcomes from the upcoming full sweep before freeze.
