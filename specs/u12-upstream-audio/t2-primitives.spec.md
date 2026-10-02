spec: task
name: "U12 IID and continuous-queue primitives"
inherits: project
depends: [t1-architecture]
---

## 意图

Transplant identifier conversion and refill-loop behavior while retaining actual unsupported PLAY as an explicit negative control.

## 已定决策

- Convert identifiers field-by-field and retain the OH canonical pointer rather than comparing24 bytes against16.
- An injected resident backend handle cannot create another owner; publication remains a separate gate.
- Callback-driven refill continues in the same OH pull buffer and stops on underrun.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-upstream-audio/**
- tools/spec-checks/tests/u12_upstream_audio.rs

## 验收标准

场景: Identifier widths and queue refill preserve positive and negative outcomes
  测试: u12_audio_primitives
  假设 Android16 identifiers OH24 identifiers and a refill callback
  当 Actual candidate functions execute in the offline host fixture
  那么 Canonical values match continuously refilled bytes are preserved and PLAY return12 is not reported as success

场景: Candidate admission does not hide static failures
  测试: u12_audio_static_gates
  假设 A pinned deployed facade and repeated offline builds
  当 Open site strings ABI and namespace checks run
  那么 Raw output and pending owner or exception decisions are retained without window authorization

## 排除范围

- No hardware playback completion or media JNI publication proof from fixtures.
