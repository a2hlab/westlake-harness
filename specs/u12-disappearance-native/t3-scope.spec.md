spec: task
name: "Gecko resident compat relocation scope"
inherits: project
depends: [t2-zlib]
---

## 意图

Trace the actual Gecko consumer namespace and coordinate its resident compat scope with cc-wiki without a duplicate owner change.

## 已定决策

- App-domain relocation is not established by a successful resident handle lookup.
- Preserve exact source/ELF identities and distinguish the common namespace constructor from individual ClassLoader instances.
- An unproven scope repair must not be counted as an observed first-fatal movement.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-compat-relocation-scope/**
- tools/spec-checks/tests/u12_compat_scope.rs

## 验收标准

场景: Consumer app scope and failed resident visibility are independently documented
  测试: u12_compat_scope
  假设 Two exact window5 Gecko runs and deployed r3/ANL/compat bytes
  当 PID-bound owner logs, relocation errors and namespace code paths are audited
  那么 Existing successful handle queries remain negative evidence against an inherit-only repair and no parallel namespace patch is published

## 排除范围

- Device experiments, package edits and an unverified global promotion.
