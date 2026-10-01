spec: task
name: "Resolve U8 native first-fatal callsites and operands offline"
inherits: project
depends: [t1-inventory, t2-consumers]
---

## 意图

Identify the field ID consumed at the exact glmark2 crash callsite and the object operand dereferenced at the ath0-rpn Skia PC without assuming a missing stack frame or a null pointer.

## 已定决策

- Bind APK member/provider/Skia identities and selected U8 hilog SHA before disassembly.
- Preserve tail-call semantics, complete callsite evidence and the nonzero invalid operand; unresolved namespace or prior-write causality remains unknown.

## 边界

### 允许修改
- benchmark/2026-10-01-b10-registration-impact/**
- specs/b10-registration-impact/**
- tools/spec-checks/tests/b10_registration_impact.rs

## 验收标准

场景: Exact callsites retain the field and tail-call boundary
  测试: b10_registration_first_fatal
  假设 SHA-bound APK and provider callsite evidence
  当 The callsite and machine evidence are checked
  那么 AssetManager mObject is retained without declaring the Java field absent or choosing an unobserved cache owner

场景: Invalid nonzero object is not relabeled null
  测试: b10_registration_first_fatal
  假设 A matching fault address and captured nonzero resource and vtable operands
  当 Operand consistency and artifact hashes are validated
  那么 Nonzero invalid pointer remains distinct from null and mismatched addresses or bytes are refused

## 排除范围

- Device operations, memory modification, binary patching and unobserved allocation/free/write attribution.
