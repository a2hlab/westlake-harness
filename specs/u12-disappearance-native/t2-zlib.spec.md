spec: task
name: "Reviewed private zlib route"
inherits: project
depends: [t1-icu]
---

## 意图

Deliver the previously reviewed narrow r3 zlib route and exact r109c alias/provider for BurgerKing.

## 已定决策

- Do not rewrite the reviewed package-boundary predicate or widen its two-key list.
- Compare the host against the actual deployed r3, not the U9 host.
- Keep existing namespace inherit edges and provide an explicit rollback recipe.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-private-zlib/**
- tools/spec-checks/tests/u12_private_zlib.rs

## 验收标准

场景: The reviewed route is reproduced without unrelated owner changes
  测试: u12_private_zlib
  假设 Exact r3 source, reviewed route and r109c zlib artifacts
  当 Reproducible builds, route negative controls and static gate deltas are checked
  那么 Only the package-specific search route changes with rollback bound and one conditional first-wall movement

## 排除范围

- New policy SONAME entries, board tests and promising new lights.
