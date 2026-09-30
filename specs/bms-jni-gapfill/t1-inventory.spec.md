spec: task
name: "Full v3a native inventory and ranked 66-key gaps"
inherits: project
---

## 意图

Give the gapfill implementer an exact class/name/descriptor worklist instead of repairing one observed native method at a time.

## 已定决策

- Enumerate all framework JAR native declarations in the pinned v3a package and retain full descriptor identities.
- Reuse existing compiled ELF/source registration attribution; augment it with completed r16/r17a log registration and missing-native evidence, preserving generation and evidence strength.
- Intersect bounded application startup paths and framework Java calls with native methods; rank by unique affected app keys, separately report all-code references and observed failures.
- Strict machine-readable inventory plus explicit exceptions; automatically generated no-path exceptions remain draft because callback/reflection coverage is incomplete.

## 边界

### 允许修改
- benchmark/2026-09-30-framework-jni-gaps/**
- specs/bms-jni-gapfill/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No edits to previous frozen scans, input APK/JAR/ELF files, runtime implementation or board state.

## 验收标准

场景: 精确标识与保守差集
  测试: framework_jni_gap_rules
  假设 Overloaded declarations, registration attempts and explicit missing-native logs exist
  当 The evidence join and strict gate classify them
  那么 Methods remain distinct by full descriptor and log attempts alone are not success
  并且 Unknown or missing methods fail unless covered by a valid approved exception

场景: 全量声明与应用覆盖
  测试: framework_jni_gap_inventory
  假设 v3a framework JARs and 66 application keys are supplied
  当 The offline scan produces the inventory and worklist
  那么 Each unique native declaration appears with exact identity and evidence
  并且 All 66 keys have explicit scanned or unknown coverage and no-path is never labeled proven unreachable

## 排除范围

- Providing stubs or JNI implementation, validating runtime behavior and claiming screens are lit.
