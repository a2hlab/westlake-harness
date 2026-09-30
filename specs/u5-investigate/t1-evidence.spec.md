spec: task
name: "Collect PID-bound blank-screen evidence"
inherits: project
---

## 意图

Continue cc-t3's paused investigation using the selected U5 records and outer-reviewed images. Filter by verified numeric application PID, identify the dedicated ActivityThread TID and preserve original log line numbers.

## 已定决策

- Parse date and time before PID and TID; never use positional split index 1 as PID.
- Distinguish dedicated Java ActivityThread from the process leader and keep each process separate.
- Select alive white or desktop keys from the 66-key first scheduled U5 cohort; retain exclusion reasons.

## 边界

### 允许修改
- benchmark/2026-10-01-u5-investigate/**
- specs/u5-investigate/**
- tools/spec-checks/tests/u5_investigate.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: PID and Java main-thread evidence stays application scoped
  测试: investigate_pid_scope
  假设 Mixed compositor and application logs with a dedicated Java thread
  当 The parser collects relevant evidence
  那么 Only numeric target PIDs enter app evidence and the Java thread differs from the process leader

场景: Cohort excludes lit dead fatal and black-screen controls
  测试: investigate_cohort
  假设 All 66 selected U5 records and visual labels
  当 The blank-screen cohort is reproduced
  那么 Eligibility is explicit and a surviving parent cannot hide another target process fatal

## 排除范围

- Device collection, guessing stacks from silence, changing original screenshots or predictions.
