spec: task
name: "Prepare parameterized U14 U13-base metadata copies"
inherits: project
---

## 意图

Prepare immutable disabled U14 common and 61b metadata copies with explicit U13 BASE and full SHA, preserving every candidate artifact and reviewed native binding.

## 已定决策

- Accept only the matching signed U13 variant or its evidenced armed metadata equivalent; arming must change only rollout_ready and rollout_blocker.
- Validate the complete planned U13 identity and fingerprints, not old U13 reference files that describe T8.
- Refuse an existing output, wrong variant, changed payload, unsigned base hash or installer action.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-on-u13-base/**
- specs/u14-on-u13-base/**
- tools/spec-checks/tests/u14_on_u13_base.rs
- README.md

## 验收标准

场景: Explicit common and 61b bases preserve payload identity
  测试: u14_u13_binding
  假设 A disabled reviewed U14 candidate and matching U13 BASE plus full SHA are supplied
  当 Binding is prepared with variant BASE SHA and fresh output together
  那么 Native and image bytes remain unchanged and installer baseline equals expected without an installer action

场景: Incorrect or armed payload changing base is rejected
  测试: u14_u13_binding
  假设 A wrong variant hash or an armed base with more than rollout metadata changed is supplied
  当 Base correspondence is checked
  那么 The preparation rejects it without granting promotion or execution

## 排除范围

- Approve findings, apply registries, promote U13 or deploy U14.
