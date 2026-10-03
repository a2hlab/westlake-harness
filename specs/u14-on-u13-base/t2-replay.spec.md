spec: task
name: "Fresh offline U14 executor diagnostics on both U13 bases"
inherits: project
depends: ["t1-binding.spec.md"]
---

## 意图

Run the real master u7_executor dry-run with each matching baseline-native, separately report reachable native/static/image checks and preserve every refusal and exact exit.

## 已定决策

- Do not supply a remote oatdump from this lane; required G2 failure remains a failure for outer replay.
- Executor exit zero never grants deployment: the package remains disabled and promotion is unconfirmed.
- Reports are cold-readable without private artifacts; all runtime artifacts retain persistent paths and hashes.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-on-u13-base/**
- specs/u14-on-u13-base/**
- tools/spec-checks/tests/u14_on_u13_base.rs
- README.md

## 验收标准

场景: Both fresh executor attempts retain their matching baseline
  测试: u14_u13_replay
  假设 Both prepared variants have explicit U13 baseline-native paths
  当 Mac dry-runs and component checks run
  那么 Each command exit and evidence hash is retained with native JAR image increments and no installer replacement

场景: Missing G2 is not converted into production PASS
  测试: u14_u13_replay
  假设 The real executor rejects required G2 because executable oatdump is unavailable
  当 The report is assembled
  那么 The original refusal remains and execution promotion and device access remain false

## 排除范围

- VM or remote probe execution and changes to production gate policy.
