spec: task
name: "Two actual media roots and source lookup"
inherits: project
---

## 意图

Pin each actual missing library name and distinguish Unity NDK media dependencies from Chessclock's Java JNI manifest lookup.

## 已定决策

- Bind original window5 errors to package, PID and SHA.
- Scan the deployed MediaPlayer initializer instead of guessing a library from the generic manifest error.
- Search local, a2hlab and hw248 in order and record unsuccessful access honestly.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-mediandk/**
- tools/spec-checks/tests/u12_mediandk.rs

## 验收标准

场景: The two observed failures require different providers
  测试: u12_mediandk_evidence
  假设 Two original pinned window5 runs and the deployed framework DEX
  当 Library names and JNI initializer instructions are checked
  那么 Unity requires libmediandk and Chessclock requires media_jni with separate repair predictions

## 排除范围

- Device operations and compat relocation scope changes.
