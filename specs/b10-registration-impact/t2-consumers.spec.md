spec: task
name: "Scan native consumers across the exact 166 APK cohort"
inherits: project
depends: [t1-inventory]
---

## 意图

Scan all in-APK and current SHA-pinned sidecar libraries, separate ELF imports from literal lookup strings, and rank the native API consumer groups without an invented unlock count.

## 已定决策

- APK/package and sidecar SHA mismatches refuse; each processed member keeps its own identity.
- Non-AArch64 and malformed ELF members remain explicit exclusions or uncertainty, not clean providers.
- Strong imports, weak imports and exact NUL-terminated lookup strings are distinct evidence.

## 边界

### 允许修改
- benchmark/2026-10-01-b10-registration-impact/**
- specs/b10-registration-impact/**
- tools/spec-checks/tests/b10_registration_impact.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Imports and lookup strings do not become executed calls
  测试: b10_registration_consumers
  假设 A native member with strong and weak imports exact lookup strings and an irrelevant substring
  当 Native API exposure is classified
  那么 Evidence kinds and exact symbol names stay separate and no execution or fatal verdict is inferred

场景: Input drift and unsupported ABI are handled honestly
  测试: b10_registration_inputs
  假设 A changed sidecar and a non-AArch64 member
  当 Member identity and ELF admission run
  那么 The changed member is rejected and the unsupported ABI is not counted as a valid AArch64 provider

## 排除范围

- Running the apps, resolving actual runtime namespace owners, and interpreting screenshots without outer signoff.
