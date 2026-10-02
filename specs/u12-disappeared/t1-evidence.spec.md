spec: task
name: "Six disappearance causes and conditional repairs"
inherits: project
---

## 意图

Recover process termination status and distinguish proven application failure chains from unobserved kill or exit callers.

## 已定决策

- Use PID-filtered app errors and package/PID-bound APPSPAWN status rather than global error grep.
- Include both VLC process attempts without merging their contexts.
- Repair predictions require the observed wall to move; no screenshot or new-light claim is authorized.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-disappeared/**
- tools/spec-checks/tests/u12_disappeared.rs

## 验收标准

场景: Six original disappearance records retain status and causal uncertainty
  测试: u12_disappeared_evidence
  假设 Six pinned original runs and PID-filtered evidence
  当 Extraction rules and delivered portable evidence are checked
  那么 Exit codes and signals are distinguished from cleanup and missing fault evidence while repairs preserve unknown next failures

## 排除范围

- Native implementation, device operations and modifying deployed bundles.
