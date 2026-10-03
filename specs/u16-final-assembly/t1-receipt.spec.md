spec: task
name: "U16 completed pair verification"
inherits: project
---

## 意图

Bind actual two-run outputs and complete compiler logs to the nine frozen inputs. Assemble a disabled U16 content candidate while leaving object-chain exception and remote G2 pending.

## 已定决策

- Verify every sealed inventory entry, actual compiler argv, compiler/tee/session statuses and exact frozen tool hashes.
- Select run1; strict reproduction is26/27 with boot.art differing only inside the known field, not yet an approved exception.
- U16 composition contains runtime1d42, Fluttereb90, stubs8593, runtime JARf6f5 and27 selected images; all other bytes stay U15.
- Keep transaction and rollout disabled; run local G1/RB/T4B and provide guarded outer-only G2/object-chain replay commands.

## 边界

### 允许修改
- benchmark/2026-10-03-u16-final-assembly/**
- specs/u16-final-assembly/**
- tools/spec-checks/tests/u16_final_assembly.rs

## 验收标准

场景: Actual two-run receipt covers nine inputs and27 outputs
  测试: u16_final_assembly_receipt
  假设 Returned build receipts contain complete actual argv and all compiler/tee statuses0
  当 The receipt invariants are checked
  那么 Both runs bind9 inputs and27 outputs while pair approval remains pending

场景: Missing output or failed tee cannot be selected
  测试: u16_final_assembly_receipt
  假设 An output is absent or one recorded tee status is nonzero
  当 Receipt verification runs
  那么 It raises an error rather than borrowing a completed run

场景: Unexpected byte delta is not a historical exception
  测试: u16_final_assembly_receipt
  假设 A changed byte lies outside0x3e3b8 through0x3e3bf
  当 The two-run difference validator runs
  那么 It rejects and leaves exception approval false

场景: Disabled package and replay do not touch a device
  测试: u16_final_assembly_receipt
  假设 No outer replay authorization is supplied
  当 The replay entry is invoked
  那么 It exits78 before remote access and all candidate rollout flags remain false

## 排除范围

- Applying registry exceptions, approving new classes, remote execution or promotion.
