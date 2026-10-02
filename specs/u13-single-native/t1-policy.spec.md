spec: task
name: "Resident media alias on the U12 policy"
inherits: project
---

## 意图

Compose the reviewed media_jni resident-only alias with the actual U12 policy without losing SoundPool or mediandk. Reject alternate owner aliases and unavailable resident handles rather than creating a second runtime.

## 已定决策

- Add exactly one system library tuple for libmedia_jni.so and the existing runtime path.
- Reuse reviewed RTLD_NOLOAD selection and exact-tuple verification.
- Keep the seven shared SONAMEs unchanged.

## 边界

### 允许修改
- benchmark/2026-10-02-u13-single-native/**
- tools/spec-checks/tests/u13_single_native.rs
- specs/u13-single-native/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: The single media alias composes with U12
  测试: u13_single_native_policy
  假设 The six U12 system entries and seven shared SONAMEs
  当 The reviewed media alias is appended
  那么 The old entries remain byte-equivalent and media uses RTLD_NOLOAD

场景: An alternate alias is rejected
  测试: u13_single_native_policy
  假设 A manifest entry redirects another SONAME to the runtime
  当 The policy verifier executes
  那么 Verification returns nonzero

场景: A missing resident owner is not reopened
  测试: u13_single_native_policy
  假设 The resident owner is unavailable
  当 SystemLoader opens media_jni
  那么 The operation returns no handle and keeps RTLD_NOLOAD

## 排除范围

- Media decoding, owner publication and new runtime/JAR changes.
