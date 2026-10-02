spec: task
name: "Repair-layer and bounded first-fatal predictions"
inherits: project
depends: [t1-evidence]
---

## 意图

Distinguish missing exports, unavailable namespaces and SoLoader fallback paths without inventing a loader fix or repeating a wall move already covered by U12.

## 已定决策

- Existing private ABI exports are not globally absent just because compat omits them.
- Relocation reached in lib-main is not an EACCES loading failure.
- Separate conditional first-fatal movement from proven movement and t20.

## 边界

### 允许修改
- benchmark/2026-10-02-u13-native-load-3/**
- specs/u13-native-load-3/**
- tools/spec-checks/tests/u13_native_load_3.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Element is not counted twice
  测试: u13_native_load_3_predictions
  假设 U12 already contains the reviewed private zlib route
  当 Predictions are emitted relative to T8 and U12
  那么 T8 conditional movement is one and incremental U13 movement is zero

场景: Meet recovery does not become a permission fix
  测试: u13_native_load_3_predictions
  假设 Public atfork failures precede fallback abort relocation
  当 Repair classes are adjudicated
  那么 Both symbols and namespace uncertainty remain explicit and permission-only movement is zero

场景: Audio load success is not PLAY completion
  测试: u13_native_load_3_predictions
  假设 The deployed facade lacks slCreateEngine but OH exports it
  当 The load-wall prediction is recorded
  那么 Conditional movement is one while PLAY return12 and UI uncertainty are retained

## 排除范围

- Audio implementation, owner publication and deployment authorization.
