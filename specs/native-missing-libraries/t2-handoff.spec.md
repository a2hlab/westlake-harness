spec: task
name: "Prepare source-bound native repairs and distinguishing window predicates"
inherits: project
depends: [t1-evidence]
---

## 意图

Provide source-bound integration patches for private zlib availability, a typed OpenSLES real-owner facade and the exact MediaPlayer system-library mapping, with host regression checks and an offline precheck fragment.

## 已定决策

- OpenSLES forwards the real backend's typed engine entry and exact interface pointers; an unbound facade fails instead of claiming success.
- The media_jni system mapping points at the existing registered runtime; app callers and realpath escapes retain rejection.
- The precheck fragment includes distinct expect.confirm and expect.refute observations and is not an authorized board plan.

## 边界

### 允许修改
- benchmark/2026-10-01-native-missing-libraries/**
- specs/native-missing-libraries/**
- tools/spec-checks/tests/native_missing_libraries.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Typed engine forwarding preserves arguments and return status
  测试: native_missing_library_handoff
  假设 A bound real backend and its standard interface pointers
  当 The facade engine entry is invoked
  那么 All six arguments and backend status are preserved and the Android queue aliases the backend queue

场景: Missing backend and conflicting rebinding fail
  测试: native_missing_library_handoff
  假设 An unbound facade or a backend missing an interface
  当 Binding or engine creation is attempted
  那么 Failure is explicit and no fabricated engine object is returned

场景: Manifest routing preserves loader isolation
  测试: native_missing_library_policy
  假设 Trusted framework and untrusted app callers and a realpath redirect
  当 The actual patched SystemLoader implementation executes
  那么 Only the trusted media_jni request opens the exact existing runtime owner and the negative routes stay rejected

场景: Precheck has discriminating outcomes and no deployment authority
  测试: native_missing_library_handoff
  假设 The three independent repair hypotheses
  当 The handoff precheck is inspected
  那么 Each has unequal confirm and refute observations and missing native gate or build evidence forbids opening a window

## 排除范围

- Building the final native generation, exceptions approval, window execution or screenshot signoff.
