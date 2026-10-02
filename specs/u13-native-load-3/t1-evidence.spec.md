spec: task
name: "PID-scoped loading chains and ELF inventory"
inherits: project
---

## 意图

Recover the exact dependency or relocation errors behind the three window5 terminal exceptions and compare every selected consumer NEEDED and strong UND entry to pinned provider inventories.

## 已定决策

- Extract the terminal PID before collecting context.
- Record SoLoader recovery separately from the terminal root.
- Keep observed namespace names separate from source-derived route predictions.

## 边界

### 允许修改
- benchmark/2026-10-02-u13-native-load-3/**
- specs/u13-native-load-3/**
- tools/spec-checks/tests/u13_native_load_3.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Original app-PID errors survive context selection
  测试: u13_native_load_3_evidence
  假设 Window5 logs contain unrelated linker noise
  当 Context is collected for the terminal PID
  那么 Every retained row has that PID and its original line number

场景: The three consumer identities are pinned
  测试: u13_native_load_3_evidence
  假设 Native assembly receipts identify deployed app members
  当 ELF metadata is extracted
  那么 SHA mismatch is rejected and NEEDED plus strong UND rows are preserved

## 排除范围

- Provider loading experiments or source changes to native libraries.
