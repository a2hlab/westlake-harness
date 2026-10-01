spec: task
name: "Scan 166 APKs and rank evidence-bound theme and graphics constructor risks"
inherits: project
---

## 意图

Scan all DEX and Activity theme resources, separate launcher lifecycle actionbar use from later Activity use, and rank graphics constructor callsites against identity-verified native implementations.

## 已定决策

- Pin old apps.json and frozen U7 APK identities plus corpus-v2 inputs and signed U7/cv2 visual labels.
- Retain whole-DEX exact API callsites and bounded lifecycle call paths, including inherited app methods; non-reached is not proved post-frame execution.
- Resolve local style parents and explicitly distinguish AppCompat windowActionBar from the Android attribute; variant ambiguity and external parents stay unknown.
- Inspect compiled constructor bodies and their direct callees; report unconditional throw, conditional throw, no direct throw witness and unresolved separately.
- Include MaskFilter, PathEffect, Shader/Gradient and adjacent ColorFilter families; exclude destructors/finalizers/update APIs from construction counts.
- Publish all 166 rows, sorted risk clusters, known fatal calibrations, negative controls and exact landing/documentation lists.

## 边界

### 允许修改
- benchmark/2026-10-01-b10-theme-graphics/**
- specs/b10-theme-graphics/**
- tools/spec-checks/tests/b10_theme_graphics.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Cohort and deployed artifact drift are refused
  测试: b10_theme_graphics_identity
  假设 Changed APK hashes missing keys or native bytes not matching U7
  当 The offline collector admits inputs
  那么 It rejects drift instead of producing a complete prediction

场景: Actionbar theme and lifecycle tiers remain distinct
  测试: b10_theme_graphics_actionbar
  假设 Inherited startup calls later Activity calls and themes with qualified variants
  当 Theme and exact-call graph classification runs
  那么 Calls have DEX and resource witnesses with honest timing and namespace ambiguity

场景: Graphics registrations and throw paths are classified conservatively
  测试: b10_theme_graphics_native
  假设 A registered Emboss constructor an argument-dependent throw and unresolved source ownership
  当 Compiled implementation evidence and consumer callsites are evaluated
  那么 Unconditional throw differs from possible throw and unknown JNI ownership is never promoted to registered

场景: Complete ranked predictions replay
  测试: b10_theme_graphics_replay
  假设 One hundred sixty six input identities static facts and signed calibration labels
  当 Machine-readable predictions and summaries are regenerated
  那么 All rows and unique-key counts reproduce without changing any previous freeze

## 排除范围

- Runtime fixes, device tests, proving every later Activity is reachable, or claiming a screenshot-positive app cannot fail after its first screen.
