spec: task
name: "Recover eleven U8 no-first-fatal termination chains"
inherits: project
---

## 意图

Audit the eleven assigned U8 keys against original hilog, fault inventories and process snapshots. Produce grouped termination evidence with file hashes and one-based line numbers, distinguishing observed exit mechanisms from unknown underlying causes.

## 已定决策

- Separate APPSPAWN wait results, System.exit, native assertions and manager death notifications.
- Reuse first_fatal.py for existing Java exception chains; do not modify frozen scoring.
- Emit the eleven-key audit as JSON and English Markdown with an additive landing manifest.

## 边界

### 允许修改
- benchmark/2026-10-01-u8-death-clusters/no-fatal-*
- benchmark/2026-10-01-u8-death-clusters/no-fatal-tests/**
- benchmark/2026-10-01-u8-death-clusters/no-fatal-evidence/**
- scripts/lab/termination_events.py
- specs/u8-no-fatal-terminations/**
- tools/spec-checks/tests/u8_no_fatal_terminations.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: System emitter events remain victim bound
  测试: u8_termination_matching
  假设 Manager logs containing target and unrelated victim PIDs
  当 The termination matcher classifies APPSPAWN, memory kill and scheduler records
  那么 Only exact target identities match and notifications do not become killing causes

场景: Exit mechanisms are not confused with handled signals
  测试: u8_termination_matching
  假设 System.exit, hwui abort, handled signal and watchdog warning fixtures
  当 The matcher assigns event roles
  那么 Exit and abort are terminal while handled signals and warning-only ANR are not terminal

场景: Eleven-key evidence is replayable
  测试: u8_termination_report
  假设 The eleven formal U8 records and their original evidence
  当 The audit JSON and Markdown are validated
  那么 Eleven unique keys have hashed sources and line-bound termination evidence and uncertainty remains explicit

## 排除范围

- Native/JAR fixes, new screenshots, deployment acceptance and identifying a SIGKILL sender without evidence.
