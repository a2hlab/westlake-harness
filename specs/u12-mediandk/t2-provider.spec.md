spec: task
name: "Typed unsupported media provider and static admission evidence"
inherits: project
depends: [t1-evidence]
---

## 意图

Build a correctly typed media error boundary for the actual imported APIs, retaining static gate deltas and unknown runtime fallback.

## 已定决策

- Use real media-status values and typed pointer, boolean, integer and void interfaces.
- Test behavior from admitted source when ignored artifact files are absent.
- Keep any generation-level gate rejection visible and deployment disabled.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-mediandk/**
- tools/spec-checks/tests/u12_mediandk.rs

## 验收标准

场景: Error boundary preserves ABI and does not claim functional media
  测试: u12_mediandk_provider
  假设 Actual imported API declarations and explicit unsupported media behavior
  当 Host source tests and recorded candidate static gates are checked
  那么 Failure values and API coverage match while exact next fatal and screenshot outcomes remain unknown

## 排除范围

- Codec implementation, installing a candidate, approving exceptions or bypassing unsupported checks.
