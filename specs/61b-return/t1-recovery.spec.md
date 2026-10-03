spec: task
name: "Evidence-first 61b return command"
inherits: project
---

## 意图

Prepare a disabled one-command recovery entry that collects reconnect evidence, dispatches the original rollback or explicitly approved new-boot baseline replay, verifies U13 identity and HW/ZZ smoke, then releases only the existing cx-t0 lock.

## 已定决策

- Exact serial, journal, plan and source hashes are pinned; default preview runs no external command.
- Collect boot_id, uptime, crash files from the incident interval and available hilog before any restoration.
- Same boot uses the original --rollback parameters. New boot uses existing --restore-baseline with a new journal; the old journal is never rewritten to bypass boot ownership.
- Both branches require321 assertions,319 paths, exact per-board fingerprints, parent/child views and fresh HW/ZZ recovery smoke before UNLOCK.
- Failure records raw stdout/stderr and keeps the lock; subsequent test keys and gate apply are printed, not executed.

## 边界

### 允许修改
- benchmark/2026-10-03-61b-return/**
- specs/61b-return/**
- tools/spec-checks/tests/sixty_one_b_return.rs

## 验收标准

场景: Disabled preview cannot contact devices
  测试: sixty_one_b_return_guards
  假设 The outer execution flag is absent
  当 The recovery entry runs
  那么 It prints exact future commands without external calls or writes

场景: Same and new boots use trusted recovery branches
  测试: sixty_one_b_return_guards
  假设 A mock61b returns valid evidence and the exact journal is active_verified
  当 Recovery runs for either boot identity
  那么 Readonly evidence precedes rollback or baseline replay and both branches require strict final verification

场景: Failure preserves the existing lock
  测试: sixty_one_b_return_guards
  假设 Transport is ambiguous or identity smoke or recovery fails
  当 The entry processes the result
  那么 It archives raw evidence and never invokes UNLOCK

场景: Successful recovery releases only61b
  测试: sixty_one_b_return_guards
  假设321 assertions and both controls pass with unchanged boot and owner
  当 Final verification completes
  那么 It releases the existing cx-t0 lock and prints the pending tests and gate application without executing them

## 排除范围

- Real device execution by this lane, new recovery engine, activation, gate changes, resetting shared infrastructure or declaring screenshots lit.
