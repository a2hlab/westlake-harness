spec: task
name: "Forward Android-width OpenSLES to the real OH owner"
inherits: project
depends: [t2-visibility-policy]
---

## 意图

Implement the remaining U10 OpenSLES facade after the matching OH implementation is available. The verified ELF uses twenty-four-byte IIDs and eight-byte scalar outputs, so direct vtable casts are forbidden. This task is pending, not an accepted delivery.

## 已定决策

- Use the actual OH engine; never provide an always-failure slCreateEngine substitute or load a second private audio engine.
- Convert Android-width arrays, PCM/locator structures and outputs; rebind IID pointers, wrap interface vtables and callback lifetimes.
- Preserve owner results and capabilities; do not invent Android configuration support absent in OH.
- Pin source, toolchain and compiled artifacts; repeat ABI, call and native closure gates on the assembled batch.

## 边界

### 允许修改
- benchmark/2026-10-01-u10-native-shims/**
- specs/u10-native-shims/**
- tools/spec-checks/tests/u10_native_shims.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Real OpenSLES owner receives engine requests through converted interfaces
  测试: u10_opensles_real_forwarding
  假设 Verified OH owner and a callable backend fixture with distinct Android and OH widths
  当 The facade creates an engine and calls object, player and queue interfaces
  那么 Input values and backend results are preserved, outputs do not overwrite caller canaries, callbacks use the Android signature and IID requests reach the actual owner pointer

场景: Wrong or unavailable owner is not disguised
  测试: u10_opensles_real_forwarding
  假设 Missing or mismatched owner identity
  当 Facade admission and dispatch are attempted
  那么 Admission refuses with explicit evidence and no second engine or canned-failure stub is installed

## 排除范围

- Board authorization, audio/UI acceptance without real execution, Android capabilities the real OH owner does not implement, shipping the incompatible V1 facade.
