spec: task
name: "Seal the demo board"
inherits: project
depends: [t4-stability]
---

## 意图

把演示板封存成以后固定拿来展示的机器:记下完整指纹,写一份照着就能演示的手册和一键恢复脚本,并在仓库规则里把它登记为演示板。

## 已定决策

- 指纹包含 runtime-fingerprint、叠加清单、已装包列表(包名+版本+APK SHA)、系统版本,存进 benchmark 目录。
- 演示手册写:开机后怎么确认就绪、演示顺序、头条怎么操作、某个应用失败时跳过哪个;一键只读自检脚本对比当前指纹与封存指纹。
- 恢复脚本从封存的部署件把板恢复到封存态,先在空闲板上演练一次。
- AGENTS.md 板子纪律加一行:该序列号为演示板,零改动,只读巡检,解封只有用户能批。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-baseline/**
- scripts/lab/demo_selfcheck.sh
- scripts/lab/demo_restore.sh
- AGENTS.md
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Self check matches the sealed fingerprint
  测试: demo_baseline_seal
  假设 The board is sealed and the fingerprint is stored
  当 demo_selfcheck.sh runs read-only
  那么 It reports every component equal to the sealed fingerprint and exits zero and any difference exits nonzero naming the component

场景: Restore is rehearsed on a spare board
  测试: demo_baseline_seal
  假设 A spare board starts from the unified state
  当 demo_restore.sh runs
  那么 The spare board self check matches the sealed fingerprint except its serial and the run log is kept

场景: Self check detects drift
  测试: demo_baseline_seal
  假设 One deployed file differs from the sealed fingerprint
  当 demo_selfcheck.sh runs
  那么 It exits nonzero and prints the path with expected and actual SHA

场景: Demo runbook lists order fallback and Toutiao steps
  测试: demo_baseline_seal
  假设 The runbook is written
  当 It is checked against the final demo list
  那么 Every demo app appears in order each has a skip fallback and the Toutiao and BoatAttack steps are present

## 排除范围

- 修墙、加新应用;封存后对演示板的任何写操作。
