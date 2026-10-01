spec: task
name: "Scan PID-bound session and buffer-queue evidence"
inherits: project
---

## 意图

Produce the sixty-six-row impact table with original event lines and three signed-bright single-session negative controls.

## 已定决策

- Apply the prewritten CRITERIA.md before collecting the full cohort.
- Reuse first_fatal app PID binding and the accepted scoring interval and source pins.
- Separate successful session creation, last-session writes, BBQ lookup failures and empty surfaces; never count method inventories as executed events.
- Compare null session to then-last session, not final session; preserve unknown Activity foreground identity.
- Include the outer 08:00 extension: unknown-session and GLSurfaceView valid-Surface IAE counts remain separate, including single-session apps and successful later creation.
- CLI collection emits JSON to stdout and reads raw logs only; rendering consumes pinned extracted evidence without requiring devices.

## 边界

### 允许修改
- benchmark/2026-10-01-last-session-scan/**
- specs/last-session-scan/**
- tools/spec-checks/tests/last_session_scan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: PID and queue correlation excludes foreign and reflected events
  测试: last_session_parser
  假设 Interleaved app foreign-PID and duplicate log events with multiple queues
  当 The scanner correlates creation update and empty surface observations
  那么 Only target executions are counted and each queue retains its own Activity and session with unknowns explicit

场景: Impact classification does not invent foreground or lighting
  测试: last_session_impact
  假设 Foreground null background-only null single-session and unknown foreground examples
  当 The frozen criteria classify the evidence
  那么 Foreground failure is a candidate background-only failure is not a blocker and unknown is not negative

场景: Complete signed cohort and three negative controls reproduce
  测试: last_session_cohort
  假设 Pinned evidence for all sixty-six signed U7 keys
  当 The report is rebuilt from the evidence
  那么 All signed states and source hashes remain bound and three bright single-session controls have zero null

## 排除范围

- New image judgments, changing existing selectors, and native implementation work.
