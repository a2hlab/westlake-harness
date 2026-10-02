spec: task
name: "Compose the Flutter ATrace slot into U15 native"
inherits: project
---

## 意图

Create a new immutable native partial using runtime94c3, host9e3a, ANL b96a dual aliases and Flutter-private libandroid9b824.

## 已定决策

- Exactly five payload replacements against U14: runtime, host, both ANL aliases and only westlake_flutter/libandroid.
- Hash-check persistent two-build donors and their final compiled sources; no source or build is invented.
- Framework9e55 and stubs94a9 plus 27 images remain the separate unexecuted BCP v2 plan; no bundle descriptor is emitted.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-native-v2/**
- specs/u15-native-v2/**
- tools/spec-checks/tests/u15_native_v2.rs

## 验收标准

场景: Five exact replacements preserve aliases and isolation
  测试: u15_native_v2_composition
  假设 Four persistent donor objects have full identities and two equal builds each
  当 The native partial composition is validated
  那么 Exactly five files change with both ANL aliases and no native-domain libandroid modification

场景: Partial bundle and implicit promotion are rejected
  测试: u15_native_v2_composition
  假设 New BCP images and signed transaction baselines are absent
  当 A bundle descriptor or execution flag or implicit baseline is supplied
  那么 Validation rejects it without claiming deployment readiness

## 排除范围

- Modify native sources, execute builds or assemble a complete production bundle.

