spec: task
name: "U15 Stage A disabled packet"
inherits: project
---

## 意图

Prepare three disabled observation plans from the accepted U15 keys and the provisional U14 reference. Preserve raw log provenance, unresolved promotion bindings and the offline 61b boundary for outer review.

## 已定决策

- Snapshot the 126-key reference and signed windows1–3; add the three signed gains without double scheduling termux.
- Keep all execution/rollout flags false and every deployment-binding SHA null, with owner and fill timing recorded.
- Use only observed hilog messages for regex markers, permitting bare hexadecimal pointers; missing new-message observations remain pending.
- Six lottery trials remain consecutive, per-key shards disjoint, new tests stop at minute35 and the window ends by minute45.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-stage-a-plan/**
- specs/u15-stage-a-plan/**
- tools/spec-checks/tests/u15_stage_a_plan.rs

## 验收标准

场景: Provisional reference is protected without double scheduling
  测试: u15_stage_a_plan_draft
  假设 The local reference has126 lit keys and signed window1 gains have3 distinct keys
  当 The disabled plans are generated
  那么 All129 provisional lit keys are covered once by category and termux remains one white-watch trial

场景: Missing promotion identity cannot confer authority
  测试: u15_stage_a_plan_draft
  假设 U14 promotion and candidate arming are pending
  当 Plans and the guard are checked
  那么 All deployment bindings are null and the guard exits78 without device or lock action

场景: Invented pointer prefix cannot replace raw evidence
  测试: u15_stage_a_plan_draft
  假设 An observed hilog message prints a pointer without0x
  当 The marker regex is checked against its stored original line
  那么 The bare pointer matches and an unsupported0x-only regex is rejected

场景: Overlapping categories or missing protection reject
  测试: u15_stage_a_plan_draft
  假设 A key is duplicated or one provisional lit key is removed
  当 The offline plan validator runs
  那么 It raises a coverage or duplicate error

场景: Offline61b is not silently reassigned
  测试: u15_stage_a_plan_draft
  假设 Only common boards can be authorized after U14 promotion
  当 The staged common policy is examined
  那么 The61b variant and its58 trials remain pending with no automatic transfer and no global-promotion claim

## 排除范围

- Filling active bindings, taking locks, production replay, applying204 registry rows or signing U14 promotion.
