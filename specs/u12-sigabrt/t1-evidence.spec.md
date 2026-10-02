spec: task
name: "Eight candidate aborts and donor repair predictions"
inherits: project
---

## 意图

Replace the SIGABRT family label with termination-bound converter or native loader causes and conditional donor repair predictions.

## 已定决策

- App caller disassembly must establish converter use independently for each key.
- Missing crash files or abort text remain unavailable rather than reconstructed as an observed message.
- A failure stub or historical ledger is not a current unlock.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-sigabrt/**
- tools/spec-checks/tests/u12_sigabrt.rs

## 验收标准

场景: Real candidate sources are grouped by their observed termination cause
  测试: u12_sigabrt_evidence
  假设 Eight pinned candidate logs and corresponding native caller libraries
  当 Read only extraction and caller disassembly are checked
  那么 Seven converter call sites and one media loader chain retain evidence and unknowns without fabricated completion or lighting

## 排除范围

- No native modification and no window authorization.
