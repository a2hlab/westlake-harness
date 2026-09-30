spec: task
name: "Describe completed 61b r17p sweep against accepted 5ea v2"
inherits: project
depends: [t4-execution-revision]
---

## 意图

Describe all 66 keys in the completed 61b r17p sweep using actual fingerprints, records and PID-attributed logs. Compare installed background permission and launcher selection against accepted 5ea v2 without attributing simultaneous board/JAR/protocol changes solely to the installer.

## 已定决策

- This is retrospective descriptive analysis, not a new forecast or frozen-profile score. Preserve all prior freezes and auditors.
- Reuse profile_audit and record_facts. Require terminal summary coverage before publishing final data; explicit partial snapshots remain partial.
- Screenshot verdicts stay pending outer review. Process survival, captures and first observed errors are independent fields.
- Installer mechanisms are grant/launcher differences with direct evidence; mixed-profile outcome differences are confounded, not causal estimates.

## 边界

### 允许修改
- benchmark/2026-09-30-r17p-61b-comparison/**
- specs/bms-background-start/t5-r17p-61b-description.spec.md
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No device I/O, writes to source runs, edits to accepted forecasts, or new same-profile accuracy claims.

## 验收标准

场景: 完整记录与安装器机制对照
  测试: r17p_description_rules
  假设 Completed records contain actual grants, launchers and exact app process tables
  当 The descriptive comparison reads each record
  那么 It counts captured=true screenshots and excludes same-UID shell helpers
  并且 It distinguishes absent permission from missing evidence and labels mixed-profile installer effects confounded

场景: 缺失数据与跨进程日志拒绝
  测试: r17p_description_rejection
  假设 A run is unfinished or log errors come from unrelated PIDs
  当 The report validates completeness and extracts app evidence
  那么 It rejects final publication of an unfinished run and excludes unrelated process errors
  并且 No survival or log-only evidence becomes a lighting verdict

场景: 外环截图签认
  测试: r17p_description_handoff
  审核: human
  假设 All 66 per-key rows and hash-verified capture references are available
  当 The outer loop reads the screenshots
  那么 Visual verdicts require explicit outer acceptance and are not inferred by the machine report

## 排除范围

- Installer intervention, board reruns, same-profile accuracy and final lighting acceptance.
