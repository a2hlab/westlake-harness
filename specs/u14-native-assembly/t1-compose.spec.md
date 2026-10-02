spec: task
name: "Single bridge and explicit transaction baseline"
inherits: project
---

## 意图

Prepare a disabled U14 batch skeleton with one bridge change and an independently pinned real transaction base.

## 已定决策

- Verify the selected donor double build bytes and leave all other U13 output bytes intact.
- Rebind runtime/image references and transaction preparation to the supplied signed baseline.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-native-assembly/**
- specs/u14-native-assembly/**
- tools/spec-checks/tests/u14_native_assembly.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Assembly changes only the selected bridge
  测试: u14_native_assembly
  假设 U13 91272eaf and two equal 7daa bridge donors are pinned
  当 The disabled draft is composed
  那么 Only bridge output bytes change and two native plus one JAR slots stay empty

场景: Transaction baseline drift is rejected
  测试: u14_native_assembly
  假设 Assembly base is not necessarily the currently deployed transaction base
  当 A supplied transaction baseline SHA or signed identity disagrees
  那么 Composition refuses instead of borrowing the assembly comparison baseline

## 排除范围

- New component builds, VM replay, device operations and window authorization.
