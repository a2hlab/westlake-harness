spec: task
name: "Disabled atomic U13 compat rebind"
inherits: project
depends: [t1-native]
---

## 意图

Bind the new compat pair into a separate disabled U13 package without overwriting the accepted old draft or fabricating approval.

## 已定决策

- Change only the root and route compat files; leave host2a87118e and all JARs unchanged.
- Report McDonald first-wall evidence and unresolved direct-provider imports separately from global inventory coverage.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-compat-ctype/**
- specs/u13-compat-ctype/**
- tools/spec-checks/tests/u13_compat_ctype.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Both aliases change without a new execution capability
  测试: u13_compat_ctype_draft
  假设 The prior frozen U13 draft is retained
  当 The compat candidate replaces its two existing targets
  那么 Only two payload files change and rollout stays disabled with exact new hashes

场景: Static inventory does not promise lighting
  测试: u13_compat_ctype_draft
  假设 McDonald reports a concrete missing data symbol
  当 All strong imports are checked against exact candidate and factory providers
  那么 Missing scope-dependent symbols and next-wall uncertainty are reported without counting inventory as live proof

## 排除范围

- Deployment, automatic approval, McDonald host whitelist and runtime rebuild.
