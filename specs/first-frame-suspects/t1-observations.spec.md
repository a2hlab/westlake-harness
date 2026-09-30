spec: task
name: "Extract scoped graphics observations from retained runs"
inherits: project
---

## 意图

Count present VSync and finishDrawing events per verified app PID, while separating unrelated system traffic and non-executed method names, and use first_fatal for termination exclusion.

## 已定决策

- Bind app PID through package launch and process receipts; require capture time and log completeness.
- Keep raw counts and exact examples; absence of an observable marker is unknown, not proof of no presented frame.
- Preserve post-capture fatal events as separate observations and do not backdate them.

## 边界

### 允许修改
- benchmark/2026-10-01-first-frame-suspects/**
- scripts/lab/scan_first_frame.py
- specs/first-frame-suspects/**
- tools/spec-checks/tests/first_frame.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: PID and time bounds exclude foreign and late rendering traffic
  测试: first_frame_scope
  假设 App events mixed with compositor traffic registration strings and post-capture events
  当 The graphics observation extractor runs
  那么 Counts include only the verified app execution interval and missing attribution remains unknown

场景: Termination excludes a blank run without deleting negative evidence
  测试: first_frame_terminal
  假设 A blank screenshot with a pre-capture termination or a later termination
  当 The retained first_fatal result is applied
  那么 The pre-capture termination excludes suspicion and the later event stays separate without rewriting the capture

## 排除范围

- Device traces, source patches to graphics owners and automatic root-cause attribution.
