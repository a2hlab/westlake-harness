spec: task
name: "Audit the actual 5ea profile and score the unchanged v2 forecast"
inherits: project
depends: [t2-v3c-r17j]
---

## 意图

Apply the user's execution-board correction without rewriting the forecast. Audit run-local fingerprints and installer evidence before scoring the completed 5ea sweep.

## 已定决策

- The authorized amendment adds 5ea; it changes no prediction, timestamp, artifact hash or success definition in v2.
- Derive observed runtime identity from facts.txt's first RUNTIME line and runtime-fingerprint.txt readback, including its no-trailing-newline short-hash convention.
- Require installer readback and per-app APK, grant, actual launcher and post-freeze launch evidence. Missing inputs remain explicitly unknown.
- Count captures from record.json and live app processes from UID-matched process tables, excluding shell helpers; these counts are not UI verdicts.

## 边界

### 允许修改
- benchmark/2026-09-30-v3c-r17j-prospective/**
- specs/bms-background-start/t3-5ea-backtest.spec.md
- tools/spec-checks/src/lib.rs
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- Do not alter freezes/v2/** or prior prediction freezes. No board I/O or run-source writes.

## 验收标准

场景: 执行板更正与实际身份
  测试: v3c_5ea_profile
  假设 The user has authorized 5ea and consistent run-local component readback is available
  当 The amended scorer checks the run
  那么 The 5ea execution board is accepted with the same frozen artifact expectations
  并且 Runtime and installer evidence is reported with paths and hashes

场景: 指纹或权限缺失拒绝
  测试: v3c_5ea_rejection
  假设 The facts fingerprint, a runtime alias, installer hash or per-app grant evidence is missing or inconsistent
  当 The auditor checks eligibility
  那么 The affected observation is excluded with a concrete reason
  并且 Process liveness and absent errors never establish a screenshot or progress verdict

## 排除范围

- Installing or repairing runtime components and modifying the producer's run artifacts.
